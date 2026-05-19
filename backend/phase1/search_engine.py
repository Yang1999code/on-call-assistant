import re
import sqlite3
import jieba
from pathlib import Path


class SearchEngine:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "search.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # FTS5 自存储模式：不需要外部 content table，避免 TEXT id 映射问题
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts
            USING fts5(id, title, content, tokenize='trigram')
        """)

    def index_document(self, doc_id: str, title: str, content: str):
        tokenized = ' '.join(jieba.cut(content))
        self.conn.execute(
            "INSERT OR REPLACE INTO documents(id, title, content) VALUES (?, ?, ?)",
            (doc_id, title, content)
        )
        self.conn.execute(
            "INSERT OR REPLACE INTO docs_fts(id, title, content) VALUES (?, ?, ?)",
            (doc_id, title, tokenized)
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 10) -> list:
        tokenized_query = ' '.join(jieba.cut(query))
        q = query.strip()

        _SPECIAL = re.compile(r'[&%_\\/\-]')
        if len(q) < 3 or _SPECIAL.search(q):
            # 短查询或含特殊字符（如 & / % _ -）：trigram 不可靠 → LIKE 回退
            rows = self.conn.execute("""
                SELECT d.id, d.title,
                       substr(d.content, max(1, instr(d.content, ?)-30), 80) as snippet,
                       1 as rank
                FROM documents d
                WHERE d.content LIKE '%' || ? || '%'
                LIMIT ?
            """, (q, q, limit)).fetchall()
        else:
            # FTS5 trigram 搜索 + jieba 分词查询
            # docs_fts 存的是 jieba 分词后的文本，snippet 从 documents 原文本生成
            fts_rows = self.conn.execute("""
                SELECT id, rank
                FROM docs_fts
                WHERE docs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (tokenized_query, limit)).fetchall()

            rows = []
            seen = set()
            for fr in fts_rows:
                if fr[0] in seen:
                    continue
                seen.add(fr[0])
                doc = self.conn.execute(
                    "SELECT id, title, content FROM documents WHERE id = ?",
                    (fr[0],)
                ).fetchone()
                if doc:
                    # 手动生成 snippet：找到匹配位置，取前后各 30 字
                    content = doc[2]
                    idx = content.find(q)
                    if idx < 0:
                        # 分词后匹配的，尝试找 tokenized 的词
                        tokens = list(jieba.cut(q))
                        for t in tokens:
                            if len(t) >= 2:
                                idx = content.find(t)
                                if idx >= 0:
                                    break
                    if idx < 0:
                        idx = 0
                    start = max(0, idx - 30)
                    end = min(len(content), idx + 50)
                    snippet = content[start:end]
                    if start > 0:
                        snippet = '...' + snippet
                    if end < len(content):
                        snippet = snippet + '...'
                    rows.append((doc[0], doc[1], snippet, fr[1]))

        max_rank = max(r[3] for r in rows) if rows else 1
        return [
            {'id': r[0], 'title': r[1], 'snippet': r[2],
             'score': round(1.0 - (r[3] - 1) / max(max_rank, 1), 4) if max_rank > 0 else 1.0}
            for r in rows
        ]

    def get_all_documents(self) -> list[tuple]:
        """Return all documents as (id, title, content) tuples."""
        return self.conn.execute(
            "SELECT id, title, content FROM documents"
        ).fetchall()

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return row[0] if row else 0

import chromadb
from pathlib import Path
from backend.phase1.search_engine import SearchEngine
from backend.phase2.embeddings import encode

CHROMA_DIR = Path(__file__).parent.parent.parent / "data" / "chroma"


def chunk_text(content: str, title: str, chunk_size: int = 500, overlap: int = 100) -> list[dict]:
    """Split document into overlapping chunks, each tagged with title."""
    chunks = []
    paragraphs = content.split("\n")
    current = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # If a single paragraph exceeds chunk_size, split it
        while len(para) > chunk_size:
            if current.strip():
                chunks.append({"text": current.strip(), "title": title})
                if len(current) > overlap:
                    current = current[-overlap:]
                else:
                    current = ""
            chunks.append({"text": para[:chunk_size], "title": title})
            para = para[chunk_size - overlap:]
        if current and len(current) + len(para) > chunk_size:
            chunks.append({"text": current.strip(), "title": title})
            if len(current) > overlap:
                current = current[-overlap:]
            else:
                current = ""
        current += para + " "
    if current.strip():
        chunks.append({"text": current.strip(), "title": title})
    if not chunks:
        chunks.append({"text": content[:chunk_size], "title": title})
    return chunks


class VectorStore:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(Path(__file__).parent.parent.parent / "data" / "search.db")
        self.keyword_engine = SearchEngine(db_path)
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._init_collection()

    def _init_collection(self):
        try:
            self.collection = self.client.get_collection("sop_chunks")
        except Exception:
            self.collection = self.client.create_collection(
                "sop_chunks",
                metadata={"hnsw:space": "cosine"}
            )

    def index_all(self):
        """Index all documents from keyword DB into ChromaDB."""
        docs = self.keyword_engine.get_all_documents()
        for doc in docs:
            self.index_document(doc[0], doc[1], doc[2])

    def index_document(self, doc_id: str, title: str, content: str):
        chunks = chunk_text(content, title)
        chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        # Remove old chunks for this doc
        try:
            old = self.collection.get(where={"doc_id": doc_id})
            if old["ids"]:
                self.collection.delete(ids=old["ids"])
        except Exception:
            pass
        if not chunks:
            return
        embeddings = encode([c["text"] for c in chunks])
        self.collection.add(
            ids=chunk_ids,
            documents=[c["text"] for c in chunks],
            embeddings=embeddings,
            metadatas=[{"doc_id": doc_id, "title": title, "chunk_index": i} for i in range(len(chunks))]
        )

    def vector_search(self, query: str, limit: int = 20) -> list[dict]:
        """Pure vector search."""
        q_embedding = encode([query])[0]
        results = self.collection.query(query_embeddings=[q_embedding], n_results=limit)
        seen = set()
        merged = []
        if not results["ids"] or not results["ids"][0]:
            return []
        for i in range(len(results["ids"][0])):
            doc_id = results["metadatas"][0][i]["doc_id"]
            if doc_id in seen:
                continue
            seen.add(doc_id)
            dist = results["distances"][0][i] if results.get("distances") else 0
            similarity = 1.0 - dist if dist else 1.0
            merged.append({
                "id": doc_id,
                "title": results["metadatas"][0][i]["title"],
                "snippet": (results["documents"][0][i] or ""),
                "score": round(similarity, 4)
            })
        return merged

    def hybrid_search(self, query: str, limit: int = 10) -> list[dict]:
        """RRF fusion of keyword (FTS5) and vector (ChromaDB) search."""
        # Get keyword results
        kw_results = self.keyword_engine.search(query, limit=limit * 2)
        # Get vector results
        vec_results = self.vector_search(query, limit=limit * 2)

        rrf_scores: dict[str, dict] = {}
        k = 60

        for rank, r in enumerate(kw_results):
            did = r["id"]
            if did not in rrf_scores:
                rrf_scores[did] = {"id": did, "title": r["title"], "snippet": r["snippet"]}
            rrf_scores[did]["kw_rank"] = rank

        for rank, r in enumerate(vec_results):
            did = r["id"]
            if did not in rrf_scores:
                rrf_scores[did] = {"id": did, "title": r["title"], "snippet": r["snippet"]}
            rrf_scores[did]["vec_rank"] = rank

        for did in rrf_scores:
            kw_score = 1.0 / (k + rrf_scores[did].get("kw_rank", 999))
            vec_score = 1.0 / (k + rrf_scores[did].get("vec_rank", 999))
            rrf_scores[did]["score"] = round(kw_score + vec_score, 4)

        sorted_results = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
        return sorted_results[:limit]

    def count_chunks(self) -> int:
        return self.collection.count()

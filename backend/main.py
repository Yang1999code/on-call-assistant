import glob
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from backend.phase1.parser import parse_html
from backend.phase1.search_engine import SearchEngine
from backend.phase1.router import router as phase1_router
from backend.phase2.router import router as phase2_router
from backend.phase2.vector_store import VectorStore
from backend.phase3.router import router as phase3_router
from backend.shared.middleware import request_logger

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ROOT = Path(__file__).parent.parent  # myOn-Call/
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = str(DATA_DIR / "search.db")

    def _clean_start():
        engine = SearchEngine(db_path)
        engine.conn.execute("DELETE FROM documents")
        engine.conn.execute("DELETE FROM docs_fts")
        engine.conn.commit()

        for f in sorted(glob.glob(str(DATA_DIR / "sop-*.html"))):
            doc_id = Path(f).stem
            with open(f, "r", encoding="utf-8") as fh:
                html = fh.read()
            parsed = parse_html(html)
            engine.index_document(doc_id, parsed["title"], parsed["content"])
        logging.info(f"Phase 1: clean indexed {engine.count()} documents")

        vs = VectorStore(db_path)
        try:
            all_ids = vs.collection.get()["ids"]
            if all_ids:
                vs.collection.delete(ids=all_ids)
        except Exception:
            pass
        vs.index_all()
        logging.info(f"Phase 2: clean indexed {vs.count_chunks()} chunks into ChromaDB")

    _clean_start()
    yield


app = FastAPI(title="On-Call Assistant", lifespan=lifespan)
app.middleware("http")(request_logger)

app.include_router(phase1_router)
app.include_router(phase2_router)
app.include_router(phase3_router)

FRONTEND_DIR.mkdir(exist_ok=True)


@app.get("/")
async def root():
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"message": "On-Call Assistant API", "phases": [1, 2, 3]}


@app.get("/status")
async def status():
    engine = SearchEngine(str(DATA_DIR / "search.db"))
    vs = VectorStore(str(DATA_DIR / "search.db"))
    return {
        "phases": {
            "1_keyword_search": {"documents": engine.count()},
            "2_semantic_search": {"vector_chunks": vs.count_chunks()},
            "3_agent": {
                "mode": "llm" if os.getenv("OPENAI_API_KEY") else "fallback",
                "tools": ["readFile"]
            }
        }
    }

from fastapi import APIRouter, Query
from backend.phase2.vector_store import VectorStore
from backend.shared.models import SearchResult, SearchResponse

router = APIRouter()
store = VectorStore()


@router.get("/v2/search", response_model=SearchResponse)
def semantic_search(q: str = Query(..., description="Semantic search query"), limit: int = Query(10, ge=1, le=50)):
    results = store.hybrid_search(q, limit=limit)
    return SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results]
    )


@router.get("/v2")
def phase2_status():
    return {"phase": 2, "vector_chunks": store.count_chunks()}

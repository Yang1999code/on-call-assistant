from fastapi import APIRouter, HTTPException, Query
from backend.phase1.parser import parse_html
from backend.phase1.search_engine import SearchEngine
from backend.shared.models import DocumentInput, SearchResult, SearchResponse

router = APIRouter()
engine = SearchEngine()


@router.post("/v1/documents", status_code=201)
def index_document(doc: DocumentInput):
    try:
        parsed = parse_html(doc.html)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"HTML parse error: {str(e)}")
    engine.index_document(doc.id, parsed["title"], parsed["content"])
    return {"id": doc.id, "title": parsed["title"]}


@router.get("/v1/search", response_model=SearchResponse)
def search(q: str = Query(..., description="Search query"), limit: int = Query(10, ge=1, le=50)):
    results = engine.search(q, limit=limit)
    return SearchResponse(
        query=q,
        results=[SearchResult(**r) for r in results]
    )


@router.get("/v1")
def phase1_status():
    return {"phase": 1, "documents": engine.count()}

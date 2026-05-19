from pydantic import BaseModel
from typing import Optional


class DocumentInput(BaseModel):
    id: str
    html: str


class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class ChatRequest(BaseModel):
    message: str

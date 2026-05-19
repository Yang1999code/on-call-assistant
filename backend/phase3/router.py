from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.phase3.agent_loop import agent_chat
from backend.shared.models import ChatRequest

router = APIRouter()


@router.post("/v3")
async def chat(request: ChatRequest):
    async def event_stream():
        async for event in agent_chat(request.message):
            yield event
    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/v3")
def phase3_status():
    import os
    has_api = bool(os.getenv("OPENAI_API_KEY"))
    return {
        "phase": 3,
        "mode": "llm" if has_api else "fallback",
        "tools": ["readFile"]
    }

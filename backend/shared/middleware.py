import time
import logging
from fastapi import Request, HTTPException

logger = logging.getLogger("oncall")

MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


async def request_logger(request: Request, call_next):
    start = time.time()

    # Body size check for POST/PUT
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        raise HTTPException(status_code=413, detail="Request body too large (max 10 MB)")

    response = await call_next(request)
    elapsed = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed:.0f}ms)")
    return response

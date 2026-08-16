from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


MAX_REQUEST_BYTES = 256 * 1024


class OperationalMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > MAX_REQUEST_BYTES:
                    response = Response(
                        content='{"detail":"Request body is too large."}',
                        status_code=413,
                        media_type="application/json",
                    )
                    response.headers["X-Request-ID"] = request_id
                    response.headers["Cache-Control"] = "no-store"
                    return response
            except ValueError:
                response = Response(
                    content='{"detail":"Invalid Content-Length header."}',
                    status_code=400,
                    media_type="application/json",
                )
                response.headers["X-Request-ID"] = request_id
                response.headers["Cache-Control"] = "no-store"
                return response

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response

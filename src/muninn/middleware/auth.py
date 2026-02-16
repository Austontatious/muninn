from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import api_key, api_key_header, require_api_key


class ApiKeyMiddleware(BaseHTTPMiddleware):
    ALLOWLIST_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        if not require_api_key():
            return await call_next(request)

        path = request.url.path
        if path in self.ALLOWLIST_PATHS or path.startswith("/docs/"):
            return await call_next(request)

        configured = api_key()
        if not configured:
            return JSONResponse(
                status_code=500,
                content={"detail": "MUNINN_API_KEY is required when MUNINN_REQUIRE_API_KEY=1"},
            )

        provided = request.headers.get(api_key_header())
        if provided != configured:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        return await call_next(request)

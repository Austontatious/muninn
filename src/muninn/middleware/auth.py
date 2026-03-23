from __future__ import annotations

import json
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ..config import api_key, api_key_header, require_api_key

logger = logging.getLogger(__name__)
_INVALID_API_KEYS_LOGGED = False


def _default_namespace() -> str:
    raw = os.getenv("MUNINN_DEFAULT_NAMESPACE") or os.getenv("MUNINN_NAMESPACE") or "default"
    value = raw.strip()
    return value or "default"


def _parse_api_key_namespaces(raw: str) -> dict[str, str]:
    value = raw.strip()
    if not value:
        return {}

    if value.startswith("{"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        if not isinstance(parsed, dict):
            return {}
        out: dict[str, str] = {}
        for key, namespace in parsed.items():
            key_text = str(key).strip()
            namespace_text = str(namespace).strip()
            if key_text and namespace_text:
                out[key_text] = namespace_text
        return out

    out: dict[str, str] = {}
    for entry in value.split(","):
        pair = entry.strip()
        if not pair or ":" not in pair:
            continue
        key, namespace = pair.split(":", 1)
        key_text = key.strip()
        namespace_text = namespace.strip()
        if key_text and namespace_text:
            out[key_text] = namespace_text
    return out


def _configured_api_key_namespaces() -> tuple[dict[str, str], bool]:
    configured: dict[str, str] = {}
    raw_map = os.getenv("MUNINN_API_KEYS")
    if raw_map and raw_map.strip():
        parsed = _parse_api_key_namespaces(raw_map)
        if not parsed:
            return {}, True
        configured.update(parsed)

    legacy_key = api_key()
    if legacy_key and legacy_key not in configured:
        configured[legacy_key] = _default_namespace()
    return configured, False


def _allow_unauth_namespace_override() -> bool:
    raw = os.getenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _extract_supplied_api_key(request: Request) -> str | None:
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    provided = request.headers.get(api_key_header()) or ""
    token = provided.strip()
    return token or None


class ApiKeyMiddleware(BaseHTTPMiddleware):
    ALLOWLIST_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in self.ALLOWLIST_PATHS or path.startswith("/docs/"):
            request.state.namespace = _default_namespace()
            request.state.namespace_enforced = False
            request.state.allow_namespace_override = _allow_unauth_namespace_override()
            return await call_next(request)

        if not require_api_key():
            request.state.namespace = _default_namespace()
            request.state.namespace_enforced = False
            request.state.allow_namespace_override = _allow_unauth_namespace_override()
            return await call_next(request)

        configured_map, map_invalid = _configured_api_key_namespaces()
        if map_invalid:
            global _INVALID_API_KEYS_LOGGED
            if not _INVALID_API_KEYS_LOGGED:
                _INVALID_API_KEYS_LOGGED = True
                logger.error(
                    "MUNINN_API_KEYS is set but invalid/empty after parsing; refusing all protected requests."
                )
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        if not configured_map:
            return JSONResponse(
                status_code=500,
                content={
                    "detail": (
                        "Set MUNINN_API_KEYS (key:namespace pairs) or MUNINN_API_KEY "
                        "when MUNINN_REQUIRE_API_KEY=1"
                    )
                },
            )

        supplied_key = _extract_supplied_api_key(request)
        if not supplied_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        namespace = configured_map.get(supplied_key)
        if not namespace:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

        request.state.namespace = namespace
        request.state.namespace_enforced = True
        request.state.allow_namespace_override = False
        return await call_next(request)

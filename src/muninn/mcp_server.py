from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from .models import (
    ConfirmCandidatesRequest,
    ListPendingRequest,
    RehydrateRequest,
    StageCandidatesRequest,
)


def _resolve_base_url() -> str:
    return os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def _resolve_headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.getenv("MUNINN_API_KEY")
    if api_key:
        header_name = os.getenv("MUNINN_API_KEY_HEADER", "X-API-Key")
        headers[header_name] = api_key
    return headers


async def _post_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{_resolve_base_url()}{path}"
    async with httpx.AsyncClient(headers=_resolve_headers(), timeout=30.0) as client:
        response = await client.post(url, json=payload)

    if response.status_code >= 400:
        raise ValueError(f"Muninn API error [{response.status_code}] {path}: {response.text}")

    if not response.content:
        return {}
    return response.json()


def create_mcp_server(host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    mcp = FastMCP(
        name="muninn-mcp",
        host=host,
        port=port,
        streamable_http_path="/mcp",
    )

    @mcp.tool(name="muninn_rehydrate", description="Forward to /v0/memory/rehydrate")
    async def muninn_rehydrate(
        namespace: str,
        query: str,
        entity_id: str | None = None,
        k: int = 8,
        profile: str = "generic",
        embedding_model: str | None = None,
        query_embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        req = RehydrateRequest(
            namespace=namespace,
            query=query,
            entity_id=entity_id,
            k=k,
            profile=profile,
            embedding_model=embedding_model,
            query_embedding=query_embedding,
        )
        return await _post_json("/v0/memory/rehydrate", req.model_dump())

    @mcp.tool(
        name="muninn_stage_candidates",
        description="Forward to /v0/memory/stage_candidates",
    )
    async def muninn_stage_candidates(
        namespace: str,
        candidates: list[dict[str, Any]],
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        req = StageCandidatesRequest(
            namespace=namespace,
            candidates=candidates,
            ttl_seconds=ttl_seconds,
        )
        return await _post_json("/v0/memory/stage_candidates", req.model_dump())

    @mcp.tool(name="muninn_list_pending", description="Forward to /v0/memory/list_pending")
    async def muninn_list_pending(
        namespace: str,
        entity_id: str | None = None,
        status: str = "pending",
        limit: int = 50,
    ) -> dict[str, Any]:
        req = ListPendingRequest(
            namespace=namespace,
            entity_id=entity_id,
            status=status,
            limit=limit,
        )
        return await _post_json("/v0/memory/list_pending", req.model_dump())

    @mcp.tool(
        name="muninn_confirm_candidates",
        description="Forward to /v0/memory/confirm_candidates",
    )
    async def muninn_confirm_candidates(
        namespace: str,
        pending_ids: list[str],
        decision: str,
        decided_by: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        req = ConfirmCandidatesRequest(
            namespace=namespace,
            pending_ids=pending_ids,
            decision=decision,
            decided_by=decided_by,
            note=note,
        )
        return await _post_json("/v0/memory/confirm_candidates", req.model_dump())

    return mcp


def run_mcp_server(host: str = "127.0.0.1", port: int = 8765, base_url: str | None = None) -> None:
    if base_url:
        os.environ["MUNINN_BASE_URL"] = base_url

    server = create_mcp_server(host=host, port=port)
    print("Muninn MCP up")
    print(f"  MCP URL: http://{host}:{port}/mcp")
    print(f"  Muninn Base URL: {_resolve_base_url()}")
    print(f"  API key header forwarding: {'enabled' if os.getenv('MUNINN_API_KEY') else 'disabled'}")
    try:
        asyncio.run(server.run_streamable_http_async())
    except KeyboardInterrupt:
        print("Muninn MCP stopped")

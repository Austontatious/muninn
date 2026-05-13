from __future__ import annotations

import json
import os
from typing import Any, Literal

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

CONNECTOR_NAME = "Muninn Memory"
CONFIRMATION_PHRASE = "CONFIRM MUNINN WRITE"
DEFAULT_MUNINN_BASE_URL = "http://friday-muninn-1:8000"
DEFAULT_NAMESPACE = "default"
DEFAULT_PROFILE = "friday"
STREAMABLE_HTTP_PATH = "/mcp"

TOOL_NAMES: tuple[str, ...] = (
    "search",
    "fetch",
    "search_memory",
    "fetch_memory",
    "rehydrate_project",
    "stage_memory_candidates",
    "list_pending_memory",
    "confirm_memory_candidates",
)
READ_ONLY_TOOL_NAMES: tuple[str, ...] = (
    "search",
    "fetch",
    "search_memory",
    "fetch_memory",
    "rehydrate_project",
    "list_pending_memory",
)
READ_ONLY_TOOL_ANNOTATIONS = ToolAnnotations(readOnlyHint=True)

_KINDS = {"fact", "episode", "preference"}
_PROFILES = {"generic", "lexi", "friday"}
_DECISIONS = {"accept", "reject"}
_PROVENANCE_SOURCE_TYPES = {"user", "assistant", "tool", "document", "system"}
_FORBIDDEN_ROUTE_PREFIXES = (
    "/v0/admin/",
    "/v0/debug/",
)
_FORBIDDEN_ROUTES = {
    "/v0/memory/write_candidates",
    "/v0/memory/upsert_embeddings",
}


def _muninn_base_url() -> str:
    return os.getenv("MUNINN_BASE_URL", DEFAULT_MUNINN_BASE_URL).rstrip("/")


def _host() -> str:
    return os.getenv("MCP_HOST", "0.0.0.0")


def _port() -> int:
    raw = os.getenv("MCP_PORT", "8000").strip()
    try:
        value = int(raw)
    except ValueError:
        return 8000
    return max(1, min(value, 65535))


def _json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _safe_error(message: str, **details: Any) -> str:
    payload: dict[str, Any] = {"ok": False, "error": message}
    payload.update({key: value for key, value in details.items() if value is not None})
    return _json_text(payload)


def _clamp(value: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = minimum
    return max(minimum, min(parsed, maximum))


def _snippet(text: str, *, limit: int = 420) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _title_for_item(item: dict[str, Any]) -> str:
    text = str(item.get("text") or "").strip()
    kind = str(item.get("kind") or "memory").strip() or "memory"
    entity_id = str(item.get("entity_id") or "").strip()
    if text:
        first_sentence = text.split(".", 1)[0].strip()
        title = first_sentence or text
        return _snippet(title, limit=90)
    if entity_id:
        return f"{kind}: {entity_id}"
    return kind


def _memory_url(memory_id: str) -> str:
    return f"muninn://memory/{memory_id}"


def _assert_allowed_route(path: str) -> None:
    if path in _FORBIDDEN_ROUTES or any(path.startswith(prefix) for prefix in _FORBIDDEN_ROUTE_PREFIXES):
        raise ValueError("Muninn MCP bridge attempted to use a forbidden route")


class MuninnClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or _muninn_base_url()).rstrip("/")
        self.timeout = timeout
        self.transport = transport

    async def _request_json(
        self,
        method: Literal["GET", "POST"],
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _assert_allowed_route(path)
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                transport=self.transport,
            ) as client:
                response = await client.request(method, path, json=json_payload)
        except httpx.HTTPError:
            return {"ok": False, "error": "muninn request failed", "path": path}

        if response.status_code >= 400:
            return {
                "ok": False,
                "error": "muninn request failed",
                "status_code": response.status_code,
                "path": path,
            }
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError:
            return {"ok": False, "error": "muninn returned non-json response", "path": path}
        if isinstance(data, dict):
            return data
        return {"value": data}

    async def post_retrieve(
        self,
        *,
        query: str,
        namespace: str = DEFAULT_NAMESPACE,
        entity_id: str | None = None,
        k: int = 8,
        query_embedding: list[float] | None = None,
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/retrieve",
            json_payload={
                "namespace": namespace,
                "query": query,
                "entity_id": entity_id,
                "k": k,
                "query_embedding": query_embedding,
                "embedding_model": embedding_model,
            },
        )

    async def post_rehydrate(
        self,
        *,
        query: str,
        namespace: str = DEFAULT_NAMESPACE,
        entity_id: str | None = None,
        k: int = 8,
        profile: str = DEFAULT_PROFILE,
        query_embedding: list[float] | None = None,
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/rehydrate",
            json_payload={
                "namespace": namespace,
                "query": query,
                "entity_id": entity_id,
                "k": k,
                "profile": profile,
                "query_embedding": query_embedding,
                "embedding_model": embedding_model,
            },
        )

    async def post_render_cards(
        self,
        *,
        items: list[dict[str, Any]],
        namespace: str = DEFAULT_NAMESPACE,
        profile: str = "generic",
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/render_cards",
            json_payload={"namespace": namespace, "items": items, "profile": profile},
        )

    async def post_stage_candidates(
        self,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        candidates: list[dict[str, Any]],
        ttl_seconds: int | None = 86400,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/stage_candidates",
            json_payload={
                "namespace": namespace,
                "candidates": candidates,
                "ttl_seconds": ttl_seconds,
            },
        )

    async def post_list_pending(
        self,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        entity_id: str | None = None,
        status: str = "pending",
        limit: int = 50,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/list_pending",
            json_payload={
                "namespace": namespace,
                "entity_id": entity_id,
                "status": status,
                "limit": limit,
            },
        )

    async def post_confirm_candidates(
        self,
        *,
        namespace: str = DEFAULT_NAMESPACE,
        pending_ids: list[str],
        decision: str,
        decided_by: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        return await self._request_json(
            "POST",
            "/v0/memory/confirm_candidates",
            json_payload={
                "namespace": namespace,
                "pending_ids": pending_ids,
                "decision": decision,
                "decided_by": decided_by,
                "note": note,
            },
        )

    async def get_health(self) -> dict[str, Any]:
        return await self._request_json("GET", "/health")

    async def get_version(self) -> dict[str, Any]:
        return await self._request_json("GET", "/v0/memory/version")


def _items_from_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    items = response.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _normalize_namespace(namespace: str) -> str:
    value = str(namespace or "").strip()
    return value or DEFAULT_NAMESPACE


def _normalize_profile(profile: str) -> str:
    value = str(profile or "").strip().lower()
    if value not in _PROFILES:
        raise ValueError("profile must be one of generic, lexi, friday")
    return value


def _normalize_provenance(raw: dict[str, Any]) -> dict[str, Any]:
    original_note = raw.get("note") if isinstance(raw.get("note"), str) else None
    original_source_type = raw.get("source_type") if isinstance(raw.get("source_type"), str) else None
    original_source_id = raw.get("source_id") if isinstance(raw.get("source_id"), str) else None

    note_parts = [
        "source=chatgpt_mcp",
        "tool=stage_memory_candidates",
        "write_mode=staged",
    ]
    if original_source_type and original_source_type != "tool":
        note_parts.append(f"original_source_type={original_source_type}")
    if original_source_id and original_source_id != "chatgpt_mcp":
        note_parts.append(f"original_source_id={original_source_id}")
    if original_note:
        note_parts.append(f"note={original_note}")

    normalized: dict[str, Any] = {
        "source_type": "tool",
        "source_id": "chatgpt_mcp",
        "note": "; ".join(note_parts),
    }
    if isinstance(raw.get("ts"), int | float):
        normalized["ts"] = float(raw["ts"])
    return normalized


def _validate_candidate(raw: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(raw, dict):
        return None, "candidate must be an object"

    kind = raw.get("kind")
    if kind not in _KINDS:
        return None, "candidate.kind must be fact, episode, or preference"

    entity = raw.get("entity")
    if not isinstance(entity, dict):
        return None, "candidate.entity must be an object"

    payload = raw.get("payload")
    if not isinstance(payload, dict):
        return None, "candidate.payload must be an object"

    confidence = raw.get("confidence", 0.7)
    if isinstance(confidence, bool) or not isinstance(confidence, int | float):
        return None, "candidate.confidence must be a number"
    if confidence < 0 or confidence > 1:
        return None, "candidate.confidence must be between 0 and 1"

    provenance = raw.get("provenance")
    if not isinstance(provenance, dict):
        return None, "candidate.provenance must be an object"

    source_type = provenance.get("source_type")
    if source_type is not None and source_type not in _PROVENANCE_SOURCE_TYPES:
        return None, "candidate.provenance.source_type is invalid"

    return (
        {
            "kind": kind,
            "entity": entity,
            "payload": payload,
            "confidence": float(confidence),
            "provenance": _normalize_provenance(provenance),
        },
        None,
    )


def _validate_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    if not isinstance(candidates, list):
        return [], ["candidates must be a list"]
    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, candidate in enumerate(candidates):
        item, error = _validate_candidate(candidate)
        if error:
            errors.append(f"candidates[{index}]: {error}")
        elif item is not None:
            normalized.append(item)
    return normalized, errors


async def _fetch_memory_record(
    *,
    memory_id: str,
    namespace: str,
    client: MuninnClient,
) -> dict[str, Any]:
    response = await client.post_retrieve(namespace=namespace, query=memory_id, k=20)
    if response.get("ok") is False:
        return response

    items = _items_from_response(response)
    exact_id_matches = [item for item in items if item.get("id") == memory_id]
    matched: dict[str, Any] | None = exact_id_matches[0] if exact_id_matches else None
    if matched is None:
        entity_matches = [item for item in items if item.get("entity_id") == memory_id]
        if len(entity_matches) == 1:
            matched = entity_matches[0]

    if matched is None:
        return {
            "found": False,
            "id": memory_id,
            "title": "Not found",
            "text": "No exact Muninn memory item found for this id.",
            "url": _memory_url(memory_id),
            "metadata": {"found": False},
        }

    cards: list[dict[str, Any]] = []
    render = await client.post_render_cards(namespace=namespace, items=[matched], profile="generic")
    if render.get("ok") is False:
        render_error = {"error": render.get("error"), "status_code": render.get("status_code")}
    else:
        render_error = None
        raw_cards = render.get("cards")
        if isinstance(raw_cards, list):
            cards = [card for card in raw_cards if isinstance(card, dict)]

    return {
        "found": True,
        "item": matched,
        "cards": cards,
        "render_error": render_error,
    }


async def search(query: str, client: MuninnClient | None = None) -> str:
    client = client or MuninnClient()
    response = await client.post_retrieve(
        namespace=DEFAULT_NAMESPACE,
        query=str(query or ""),
        k=8,
    )
    if response.get("ok") is False:
        return _json_text(response)

    results = []
    for item in _items_from_response(response):
        memory_id = str(item.get("id") or "")
        results.append(
            {
                "id": memory_id,
                "title": _title_for_item(item),
                "url": _memory_url(memory_id),
                "snippet": _snippet(str(item.get("text") or "")),
            }
        )
    return _json_text({"results": results})


async def fetch(id: str, client: MuninnClient | None = None) -> str:
    memory_id = str(id or "").strip()
    client = client or MuninnClient()
    record = await _fetch_memory_record(
        memory_id=memory_id,
        namespace=DEFAULT_NAMESPACE,
        client=client,
    )
    if record.get("ok") is False:
        return _json_text(record)
    if not record.get("found"):
        return _json_text(
            {
                "id": memory_id,
                "title": "Not found",
                "text": "No exact Muninn memory item found for this id.",
                "url": _memory_url(memory_id),
                "metadata": {"found": False},
            }
        )

    item = record["item"]
    memory_id = str(item.get("id") or memory_id)
    return _json_text(
        {
            "id": memory_id,
            "title": _title_for_item(item),
            "text": str(item.get("text") or ""),
            "url": _memory_url(memory_id),
            "metadata": {
                "kind": item.get("kind"),
                "entity_id": item.get("entity_id"),
                "confidence": item.get("confidence"),
                "provenance": item.get("provenance"),
                "cards": record.get("cards", []),
                "render_error": record.get("render_error"),
            },
        }
    )


async def search_memory(
    query: str,
    namespace: str = DEFAULT_NAMESPACE,
    entity_id: str | None = None,
    limit: int = 8,
    client: MuninnClient | None = None,
) -> str:
    client = client or MuninnClient()
    k = _clamp(limit, minimum=1, maximum=20)
    response = await client.post_retrieve(
        namespace=_normalize_namespace(namespace),
        query=str(query or ""),
        entity_id=entity_id,
        k=k,
    )
    if response.get("ok") is False:
        return _json_text(response)
    items = _items_from_response(response)
    return _json_text({"items": items, "count": len(items)})


async def fetch_memory(
    memory_id: str,
    namespace: str = DEFAULT_NAMESPACE,
    client: MuninnClient | None = None,
) -> str:
    client = client or MuninnClient()
    record = await _fetch_memory_record(
        memory_id=str(memory_id or "").strip(),
        namespace=_normalize_namespace(namespace),
        client=client,
    )
    return _json_text(record)


async def rehydrate_project(
    project: str,
    task: str | None = None,
    namespace: str = DEFAULT_NAMESPACE,
    profile: str = DEFAULT_PROFILE,
    limit: int = 8,
    client: MuninnClient | None = None,
) -> str:
    client = client or MuninnClient()
    try:
        normalized_profile = _normalize_profile(profile)
    except ValueError as exc:
        return _safe_error(str(exc))

    project_text = str(project or "").strip()
    task_text = str(task or "").strip() if task is not None else None
    query = f"{project_text}: {task_text}" if task_text else project_text
    k = _clamp(limit, minimum=1, maximum=20)
    response = await client.post_rehydrate(
        namespace=_normalize_namespace(namespace),
        query=query,
        k=k,
        profile=normalized_profile,
    )
    if response.get("ok") is False:
        return _json_text(response)
    return _json_text(
        {
            "project": project_text,
            "task": task_text,
            "cards": response.get("cards", []),
            "items": response.get("items", []),
            "usage_hint": (
                "Use this as durable project context. "
                "Prefer explicit memory facts over guessing."
            ),
        }
    )


async def stage_memory_candidates(
    candidates: list[dict[str, Any]],
    namespace: str = DEFAULT_NAMESPACE,
    ttl_seconds: int | None = 86400,
    client: MuninnClient | None = None,
) -> str:
    normalized, errors = _validate_candidates(candidates)
    if errors:
        return _json_text({"ok": False, "error": "invalid candidates", "details": errors})

    ttl: int | None
    if ttl_seconds is None:
        ttl = None
    else:
        ttl = _clamp(ttl_seconds, minimum=60, maximum=60 * 60 * 24 * 30)

    client = client or MuninnClient()
    response = await client.post_stage_candidates(
        namespace=_normalize_namespace(namespace),
        candidates=normalized,
        ttl_seconds=ttl,
    )
    return _json_text(response)


async def list_pending_memory(
    namespace: str = DEFAULT_NAMESPACE,
    entity_id: str | None = None,
    status: str = "pending",
    limit: int = 50,
    client: MuninnClient | None = None,
) -> str:
    client = client or MuninnClient()
    response = await client.post_list_pending(
        namespace=_normalize_namespace(namespace),
        entity_id=entity_id,
        status=str(status or "pending"),
        limit=_clamp(limit, minimum=1, maximum=100),
    )
    return _json_text(response)


async def confirm_memory_candidates(
    pending_ids: list[str],
    decision: str,
    note: str | None = None,
    namespace: str = DEFAULT_NAMESPACE,
    confirmation_phrase: str = "",
    client: MuninnClient | None = None,
) -> str:
    if confirmation_phrase != CONFIRMATION_PHRASE:
        return _json_text(
            {
                "ok": False,
                "error": "confirmation phrase required",
                "required_phrase": CONFIRMATION_PHRASE,
            }
        )
    if decision not in _DECISIONS:
        return _safe_error("decision must be accept or reject")
    if not isinstance(pending_ids, list) or not all(isinstance(item, str) for item in pending_ids):
        return _safe_error("pending_ids must be a list of strings")

    client = client or MuninnClient()
    response = await client.post_confirm_candidates(
        namespace=_normalize_namespace(namespace),
        pending_ids=pending_ids,
        decision=decision,
        decided_by="chatgpt_mcp",
        note=note,
    )
    return _json_text(response)


def get_mcp_tool_names() -> tuple[str, ...]:
    return TOOL_NAMES


def create_mcp_server(*, host: str | None = None, port: int | None = None) -> FastMCP:
    mcp = FastMCP(
        name=CONNECTOR_NAME,
        stateless_http=True,
        json_response=True,
        host=host or _host(),
        port=port or _port(),
        streamable_http_path=STREAMABLE_HTTP_PATH,
    )

    @mcp.tool(
        name="search",
        description="Search Muninn durable memory.",
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def search_tool(query: str) -> str:
        return await search(query)

    @mcp.tool(
        name="fetch",
        description="Fetch one exact Muninn memory item by id.",
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def fetch_tool(id: str) -> str:
        return await fetch(id)

    @mcp.tool(
        name="search_memory",
        description=(
            "Search Muninn memory with richer item output. Use this when the user asks "
            "what Muninn remembers, asks for prior durable memory, or asks to search "
            "project/user memory."
        ),
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def search_memory_tool(
        query: str,
        namespace: str = DEFAULT_NAMESPACE,
        entity_id: str | None = None,
        limit: int = 8,
    ) -> str:
        return await search_memory(query, namespace, entity_id, limit)

    @mcp.tool(
        name="fetch_memory",
        description="Fetch one exact Muninn memory item with rendered cards.",
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def fetch_memory_tool(memory_id: str, namespace: str = DEFAULT_NAMESPACE) -> str:
        return await fetch_memory(memory_id, namespace)

    @mcp.tool(
        name="rehydrate_project",
        description=(
            "Rehydrate durable context for a project and task. Use this when the user "
            "asks to recover durable context for a project, continue prior work, "
            "remember previous decisions, or rehydrate project state."
        ),
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def rehydrate_project_tool(
        project: str,
        task: str | None = None,
        namespace: str = DEFAULT_NAMESPACE,
        profile: str = DEFAULT_PROFILE,
        limit: int = 8,
    ) -> str:
        return await rehydrate_project(project, task, namespace, profile, limit)

    @mcp.tool(name="stage_memory_candidates", description="Stage proposed Muninn memory candidates.")
    async def stage_memory_candidates_tool(
        candidates: list[dict[str, Any]],
        namespace: str = DEFAULT_NAMESPACE,
        ttl_seconds: int | None = 86400,
    ) -> str:
        return await stage_memory_candidates(candidates, namespace, ttl_seconds)

    @mcp.tool(
        name="list_pending_memory",
        description="List staged Muninn memory candidates.",
        annotations=READ_ONLY_TOOL_ANNOTATIONS,
    )
    async def list_pending_memory_tool(
        namespace: str = DEFAULT_NAMESPACE,
        entity_id: str | None = None,
        status: str = "pending",
        limit: int = 50,
    ) -> str:
        return await list_pending_memory(namespace, entity_id, status, limit)

    @mcp.tool(
        name="confirm_memory_candidates",
        description="Accept or reject staged Muninn candidates with an explicit confirmation phrase.",
    )
    async def confirm_memory_candidates_tool(
        pending_ids: list[str],
        decision: str,
        note: str | None = None,
        namespace: str = DEFAULT_NAMESPACE,
        confirmation_phrase: str = "",
    ) -> str:
        return await confirm_memory_candidates(
            pending_ids,
            decision,
            note,
            namespace,
            confirmation_phrase,
        )

    return mcp


def main() -> None:
    mcp = create_mcp_server()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()

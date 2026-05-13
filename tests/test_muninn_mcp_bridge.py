from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from apps.muninn_mcp import server


class Recorder:
    def __init__(self, responses: dict[str, dict[str, Any]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict[str, Any] | None]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content.decode("utf-8")) if request.content else None
        self.calls.append((request.url.path, payload))
        response = self.responses.get(request.url.path, {})
        return httpx.Response(200, json=response, request=request)

    def client(self) -> server.MuninnClient:
        return server.MuninnClient(
            base_url="http://muninn.test",
            transport=httpx.MockTransport(self.handler),
        )


def run(coro):
    return asyncio.run(coro)


def parse(text: str) -> dict[str, Any]:
    return json.loads(text)


def mcp_tools_by_name() -> dict[str, Any]:
    mcp = server.create_mcp_server()
    return {tool.name: tool for tool in run(mcp.list_tools())}


def test_search_returns_valid_json_with_results() -> None:
    recorder = Recorder(
        {
            "/v0/memory/retrieve": {
                "items": [
                    {
                        "kind": "fact",
                        "id": "mem_1",
                        "entity_id": "project:mimir",
                        "text": "Mimir owns repository world-state.",
                        "confidence": 0.91,
                        "provenance": {"source_type": "user"},
                    }
                ]
            }
        }
    )

    payload = parse(run(server.search("Mimir", client=recorder.client())))

    assert payload["results"] == [
        {
            "id": "mem_1",
            "title": "Mimir owns repository world-state",
            "url": "muninn://memory/mem_1",
            "snippet": "Mimir owns repository world-state.",
        }
    ]
    assert recorder.calls[0][0] == "/v0/memory/retrieve"


def test_fetch_returns_exact_match_only_no_fuzzy_fallback() -> None:
    recorder = Recorder(
        {
            "/v0/memory/retrieve": {
                "items": [
                    {
                        "kind": "fact",
                        "id": "other",
                        "entity_id": "project:mimir",
                        "text": "This text mentions target-id but is not the exact id.",
                        "confidence": 0.8,
                        "provenance": {"source_type": "user"},
                    }
                ]
            }
        }
    )

    payload = parse(run(server.fetch("target-id", client=recorder.client())))

    assert payload["metadata"] == {"found": False}
    assert payload["title"] == "Not found"
    assert [call[0] for call in recorder.calls] == ["/v0/memory/retrieve"]


def test_fetch_not_found_returns_safe_json() -> None:
    recorder = Recorder({"/v0/memory/retrieve": {"items": []}})

    payload = parse(run(server.fetch("missing", client=recorder.client())))

    assert payload == {
        "id": "missing",
        "metadata": {"found": False},
        "text": "No exact Muninn memory item found for this id.",
        "title": "Not found",
        "url": "muninn://memory/missing",
    }


def test_search_memory_clamps_limit() -> None:
    recorder = Recorder({"/v0/memory/retrieve": {"items": []}})

    payload = parse(run(server.search_memory("x", limit=999, client=recorder.client())))

    assert payload == {"items": [], "count": 0}
    assert recorder.calls[0][1]["k"] == 20


def test_rehydrate_project_uses_rehydrate_and_friday_default() -> None:
    recorder = Recorder({"/v0/memory/rehydrate": {"cards": [], "items": []}})

    payload = parse(run(server.rehydrate_project("Mimir", client=recorder.client())))

    assert payload["project"] == "Mimir"
    assert recorder.calls == [
        (
            "/v0/memory/rehydrate",
            {
                "namespace": "default",
                "query": "Mimir",
                "entity_id": None,
                "k": 8,
                "profile": "friday",
                "query_embedding": None,
                "embedding_model": None,
            },
        )
    ]


def test_stage_memory_candidates_calls_only_stage_candidates() -> None:
    recorder = Recorder(
        {
            "/v0/memory/stage_candidates": {
                "accepted": 0,
                "pending": 1,
                "rejected": 0,
                "accepted_ids": [],
                "pending_ids": ["pending_1"],
            }
        }
    )
    candidate = {
        "kind": "fact",
        "entity": {"id": "project:muninn"},
        "payload": {"subject": "Muninn", "predicate": "owns", "object": "durable memory"},
        "confidence": 0.82,
        "provenance": {"source_type": "assistant", "source_id": "turn_1"},
    }

    payload = parse(
        run(server.stage_memory_candidates([candidate], client=recorder.client()))
    )

    assert payload["pending_ids"] == ["pending_1"]
    assert [call[0] for call in recorder.calls] == ["/v0/memory/stage_candidates"]
    sent = recorder.calls[0][1]["candidates"][0]
    assert sent["provenance"]["source_type"] == "tool"
    assert sent["provenance"]["source_id"] == "chatgpt_mcp"
    assert "write_mode=staged" in sent["provenance"]["note"]


def test_confirm_memory_candidates_refuses_without_exact_phrase() -> None:
    recorder = Recorder({"/v0/memory/confirm_candidates": {"processed": 1}})

    payload = parse(
        run(
            server.confirm_memory_candidates(
                ["pending_1"],
                "accept",
                confirmation_phrase="confirm muninn write",
                client=recorder.client(),
            )
        )
    )

    assert payload == {
        "ok": False,
        "error": "confirmation phrase required",
        "required_phrase": "CONFIRM MUNINN WRITE",
    }
    assert recorder.calls == []


def test_confirm_memory_candidates_calls_confirm_only_with_exact_phrase() -> None:
    recorder = Recorder(
        {
            "/v0/memory/confirm_candidates": {
                "namespace": "default",
                "decision": "accept",
                "processed": 1,
                "accepted_writes": 1,
                "rejected": 0,
                "missing": 0,
                "expired": 0,
                "accepted_ids": ["mem_1"],
            }
        }
    )

    payload = parse(
        run(
            server.confirm_memory_candidates(
                ["pending_1"],
                "accept",
                note="approved",
                confirmation_phrase="CONFIRM MUNINN WRITE",
                client=recorder.client(),
            )
        )
    )

    assert payload["processed"] == 1
    assert recorder.calls == [
        (
            "/v0/memory/confirm_candidates",
            {
                "namespace": "default",
                "pending_ids": ["pending_1"],
                "decision": "accept",
                "decided_by": "chatgpt_mcp",
                "note": "approved",
            },
        )
    ]


def test_no_mcp_tool_names_include_forbidden_fragments() -> None:
    forbidden = {
        "write_candidates",
        "direct_write",
        "upsert",
        "admin",
        "debug",
        "cleanup",
        "delete",
        "shell",
        "exec",
    }

    exposed = server.get_mcp_tool_names()

    assert set(exposed) == {
        "search",
        "fetch",
        "search_memory",
        "fetch_memory",
        "rehydrate_project",
        "stage_memory_candidates",
        "list_pending_memory",
        "confirm_memory_candidates",
    }
    assert not [name for name in exposed for fragment in forbidden if fragment in name]


def test_read_only_tools_expose_read_only_hint_annotations() -> None:
    tools = mcp_tools_by_name()

    for name in server.READ_ONLY_TOOL_NAMES:
        annotations = getattr(tools[name], "annotations", None)
        assert annotations is not None
        assert getattr(annotations, "readOnlyHint", None) is True

    write_tool_names = set(server.TOOL_NAMES) - set(server.READ_ONLY_TOOL_NAMES)
    for name in write_tool_names:
        annotations = getattr(tools[name], "annotations", None)
        assert getattr(annotations, "readOnlyHint", None) is not True


def test_memory_search_and_rehydrate_descriptions_include_selection_guidance() -> None:
    tools = mcp_tools_by_name()

    assert "what Muninn remembers" in tools["search_memory"].description
    assert "prior durable memory" in tools["search_memory"].description
    assert "recover durable context for a project" in tools["rehydrate_project"].description
    assert "continue prior work" in tools["rehydrate_project"].description


def test_adapter_rejects_forbidden_routes() -> None:
    recorder = Recorder(
        {
            "/health": {"ok": True},
            "/v0/memory/version": {"version": "0.11.0"},
            "/v0/memory/retrieve": {"items": []},
            "/v0/memory/rehydrate": {"cards": [], "items": []},
            "/v0/memory/render_cards": {"cards": []},
            "/v0/memory/stage_candidates": {"pending": 0},
            "/v0/memory/list_pending": {"items": []},
            "/v0/memory/confirm_candidates": {"processed": 0},
        }
    )
    client = recorder.client()

    run(client.get_health())
    run(client.get_version())
    run(client.post_retrieve(query="x"))
    run(client.post_rehydrate(query="x"))
    run(client.post_render_cards(items=[]))
    run(client.post_stage_candidates(candidates=[]))
    run(client.post_list_pending())
    run(
        client.post_confirm_candidates(
            pending_ids=[],
            decision="reject",
            decided_by="chatgpt_mcp",
        )
    )

    assert {path for path, _ in recorder.calls}.isdisjoint(
        {
            "/v0/memory/write_candidates",
            "/v0/memory/upsert_embeddings",
            "/v0/admin/cleanup",
            "/v0/debug/stats",
        }
    )
    with pytest.raises(ValueError):
        run(client._request_json("POST", "/v0/memory/write_candidates", json_payload={}))
    with pytest.raises(ValueError):
        run(client._request_json("POST", "/v0/memory/upsert_embeddings", json_payload={}))
    with pytest.raises(ValueError):
        run(client._request_json("GET", "/v0/admin/cleanup"))
    with pytest.raises(ValueError):
        run(client._request_json("GET", "/v0/debug/stats"))

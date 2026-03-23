from __future__ import annotations

import json

import pytest

pytest.importorskip("mcp")

from muninn.human_memory.adaptation import adaptation_card_upsert
from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.mcp_server import (
    AdaptationQueryInput,
    LensInput,
    _collect_adaptation_cards,
    _handle_tool_exception,
)


def _init_conn(tmp_path):
    db_path = tmp_path / "mcp_adaptation_query.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:mcpadapt12345678",
        label="mcp-adapt",
        meta_json=json.dumps({"root_path": "/tmp/mcp-adapt"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return conn, resolved.key


def test_collect_adaptation_cards_obeys_scope_order_and_shape(tmp_path) -> None:
    conn, repo_key = _init_conn(tmp_path)
    subject_id = "client_scope_order"

    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        memory_type="preference.direct",
        subject_id=subject_id,
        category="voice",
        scope={"type": "campaign"},
        persistence="durable",
        source_type="direct_feedback",
        title="Repo-scoped durable preference",
        summary="Repo preference summary",
        body="Repo preference body",
    )
    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key="global",
        memory_type="preference.direct",
        subject_id=subject_id,
        category="voice",
        scope={"type": "global"},
        persistence="durable",
        source_type="direct_feedback",
        title="Global durable preference",
        summary="Global preference summary",
        body="Global preference body",
    )

    lens = LensInput(space_key=repo_key, scope="soft")
    query = AdaptationQueryInput(
        subject_id=subject_id,
        view="durable_preferences",
        limit=5,
    )
    payload = _collect_adaptation_cards(conn, lens, query)
    assert payload["counts"]["total"] == 2
    assert payload["cards"][0]["space_key"] == repo_key
    assert payload["cards"][1]["space_key"] == "global"
    assert "body" not in payload["cards"][0]
    assert payload["filters"]["view"] == "durable_preferences"
    conn.close()


def test_handle_tool_exception_maps_value_error_to_invalid_arguments() -> None:
    err = _handle_tool_exception(ValueError("invalid_search_query:no_terms"))
    assert err["error"]["code"] == "InvalidArguments"
    assert "invalid_search_query:no_terms" in err["error"]["details"]["error"]

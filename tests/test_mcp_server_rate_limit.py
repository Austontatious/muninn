from __future__ import annotations

import json

from muninn.human_memory.bootstrap import (
    DEFAULT_CLIENT_NAME,
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from muninn.human_memory.cards import card_upsert
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.mcp_server import (
    _count_recent_card_creates,
    _resolve_mcp_card_write_limit_per_hour,
    _resolve_mcp_card_write_window_seconds,
    _resolve_mcp_enable_slash_aliases,
    _resolve_mcp_suppress_alias_warnings,
)


def test_count_recent_card_creates_scoped_by_space_and_client(tmp_path) -> None:
    db_path = tmp_path / "human_memory_rate_limit.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    space_a = ResolvedSpace(
        key="repo:aaaaaaaaaaaaaaaa",
        label="repo-a",
        meta_json=json.dumps({"root_path": "/tmp/a"}, separators=(",", ":")),
    )
    space_b = ResolvedSpace(
        key="repo:bbbbbbbbbbbbbbbb",
        label="repo-b",
        meta_json=json.dumps({"root_path": "/tmp/b"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=space_a)
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=space_b)

    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_a.key,
        kind="note",
        title="A1",
        summary="A1",
        body="A1",
        created_by_client_name=DEFAULT_CLIENT_NAME,
    )
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_a.key,
        kind="note",
        title="A2",
        summary="A2",
        body="A2",
        created_by_client_name=DEFAULT_CLIENT_NAME,
    )
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_b.key,
        kind="note",
        title="B1",
        summary="B1",
        body="B1",
        created_by_client_name=DEFAULT_CLIENT_NAME,
    )
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_a.key,
        kind="note",
        title="A3",
        summary="A3",
        body="A3",
        created_by_client_name="other-client",
    )

    count_space_a = _count_recent_card_creates(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_a.key,
        client_name=DEFAULT_CLIENT_NAME,
        window_seconds=3600,
    )
    count_space_b = _count_recent_card_creates(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_b.key,
        client_name=DEFAULT_CLIENT_NAME,
        window_seconds=3600,
    )
    count_other_client = _count_recent_card_creates(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_a.key,
        client_name="other-client",
        window_seconds=3600,
    )
    assert count_space_a == 2
    assert count_space_b == 1
    assert count_other_client == 1
    conn.close()


def test_rate_limit_env_parsing(monkeypatch) -> None:
    monkeypatch.delenv("MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR", raising=False)
    monkeypatch.delenv("MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS", raising=False)
    monkeypatch.delenv("MUNINN_MCP_ENABLE_SLASH_ALIASES", raising=False)
    monkeypatch.delenv("MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS", raising=False)
    assert _resolve_mcp_card_write_limit_per_hour() == 20
    assert _resolve_mcp_card_write_window_seconds() == 3600
    assert _resolve_mcp_enable_slash_aliases() is True
    assert _resolve_mcp_suppress_alias_warnings() is True

    monkeypatch.setenv("MUNINN_MCP_CARD_WRITE_LIMIT_PER_HOUR", "0")
    monkeypatch.setenv("MUNINN_MCP_CARD_WRITE_WINDOW_SECONDS", "15")
    monkeypatch.setenv("MUNINN_MCP_ENABLE_SLASH_ALIASES", "0")
    monkeypatch.setenv("MUNINN_MCP_SUPPRESS_ALIAS_WARNINGS", "false")
    assert _resolve_mcp_card_write_limit_per_hour() == 0
    assert _resolve_mcp_card_write_window_seconds() == 15
    assert _resolve_mcp_enable_slash_aliases() is False
    assert _resolve_mcp_suppress_alias_warnings() is False

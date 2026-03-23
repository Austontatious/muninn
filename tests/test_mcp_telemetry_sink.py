from __future__ import annotations

import json

from muninn import mcp_server
from muninn import telemetry


def _reset_sink_state() -> None:
    telemetry.reset_telemetry_state()


def test_jsonl_telemetry_writes_tool_event(monkeypatch, tmp_path) -> None:
    sink_path = tmp_path / "mcp_telemetry.jsonl"
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_PATH", str(sink_path))
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_FLUSH", "1")
    _reset_sink_state()

    mcp_server._log_tool_invocation(
        "muninn.cards.search",
        status="ok",
        scope="soft",
        space_keys=["repo:abc", "global"],
        query="belize bowie restaurant",
        results=1,
        total_matches=2,
        top_score=0.72,
        duration_ms=12,
    )

    lines = sink_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event"] == "tool_call"
    assert row["tool"] == "muninn.cards.search"
    assert row["invoked_as"] == "muninn.cards.search"
    assert row["deprecated_alias"] is False
    assert row["scope"] == "soft"
    assert row["total_matches"] == 2
    assert row["top_score"] == 0.72
    assert row["duration_ms"] == 12


def test_jsonl_telemetry_invalid_path_warns_and_falls_back_to_console(monkeypatch, capsys) -> None:
    # /proc is unwritable for regular users; file sink should warn once and keep console logging.
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_PATH", "/proc/1/muninn_telemetry.jsonl")
    monkeypatch.delenv("MUNINN_MCP_TELEMETRY_FLUSH", raising=False)
    _reset_sink_state()

    mcp_server._log_tool_invocation(
        "muninn.cards.recent",
        status="ok",
        scope="strict",
        cards=5,
        duration_ms=9,
    )
    mcp_server._log_tool_invocation(
        "muninn.cards.recent",
        status="ok",
        scope="strict",
        cards=4,
        duration_ms=8,
    )

    captured = capsys.readouterr()
    assert telemetry.telemetry_context()["telemetry_file_state"] == "file_unavailable"
    assert captured.err.count("Muninn telemetry warning:") == 1


def test_jsonl_telemetry_rotates_with_backups(monkeypatch, tmp_path) -> None:
    sink_path = tmp_path / "mcp_telemetry.jsonl"
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_PATH", str(sink_path))
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_FLUSH", "1")
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_MAX_BYTES", "200")
    monkeypatch.setenv("MUNINN_MCP_TELEMETRY_BACKUP_COUNT", "2")
    _reset_sink_state()

    for idx in range(6):
        mcp_server._log_tool_invocation(
            "muninn.cards.search",
            status="ok",
            scope="soft",
            request_id=f"req-{idx}",
            query="checkpoint audit batching",
            duration_ms=idx + 1,
        )

    backups = sorted(tmp_path.glob("mcp_telemetry.jsonl*"))
    assert sink_path in backups
    assert (tmp_path / "mcp_telemetry.jsonl.1").exists()
    assert telemetry.telemetry_context()["telemetry_backup_count"] == 2

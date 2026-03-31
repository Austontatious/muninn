from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

from muninn import cli


def _make_args(
    *,
    telemetry_path: Path,
    as_json: bool = True,
    since: str | None = None,
    last: str = "1h",
    unit: str = "muninn-mcp.service",
    limit: int = 5000,
) -> argparse.Namespace:
    return argparse.Namespace(
        telemetry_path=str(telemetry_path),
        as_json=as_json,
        since=since,
        last=last,
        unit=unit,
        limit=limit,
    )


def test_audit_uses_jsonl_when_present(tmp_path, capsys) -> None:
    telemetry_path = tmp_path / "mcp_telemetry.jsonl"
    now = time.time()
    rows = [
        {
            "ts": now,
            "event": "tool_call",
            "tool": "muninn.spaces.resolve",
            "status": "ok",
            "duration_ms": 10,
            "space_key": "repo:abc",
        },
        {
            "ts": now + 1,
            "event": "tool_call",
            "tool": "muninn.cards.recent",
            "status": "ok",
            "scope": "strict",
            "cards": 5,
            "duration_ms": 14,
            "space_keys": ["repo:abc"],
        },
        {
            "ts": now + 2,
            "event": "tool_call",
            "tool": "muninn.cards.search",
            "status": "ok",
            "scope": "soft",
            "query": "belize bowie restaurant reference",
            "total_matches": 3,
            "top_score": 0.81,
            "duration_ms": 21,
            "space_keys": ["repo:abc", "global"],
        },
        {
            "ts": now + 3,
            "event": "tool_call",
            "tool": "muninn.cards.upsert",
            "status": "ok",
            "scope": "strict",
            "space_key": "repo:abc",
            "card_id": "card-1",
            "summary_chars": 120,
            "warning_codes": ["missing_evidence"],
            "duration_ms": 16,
        },
    ]
    telemetry_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    code = cli._cmd_audit(_make_args(telemetry_path=telemetry_path))
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["source"] == "jsonl"
    assert payload["events_analyzed"] == 4
    assert payload["discipline"]["ordered_start_rate"] == 1.0
    assert payload["discipline"]["staged_start_rate"] == 1.0
    assert payload["discipline"]["bundle_first_rate"] == 0.0
    assert payload["summary"]["staged_start_sessions"] == 1
    assert payload["summary"]["bundle_first_sessions"] == 0
    assert payload["write_hygiene"]["missing_evidence_warning_count"] == 1


def test_audit_counts_bundle_first_session_as_compliant(tmp_path, capsys) -> None:
    telemetry_path = tmp_path / "mcp_telemetry.jsonl"
    now = time.time()
    rows = [
        {
            "ts": now,
            "event": "tool_call",
            "tool": "muninn.rehydrate.bundle",
            "status": "ok",
            "scope": "soft",
            "duration_ms": 18,
            "result_count": 4,
        },
        {
            "ts": now + 1,
            "event": "tool_call",
            "tool": "muninn.cards.upsert",
            "status": "ok",
            "scope": "strict",
            "space_key": "repo:abc",
            "card_id": "card-2",
            "summary_chars": 96,
            "duration_ms": 12,
        },
    ]
    telemetry_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    code = cli._cmd_audit(_make_args(telemetry_path=telemetry_path))
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["discipline"]["ordered_start_rate"] == 1.0
    assert payload["discipline"]["staged_start_rate"] == 0.0
    assert payload["discipline"]["bundle_first_rate"] == 1.0
    assert payload["summary"]["ordered_start_sessions"] == 1
    assert payload["summary"]["bundle_first_sessions"] == 1
    assert payload["summary"]["partial_start_sessions"] == 0


def test_audit_partial_start_session_remains_non_compliant(tmp_path, capsys) -> None:
    telemetry_path = tmp_path / "mcp_partial_telemetry.jsonl"
    now = time.time()
    rows = [
        {
            "ts": now,
            "event": "tool_call",
            "tool": "muninn.spaces.resolve",
            "status": "ok",
            "duration_ms": 10,
            "space_key": "repo:abc",
        },
        {
            "ts": now + 1,
            "event": "tool_call",
            "tool": "muninn.cards.search",
            "status": "ok",
            "scope": "soft",
            "query": "repo constraints",
            "total_matches": 1,
            "top_score": 0.66,
            "duration_ms": 14,
        },
    ]
    telemetry_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    code = cli._cmd_audit(_make_args(telemetry_path=telemetry_path))
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["discipline"]["ordered_start_rate"] == 0.0
    assert payload["discipline"]["staged_start_rate"] == 0.0
    assert payload["discipline"]["bundle_first_rate"] == 0.0
    assert payload["summary"]["partial_start_sessions"] == 1


def test_audit_falls_back_to_journal(monkeypatch, tmp_path, capsys) -> None:
    telemetry_path = tmp_path / "missing.jsonl"
    now = round(time.time(), 3)
    stdout = "\n".join(
        [
            f"MCP_TOOL {json.dumps({'ts': now, 'tool': 'muninn.spaces.resolve', 'status': 'ok'})}",
            (
                "MCP_TOOL "
                + json.dumps(
                    {
                        "ts": now + 1,
                        "tool": "muninn.cards.search",
                        "status": "ok",
                        "scope": "soft",
                        "query": "repo constraints",
                        "total_matches": 1,
                        "top_score": 0.66,
                    }
                )
            ),
        ]
    )

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    code = cli._cmd_audit(_make_args(telemetry_path=telemetry_path))
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["source"] == "journalctl"
    assert payload["events_analyzed"] == 2
    assert payload["discipline"]["ordered_start_rate"] == 0.0


def test_audit_prints_actionable_message_when_no_source(monkeypatch, tmp_path, capsys) -> None:
    telemetry_path = tmp_path / "missing.jsonl"

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("journalctl not found")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    code = cli._cmd_audit(_make_args(telemetry_path=telemetry_path, as_json=False))
    captured = capsys.readouterr()
    assert code == 1
    assert "No telemetry events found." in captured.err
    assert "MUNINN_MCP_TELEMETRY_PATH" in captured.err

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main


def _compact_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.execute("PRAGMA journal_mode=DELETE;")
    for suffix in ["-wal", "-shm"]:
        path = Path(str(db_path) + suffix)
        if path.exists():
            path.unlink()


def _seed_shadow_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "replay_gate_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    for card in [
        MemoryCard(
            id="card-current",
            kind="decision",
            title="Replay gate current state",
            summary="The bridge replay gate validates audit traces and required context.",
            body="Live cutover remains blocked while shadow consumption is tested.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/reports/replay.md:1")],
        ),
        MemoryCard(
            id="card-boundary",
            kind="constraint",
            title="Replay gate safety boundary",
            summary="Adaptive retrieval is opt-in and never default.",
            body="Writes remain disabled for shadow bridge operations.",
            scope_key="repo:test",
            updated_at="2026-05-17T11:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/AGENTS.md:1")],
        ),
    ]:
        store.create_card(card)
        store.upsert_reinforcement_state(
            {
                "schema_version": "muninn.v2.recall_reinforcement.v1",
                "record_type": "muninn_v2_reinforcement_state",
                "record_id": card.id,
                "scope_key": "repo:test",
                "status": "preserved",
                "effective_score": 1.0,
                "last_event_at": "2026-05-17T12:00:00Z",
                "computed_at": "2026-05-17T12:01:00Z",
                "explanation": ["test replay gate state"],
            }
        )
    _compact_db(db_path)
    return db_path


def _seed_shadow_db_without_evidence(tmp_path: Path) -> Path:
    db_path = tmp_path / "replay_gate_no_evidence_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    card = MemoryCard(
        id="card-current",
        kind="decision",
        title="Replay gate current state",
        summary="The bridge replay gate validates audit traces for sparse projects.",
        body="Sparse projects may lack evidence refs but still need replayable context.",
        scope_key="repo:test",
        updated_at="2026-05-17T12:00:00Z",
    )
    store.create_card(card)
    store.upsert_reinforcement_state(
        {
            "schema_version": "muninn.v2.recall_reinforcement.v1",
            "record_type": "muninn_v2_reinforcement_state",
            "record_id": card.id,
            "scope_key": "repo:test",
            "status": "preserved",
            "effective_score": 1.0,
            "last_event_at": "2026-05-17T12:00:00Z",
            "computed_at": "2026-05-17T12:01:00Z",
            "explanation": ["test replay gate state"],
        }
    )
    _compact_db(db_path)
    return db_path


def _drill_fixture(tmp_path: Path, db_path: Path) -> Path:
    fixture = {
        "schema_version": "muninn.v2.bridge_ops_drill_fixture.v1",
        "name": "replay gate test drill",
        "version": 1,
        "defaults": {
            "min_coverage": 1.0,
            "require_all_required": True,
            "budget_max_context_chars": 1600,
            "budget_min_coverage": 0.5,
            "ignored_overinclude_terms": ["replay", "gate", "bridge"],
        },
        "pilots": [
            {
                "id": "gate-test",
                "project": "GateTest",
                "v2_db": str(db_path),
                "space_key": "repo:test",
                "project_path": "/tmp/gate-test",
                "consumer_id": "codex-shadow",
                "policy": {
                    "schema_version": "BridgeCapabilityPolicyV1",
                    "consumer_id": "codex-shadow",
                    "allowed_operations": ["health", "search", "rehydrate", "explain"],
                    "allowed_space_keys": ["repo:test"],
                    "allowed_project_paths": ["/tmp/gate-test"],
                    "max_results": 4,
                    "max_context_chars": 2400,
                    "allow_adaptive_scoring": False,
                    "allow_reinforcement_read": True,
                    "allow_reinforcement_write": False,
                    "allow_cross_project": False,
                    "require_evidence": True,
                    "require_explanations": True,
                    "audit_log_required": True,
                },
                "request_defaults": {
                    "limit": 4,
                    "primary_limit": 2,
                    "max_context_chars": 2400,
                    "retrieval_mode": "hybrid",
                    "include_evidence": True,
                    "include_explanations": True,
                    "recent_supplement": True,
                    "strict": True,
                },
                "sessions": [
                    {
                        "id": "gate-session",
                        "continuity_needs": [
                            {
                                "id": "current-continuity",
                                "card_ids": ["card-current"],
                            }
                        ],
                        "tasks": [
                            {
                                "id": "validate",
                                "query": "validate replay gate current state and safety boundary",
                                "v1_context": "The replay gate validates audit traces and keeps adaptive retrieval opt-in.",
                                "expected_needs": [
                                    {
                                        "id": "audit-traces",
                                        "all_terms": ["audit traces"],
                                        "card_ids": ["card-current"],
                                    },
                                    {
                                        "id": "adaptive-boundary",
                                        "all_terms": ["Adaptive retrieval"],
                                        "card_ids": ["card-boundary"],
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }
    path = tmp_path / "drill_fixture.json"
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _drill_fixture_without_required_evidence(tmp_path: Path, db_path: Path) -> Path:
    fixture = json.loads(_drill_fixture(tmp_path, db_path).read_text(encoding="utf-8"))
    pilot = fixture["pilots"][0]
    pilot["policy"]["require_evidence"] = False
    pilot["request_defaults"]["primary_limit"] = 1
    task = pilot["sessions"][0]["tasks"][0]
    task["expected_needs"] = [
        {
            "id": "sparse-current-state",
            "all_terms": ["sparse projects"],
            "card_ids": ["card-current"],
        }
    ]
    task["v1_context"] = "Sparse projects may lack evidence refs but still need replayable context."
    path = tmp_path / "drill_fixture_no_evidence.json"
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _write_v1_safety(tmp_path: Path) -> Path:
    path = tmp_path / "v1_safety.json"
    path.write_text(
        json.dumps(
            {
                "row_counts_changed": False,
                "size_changed": False,
                "mtime_changed": False,
                "rows": [{"table": "cards", "before": 1, "after": 1, "changed": False}],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_bridge_replay_gate_validates_drill_and_failure_drills(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = _seed_shadow_db(tmp_path)
    fixture = _drill_fixture(tmp_path, db_path)
    safety = _write_v1_safety(tmp_path)

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("bridge-replay-gate attempted to open v1")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)
    assert main(["bridge-ops-drill", "--fixture", str(fixture), "--out-dir", str(tmp_path / "drill")]) == 0
    capsys.readouterr()

    code = main(
        [
            "bridge-replay-gate",
            "--drill-report",
            str(tmp_path / "drill" / "bridge_ops_drill_report.json"),
            "--v1-safety",
            str(safety),
            "--out-dir",
            str(tmp_path / "gate"),
            "--run-failure-drills",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report = json.loads((tmp_path / "gate" / "bridge_replay_gate_report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert payload["mode"] == "bridge_replay_gate"
    assert payload["technical_replay_gate"] == "GO"
    assert payload["live_shadow_trial"] == "NO-GO"
    assert report["status"]["live_cutover"] == "NO-GO"
    assert report["status"]["writes"] == "NO-GO"
    assert report["status"]["adaptive_default"] == "NO-GO"
    assert report["summary"]["failed"] == 0
    assert report["summary"]["failure_drills"] == 7
    assert report["summary"]["failure_drills_detected"] == 7
    assert all(item["detected"] for item in report["failure_drills"])
    assert (tmp_path / "gate" / "bridge_replay_gate_report.md").exists()
    assert not Path(str(db_path) + "-wal").exists()
    assert not Path(str(db_path) + "-shm").exists()


def test_bridge_replay_gate_failure_drills_cover_optional_evidence_policies(tmp_path: Path, capsys) -> None:
    db_path = _seed_shadow_db_without_evidence(tmp_path)
    fixture = _drill_fixture_without_required_evidence(tmp_path, db_path)
    safety = _write_v1_safety(tmp_path)

    assert main(["bridge-ops-drill", "--fixture", str(fixture), "--out-dir", str(tmp_path / "drill")]) == 0
    capsys.readouterr()

    code = main(
        [
            "bridge-replay-gate",
            "--drill-report",
            str(tmp_path / "drill" / "bridge_ops_drill_report.json"),
            "--v1-safety",
            str(safety),
            "--out-dir",
            str(tmp_path / "gate"),
            "--run-failure-drills",
        ]
    )

    report = json.loads((tmp_path / "gate" / "bridge_replay_gate_report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert report["status"]["technical_replay_gate"] == "GO"
    assert report["summary"]["failure_drills_detected"] == 7
    assert all(item["detected"] for item in report["failure_drills"])


def test_bridge_replay_gate_fails_when_v1_safety_missing(tmp_path: Path, capsys) -> None:
    db_path = _seed_shadow_db(tmp_path)
    fixture = _drill_fixture(tmp_path, db_path)
    assert main(["bridge-ops-drill", "--fixture", str(fixture), "--out-dir", str(tmp_path / "drill")]) == 0
    capsys.readouterr()

    code = main(
        [
            "bridge-replay-gate",
            "--drill-report",
            str(tmp_path / "drill" / "bridge_ops_drill_report.json"),
            "--out-dir",
            str(tmp_path / "gate"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report = json.loads((tmp_path / "gate" / "bridge_replay_gate_report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert payload["technical_replay_gate"] == "NO-GO"
    assert any(item["name"] == "v1_untouched" and not item["ok"] for item in report["gates"])

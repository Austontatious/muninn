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
    db_path = tmp_path / "ops_drill_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    cards = [
        MemoryCard(
            id="card-current",
            kind="decision",
            title="Ops drill current project state",
            summary="The shadow bridge provides replayable project context with audit traces.",
            body="Agents should continue the project using v2 shadow context only.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/reports/ops.md:10")],
        ),
        MemoryCard(
            id="card-runbook",
            kind="runbook",
            title="Ops drill runbook",
            summary="Use bridge-request artifacts and rendered context blocks for operator review.",
            body="Budget pressure should preserve primary project state before supplements.",
            scope_key="repo:test",
            updated_at="2026-05-17T11:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/RUNBOOK.md:20")],
        ),
        MemoryCard(
            id="card-boundary",
            kind="constraint",
            title="Ops drill safety boundary",
            summary="Live cutover remains NO-GO and adaptive retrieval is never default.",
            body="The drill is shadow-only and read-only.",
            scope_key="repo:test",
            updated_at="2026-05-17T10:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/AGENTS.md:1")],
        ),
    ]
    for card in cards:
        store.create_card(card)
        store.upsert_reinforcement_state(
            {
                "schema_version": "muninn.v2.recall_reinforcement.v1",
                "record_type": "muninn_v2_reinforcement_state",
                "record_id": card.id,
                "scope_key": "repo:test",
                "status": "boosted" if card.id != "card-boundary" else "preserved",
                "effective_score": 1.75,
                "last_event_at": "2026-05-17T12:00:00Z",
                "computed_at": "2026-05-17T12:01:00Z",
                "explanation": ["offline drill fixture state"],
            }
        )
    _compact_db(db_path)
    return db_path


def _fixture(tmp_path: Path, db_path: Path) -> Path:
    fixture = {
        "schema_version": "muninn.v2.bridge_ops_drill_fixture.v1",
        "name": "test bridge ops drill",
        "version": 1,
        "defaults": {
            "min_coverage": 0.8,
            "require_all_required": True,
            "budget_max_context_chars": 1600,
            "budget_min_coverage": 0.5,
            "ignored_overinclude_terms": ["ops", "drill", "project", "context"],
        },
        "pilots": [
            {
                "id": "ops-test",
                "project": "OpsTest",
                "v2_db": str(db_path),
                "space_key": "repo:test",
                "project_path": "/tmp/ops-test",
                "consumer_id": "codex-shadow",
                "policy": {
                    "schema_version": "BridgeCapabilityPolicyV1",
                    "consumer_id": "codex-shadow",
                    "allowed_operations": ["health", "search", "rehydrate", "explain"],
                    "allowed_space_keys": ["repo:test"],
                    "allowed_project_paths": ["/tmp/ops-test"],
                    "max_results": 6,
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
                        "id": "multi-turn-shadow",
                        "continuity_needs": [
                            {
                                "id": "continuity-current-state",
                                "description": "Current state survives multiple tasks.",
                                "card_ids": ["card-current"],
                            }
                        ],
                        "tasks": [
                            {
                                "id": "resume",
                                "query": "resume ops drill current project state",
                                "v1_context": "The current project state uses shadow bridge context with audit traces.",
                                "expected_needs": [
                                    {
                                        "id": "current-state",
                                        "description": "Project current state is present.",
                                        "all_terms": ["current project state"],
                                        "card_ids": ["card-current"],
                                    },
                                    {
                                        "id": "audit-traces",
                                        "description": "Audit trace behavior is visible.",
                                        "all_terms": ["audit traces"],
                                    },
                                ],
                            },
                            {
                                "id": "operate",
                                "query": "continue ops drill runbook with shadow only safety boundary",
                                "v1_context": "The runbook requires rendered context blocks and live cutover remains NO-GO.",
                                "expected_needs": [
                                    {
                                        "id": "runbook",
                                        "description": "Runbook is included.",
                                        "all_terms": ["rendered context blocks"],
                                        "card_ids": ["card-runbook"],
                                    },
                                    {
                                        "id": "safety-boundary",
                                        "description": "No live cutover boundary is included.",
                                        "all_terms": ["live cutover"],
                                        "card_ids": ["card-boundary"],
                                    },
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    }
    path = tmp_path / "bridge_ops_fixture.json"
    path.write_text(json.dumps(fixture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_bridge_ops_drill_cli_runs_longitudinal_modes_without_v1(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = _seed_shadow_db(tmp_path)
    fixture_path = _fixture(tmp_path, db_path)

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("bridge-ops-drill attempted to open v1")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)
    code = main(
        [
            "bridge-ops-drill",
            "--fixture",
            str(fixture_path),
            "--out-dir",
            str(tmp_path / "drill"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report = json.loads((tmp_path / "drill" / "bridge_ops_drill_report.json").read_text(encoding="utf-8"))
    assert code == 0
    assert payload["mode"] == "bridge_ops_drill"
    assert payload["bridge_shadow_consumption"] == "GO"
    assert report["status"] == {
        "adaptive_default": "NO-GO",
        "bridge_shadow_consumption": "GO",
        "live_cutover": "NO-GO",
        "writes": "NO-GO",
    }
    assert report["summary"]["tasks"] == 2
    assert report["summary"]["mode_runs"] == 6
    assert report["summary"]["adaptive_on_enabled"] == 2
    assert report["summary"]["adaptive_default_enabled"] == 0
    assert report["summary"]["audit_replay_failures"] == 0
    assert report["summary"]["contamination_denied"] == report["summary"]["contamination_checks"]
    assert (tmp_path / "drill" / "operator_review_notes.md").exists()
    assert list((tmp_path / "drill" / "rendered_context_blocks").glob("*.md"))
    assert not Path(str(db_path) + "-wal").exists()
    assert not Path(str(db_path) + "-shm").exists()

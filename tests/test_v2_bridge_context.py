from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from jsonschema import Draft202012Validator

from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.bridge import (
    BRIDGE_REQUEST_CONTRACT_VERSION,
    BRIDGE_REQUEST_SCHEMA_VERSION,
    BridgePolicyError,
    validate_bridge_request,
)
from muninn.v2.cli import main


REPO_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_REQUEST_SCHEMA_PATH = (
    REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/schemas/bridge-request.v1.schema.json"
)
BRIDGE_REQUEST_FIXTURE_PATH = (
    REPO_ROOT
    / "docs/contracts/muninn_v2_bridge/v1/examples/valid/bridge-request.read-only-context.v1.json"
)
REHYDRATE_RESPONSE_SCHEMA_PATH = (
    REPO_ROOT / "docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json"
)


def _validate_json(schema_path: Path, payload: dict) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _seed_v2_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "shadow_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    store.create_card(
        MemoryCard(
            id="bridge-primary",
            kind="decision",
            title="Friday bridge context contract",
            summary="The bridge returns read-only RehydrateResponseV1 context.",
            body="Use explicit v2 DB input and audit the read-only boundary.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/docs/bridge.md:10")],
        )
    )
    store.create_card(
        MemoryCard(
            id="bridge-supplement",
            kind="runbook",
            title="Friday shadow preview command",
            summary="Shadow previews combine primary retrieval and recent supplements.",
            scope_key="repo:test",
            updated_at="2026-05-17T11:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/RUNBOOK.md:4")],
        )
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.execute("PRAGMA journal_mode=DELETE;")
    for suffix in ["-wal", "-shm"]:
        path = Path(str(db_path) + suffix)
        if path.exists():
            path.unlink()
    return db_path


def _bridge_request(db_path: Path) -> dict:
    return {
        "schema_version": BRIDGE_REQUEST_SCHEMA_VERSION,
        "contract_version": BRIDGE_REQUEST_CONTRACT_VERSION,
        "request_id": "test_bridge_context",
        "capability": {"name": "read_only_context", "version": BRIDGE_REQUEST_CONTRACT_VERSION},
        "source": {
            "v2_db": str(db_path),
            "space_key": "repo:test",
            "project_path": None,
        },
        "query": {"text": "Friday bridge context contract"},
        "options": {
            "limit": 2,
            "primary_limit": 1,
            "recent_limit": 1,
            "retrieval_mode": "hybrid",
            "include_evidence": True,
            "include_explanations": True,
            "max_chars": None,
            "recent_supplement": True,
            "strict": True,
        },
        "safety": {
            "allow_writes": False,
            "allow_v1_access": False,
            "allow_reinforcement_events": False,
            "adaptive_retrieval": False,
            "allow_llm": False,
            "dry_run": True,
        },
    }


def test_bridge_request_v1_fixture_matches_schema() -> None:
    fixture = json.loads(BRIDGE_REQUEST_FIXTURE_PATH.read_text(encoding="utf-8"))
    _validate_json(BRIDGE_REQUEST_SCHEMA_PATH, fixture)
    assert fixture["schema_version"] == BRIDGE_REQUEST_SCHEMA_VERSION
    assert fixture["contract_version"] == BRIDGE_REQUEST_CONTRACT_VERSION
    assert fixture["capability"]["name"] == "read_only_context"


def test_bridge_context_requires_explicit_args(tmp_path: Path) -> None:
    assert main(["bridge-context", "--out-dir", str(tmp_path)]) == 2
    assert main(["bridge-context", "--request", str(tmp_path / "missing.json")]) == 2


def test_bridge_rejects_unsafe_capabilities(tmp_path: Path) -> None:
    db_path = _seed_v2_db(tmp_path)
    request = _bridge_request(db_path)
    request["safety"]["allow_writes"] = True

    try:
        validate_bridge_request(request)
    except BridgePolicyError as exc:
        assert str(exc) == "bridge_writes_forbidden"
    else:
        raise AssertionError("unsafe bridge request was accepted")


def test_bridge_context_cli_writes_rehydrate_response_markdown_and_audit(tmp_path: Path, capsys) -> None:
    db_path = _seed_v2_db(tmp_path)
    request = _bridge_request(db_path)
    request_path = tmp_path / "bridge_request.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    out_dir = tmp_path / "bridge_out"

    code = main(["bridge-context", "--request", str(request_path), "--out-dir", str(out_dir)])

    payload = json.loads(capsys.readouterr().out)
    response = json.loads((out_dir / "bridge_rehydrate_response.json").read_text(encoding="utf-8"))
    audit = json.loads((out_dir / "bridge_audit_log.json").read_text(encoding="utf-8"))
    markdown = (out_dir / "bridge_context.md").read_text(encoding="utf-8")
    _validate_json(REHYDRATE_RESPONSE_SCHEMA_PATH, response)
    assert code == 0
    assert payload["mode"] == "bridge_context"
    assert payload["decision"] == "go_read_only_bridge"
    assert payload["read_only_ok"] is True
    assert response["record_type"] == "muninn_v2_rehydrate_response"
    assert response["request"]["query"]["text"] == "Friday bridge context contract"
    assert response["selected_memory"]["cards"]
    assert response["selected_memory"]["evidence"]
    assert response["explanations"]["included"] is True
    assert audit["record_type"] == "muninn_v2_bridge_context_audit"
    assert audit["safety"]["v1_accessed"] is False
    assert audit["safety"]["v1_mutated"] is False
    assert audit["safety"]["v2_canonical_memory_mutated"] is False
    assert audit["safety"]["recall_events_recorded"] is False
    assert "Primary Retrieval Matches" in markdown


def test_bridge_context_does_not_call_v1_or_record_recall_events(tmp_path: Path, monkeypatch) -> None:
    db_path = _seed_v2_db(tmp_path)
    request = _bridge_request(db_path)
    request_path = tmp_path / "bridge_request.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")

    def _forbidden_v1(*_args, **_kwargs):
        raise AssertionError("bridge attempted to open v1")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", _forbidden_v1)
    code = main(["bridge-context", "--request", str(request_path), "--out-dir", str(tmp_path / "bridge")])

    with sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True) as conn:
        recall_count = conn.execute("SELECT COUNT(*) FROM v2_recall_events").fetchone()[0]
    assert code == 0
    assert recall_count == 0

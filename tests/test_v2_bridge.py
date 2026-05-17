from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from jsonschema import Draft202012Validator

from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main


REPO_ROOT = Path(__file__).resolve().parents[1]
REQUEST_SCHEMA = REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/schemas/bridge-request.v1.schema.json"
RESPONSE_SCHEMA = REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/schemas/bridge-response.v1.schema.json"
POLICY_SCHEMA = REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/schemas/bridge-capability-policy.v1.schema.json"
REQUEST_EXAMPLES = sorted((REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/examples/valid").glob("bridge-request.*.json"))
POLICY_EXAMPLE = REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/examples/valid/bridge-capability-policy.codex-shadow.v1.json"
RESPONSE_EXAMPLE = REPO_ROOT / "docs/contracts/muninn_v2_bridge/v1/examples/valid/bridge-response.rehydrate-ok.v1.json"


def _validate(schema_path: Path, payload: dict) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _seed_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "bridge_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    store.create_card(
        MemoryCard(
            id="card-current",
            kind="decision",
            title="Friday current bridge state",
            summary="The read-only bridge serves policy-scoped context.",
            body="Current state and next step context are served through BridgeResponseV1.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/docs/bridge.md:1")],
        )
    )
    store.create_card(
        MemoryCard(
            id="card-runbook",
            kind="runbook",
            title="Friday bridge runbook",
            summary="Use explicit policy and request files.",
            body="The bridge request command writes response and audit files only.",
            scope_key="repo:test",
            updated_at="2026-05-17T11:00:00Z",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/RUNBOOK.md:2")],
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


def _policy() -> dict:
    return {
        "schema_version": "BridgeCapabilityPolicyV1",
        "consumer_id": "codex-shadow",
        "allowed_operations": ["health", "search", "rehydrate", "explain"],
        "allowed_space_keys": ["repo:test"],
        "allowed_project_paths": ["/tmp/friday"],
        "max_results": 2,
        "max_context_chars": 1200,
        "allow_adaptive_scoring": False,
        "allow_reinforcement_read": True,
        "allow_reinforcement_write": False,
        "allow_cross_project": False,
        "require_evidence": True,
        "require_explanations": True,
        "audit_log_required": True,
    }


def _request(operation: str, **overrides) -> dict:
    payload = {
        "schema_version": "BridgeRequestV1",
        "request_id": f"test-{operation}",
        "operation": operation,
        "consumer_id": "codex-shadow",
        "query": "Friday current bridge state",
        "space_key": "repo:test",
        "project_path": "/tmp/friday",
        "limit": 4,
        "retrieval_mode": "hybrid",
        "include_evidence": True,
        "include_explanations": True,
        "allow_adaptive_scoring": False,
    }
    if operation == "health":
        payload = {
            "schema_version": "BridgeRequestV1",
            "request_id": "test-health",
            "operation": "health",
            "consumer_id": "codex-shadow",
        }
    if operation == "explain":
        payload["card_id"] = "card-current"
    if operation == "rehydrate":
        payload["max_context_chars"] = 3000
        payload["primary_limit"] = 1
    payload.update(overrides)
    return payload


def _run_bridge(tmp_path: Path, db_path: Path, request: dict, policy: dict | None = None) -> tuple[int, dict, Path]:
    policy_path = tmp_path / f"{request.get('request_id', 'request')}_policy.json"
    request_path = tmp_path / f"{request.get('request_id', 'request')}_request.json"
    out_dir = tmp_path / f"{request.get('request_id', 'request')}_out"
    policy_path.write_text(json.dumps(policy or _policy(), indent=2, sort_keys=True), encoding="utf-8")
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    code = main(
        [
            "bridge-request",
            "--v2-db",
            str(db_path),
            "--policy",
            str(policy_path),
            "--request",
            str(request_path),
            "--out-dir",
            str(out_dir),
        ]
    )
    response_path = next(out_dir.glob("bridge_response_*.json"))
    response = json.loads(response_path.read_text(encoding="utf-8"))
    return code, response, out_dir


def test_bridge_contract_examples_validate() -> None:
    for example in REQUEST_EXAMPLES:
        _validate(REQUEST_SCHEMA, json.loads(example.read_text(encoding="utf-8")))
    _validate(POLICY_SCHEMA, json.loads(POLICY_EXAMPLE.read_text(encoding="utf-8")))
    _validate(RESPONSE_SCHEMA, json.loads(RESPONSE_EXAMPLE.read_text(encoding="utf-8")))


def test_bridge_health_search_rehydrate_and_explain(tmp_path: Path, capsys) -> None:
    db_path = _seed_db(tmp_path)
    for operation in ["health", "search", "rehydrate", "explain"]:
        code, response, out_dir = _run_bridge(tmp_path, db_path, _request(operation))
        _validate(RESPONSE_SCHEMA, response)
        cli_payload = json.loads(capsys.readouterr().out)
        assert code == 0
        assert response["status"] == "ok"
        assert response["policy_decision"]["allowed"] is True
        assert cli_payload["mode"] == "bridge_request"
        assert list(out_dir.glob("bridge_audit_*.json"))
    search_response = json.loads((tmp_path / "test-search_out" / "bridge_response_test-search.json").read_text(encoding="utf-8"))
    assert search_response["result"]["result_count"] >= 1
    assert search_response["result"]["results"][0]["evidence"]
    rehydrate_response = json.loads((tmp_path / "test-rehydrate_out" / "bridge_response_test-rehydrate.json").read_text(encoding="utf-8"))
    assert rehydrate_response["result"]["rehydrate_response"]["record_type"] == "muninn_v2_rehydrate_response"
    assert rehydrate_response["policy_decision"]["clamps"]["limit"]["applied"] == 2
    assert rehydrate_response["policy_decision"]["clamps"]["max_context_chars"]["applied"] == 1200
    explain_response = json.loads((tmp_path / "test-explain_out" / "bridge_response_test-explain.json").read_text(encoding="utf-8"))
    assert explain_response["result"]["card_found"] is True
    assert explain_response["result"]["derived_index"]["record_id"] == "card-current"


def test_bridge_policy_denials_and_structured_errors(tmp_path: Path) -> None:
    db_path = _seed_db(tmp_path)
    cases = [
        (_request("delete", request_id="deny-unknown"), "denied", "unsupported_operation"),
        (_request("search", request_id="deny-project", project_path="/tmp/other"), "denied", "project_path_not_allowed"),
        (_request("search", request_id="deny-adaptive", allow_adaptive_scoring=True), "denied", "adaptive_scoring_not_allowed"),
        (_request("search", request_id="deny-evidence", include_evidence=False), "denied", "evidence_required"),
        ({"schema_version": "bad", "request_id": "bad-schema", "operation": "search", "consumer_id": "codex-shadow"}, "error", "invalid_schema_version"),
    ]
    for request, status, reason in cases:
        code, response, out_dir = _run_bridge(tmp_path, db_path, request)
        assert code == 0
        assert response["status"] == status
        assert reason in response["policy_decision"]["reason_codes"] or reason in response["error"]["details"]["reason_codes"]
        assert list(out_dir.glob("bridge_audit_*.json"))


def test_bridge_request_does_not_access_v1_or_mutate_canonical_db(tmp_path: Path, monkeypatch) -> None:
    db_path = _seed_db(tmp_path)
    before = db_path.stat().st_mtime_ns

    def _forbidden_v1(*_args, **_kwargs):
        raise AssertionError("bridge-request attempted to open v1")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", _forbidden_v1)
    code, response, _out_dir = _run_bridge(tmp_path, db_path, _request("search"))

    assert code == 0
    assert response["status"] == "ok"
    assert db_path.stat().st_mtime_ns == before
    assert not Path(str(db_path) + "-wal").exists()
    assert not Path(str(db_path) + "-shm").exists()

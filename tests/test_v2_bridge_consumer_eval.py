from __future__ import annotations

import json
from pathlib import Path

from muninn.v2.bridge.contracts import payload_hash
from muninn.v2.cli import main
from muninn.v2.eval import (
    load_bridge_consumer_fixture,
    run_bridge_consumer_eval,
    validate_bridge_response,
    write_bridge_consumer_eval_reports,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
REHYDRATE_FIXTURE = (
    REPO_ROOT
    / "docs/contracts/muninn_v2/v1/examples/valid/rehydrate-response.shadow-preview.v1.json"
)


def _policy() -> dict:
    return {
        "schema_version": "BridgeCapabilityPolicyV1",
        "consumer_id": "codex-shadow",
        "allowed_operations": ["health", "search", "rehydrate", "explain"],
        "allowed_space_keys": ["repo:test"],
        "allowed_project_paths": ["/mnt/data/friday"],
        "max_results": 12,
        "max_context_chars": 12000,
        "allow_adaptive_scoring": False,
        "allow_reinforcement_read": True,
        "allow_reinforcement_write": False,
        "allow_cross_project": False,
        "require_evidence": True,
        "require_explanations": True,
        "audit_log_required": True,
    }


def _request() -> dict:
    return {
        "schema_version": "BridgeRequestV1",
        "request_id": "bridge-consumer-test",
        "operation": "rehydrate",
        "consumer_id": "codex-shadow",
        "query": "resume Friday project current state and next steps",
        "space_key": "repo:test",
        "project_path": "/mnt/data/friday",
        "limit": 2,
        "primary_limit": 1,
        "max_context_chars": 12000,
        "retrieval_mode": "hybrid",
        "include_evidence": True,
        "include_explanations": True,
        "allow_adaptive_scoring": False,
        "recent_supplement": True,
        "strict": True,
    }


def _write_case_files(tmp_path: Path, *, mutate_response: dict | None = None, mutate_audit: dict | None = None) -> Path:
    request = _request()
    policy = _policy()
    response = {
        "schema_version": "BridgeResponseV1",
        "contract_version": "1.0.0",
        "record_type": "muninn_v2_bridge_response",
        "request_id": request["request_id"],
        "operation": "rehydrate",
        "consumer_id": "codex-shadow",
        "status": "ok",
        "policy_decision": {"allowed": True, "reason_codes": [], "clamps": {}},
        "degradation": {
            "degraded": True,
            "reason_codes": ["sqlite_vec_unavailable_using_json_vector_fallback"],
        },
        "result": {
            "operation": "rehydrate",
            "rehydrate_response": json.loads(REHYDRATE_FIXTURE.read_text(encoding="utf-8")),
            "adaptive_scoring": {"enabled": False},
            "clamps": {},
        },
        "error": None,
        "audit": {
            "trace_id": "bridge_consumer_test_trace",
            "created_at": "2026-05-17T00:00:00Z",
            "replayable": True,
            "input_hash": payload_hash(request),
            "policy_hash": payload_hash(policy),
            "response_hash": None,
        },
    }
    if mutate_response:
        response.update(mutate_response)
    response["audit"]["response_hash"] = payload_hash(
        {**response, "audit": {**response["audit"], "response_hash": None}}
    )
    db_path = tmp_path / "shadow.db"
    db_path.write_bytes(b"read-only fixture db bytes")
    audit = {
        "schema_version": "BridgeAuditV1",
        "record_type": "muninn_v2_bridge_audit",
        "request_id": request["request_id"],
        "trace_id": response["audit"]["trace_id"],
        "operation": "rehydrate",
        "consumer_id": "codex-shadow",
        "created_at": response["audit"]["created_at"],
        "replayable": True,
        "request_hash": response["audit"]["input_hash"],
        "policy_hash": response["audit"]["policy_hash"],
        "response_hash": response["audit"]["response_hash"],
        "policy_decision": response["policy_decision"],
        "degradation": response["degradation"],
        "db": {
            "path": str(db_path),
            "hash": None,
            "before": {"size_bytes": db_path.stat().st_size},
            "after": {"size_bytes": db_path.stat().st_size},
            "changed": {"size_bytes": False, "mtime_ns": False},
        },
        "retrieval_config": {"operation": "rehydrate", "retrieval_mode": "hybrid", "limit": 2},
        "adaptive_config": {"requested": False, "enabled": False, "default": False},
        "artifacts": {},
    }
    if mutate_audit:
        audit.update(mutate_audit)
    request_path = tmp_path / "request.json"
    policy_path = tmp_path / "policy.json"
    response_path = tmp_path / "bridge_response_bridge-consumer-test.json"
    audit_path = tmp_path / "bridge_audit_bridge-consumer-test.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True), encoding="utf-8")
    response_path.write_text(json.dumps(response, indent=2, sort_keys=True), encoding="utf-8")
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    fixture = {
        "schema_version": "muninn.v2.bridge_consumer_eval_fixture.v1",
        "name": "bridge consumer fixture",
        "version": 1,
        "defaults": {
            "min_coverage": 1.0,
            "require_all_required": True,
            "ignored_overinclude_terms": ["friday", "project", "current", "state", "next", "steps"],
        },
        "cases": [
            {
                "id": "friday-shadow-bridge-consumer",
                "project": "Friday",
                "task": request["query"],
                "bridge_response_path": str(response_path),
                "bridge_audit_path": str(audit_path),
                "bridge_request_path": str(request_path),
                "bridge_policy_path": str(policy_path),
                "v2_db_path": str(db_path),
                "v1_context": "Friday direct chat routes code prompts to coder with repo file context.",
                "expected_needs": [
                    {
                        "id": "direct-code-route",
                        "description": "Agent knows direct chat routes code prompts to coder.",
                        "all_terms": ["direct chat", "coder"],
                        "any_terms": ["repo file context", "file context"],
                    }
                ],
            }
        ],
    }
    fixture_path = tmp_path / "bridge_consumer_fixture.json"
    fixture_path.write_text(json.dumps(fixture, indent=2, sort_keys=True), encoding="utf-8")
    return fixture_path


def test_bridge_consumer_eval_validates_replays_and_renders_context(tmp_path: Path) -> None:
    fixture_path = _write_case_files(tmp_path)

    report = run_bridge_consumer_eval(load_bridge_consumer_fixture(fixture_path))

    case = report["cases"][0]
    validate_bridge_response(json.loads(Path(case["bridge_response_path"]).read_text(encoding="utf-8")))
    assert report["summary"]["go_cases"] == 1
    assert report["status"]["bridge_shadow_consumption"] == "GO"
    assert case["audit_replay"]["verified"] is True
    assert case["provenance"]["explanations_included"] is True
    assert "BEGIN MUNINN V2 AGENT CONTEXT" in report["context_blocks"][case["id"]]

    artifacts = write_bridge_consumer_eval_reports(report, tmp_path / "out")
    assert Path(artifacts["json"]).exists()
    assert Path(artifacts["markdown"]).exists()
    assert Path(artifacts["context_blocks"][case["id"]]).exists()


def test_bridge_consumer_eval_marks_replay_mismatch_no_go(tmp_path: Path) -> None:
    fixture_path = _write_case_files(tmp_path, mutate_audit={"response_hash": "wrong"})

    report = run_bridge_consumer_eval(load_bridge_consumer_fixture(fixture_path))
    case = report["cases"][0]

    assert case["audit_replay"]["verified"] is False
    assert "audit_response_hash" in case["audit_replay"]["failed_checks"]
    assert case["decision"] == "no_go"
    assert report["status"]["bridge_shadow_consumption"] == "NO-GO"


def test_bridge_consumer_eval_cli_does_not_access_v1(tmp_path: Path, monkeypatch, capsys) -> None:
    fixture_path = _write_case_files(tmp_path)

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("bridge-consumer-eval attempted to open v1")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)
    code = main(
        [
            "bridge-consumer-eval",
            "--fixture",
            str(fixture_path),
            "--out-dir",
            str(tmp_path / "audit"),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["mode"] == "bridge_consumer_eval"
    assert payload["bridge_shadow_consumption"] == "GO"
    assert (tmp_path / "audit" / "bridge_consumer_eval_report.json").exists()


def test_bridge_consumer_eval_rejects_non_rehydrate_bridge_response(tmp_path: Path) -> None:
    fixture_path = _write_case_files(tmp_path, mutate_response={"operation": "search"})

    code = main(
        [
            "bridge-consumer-eval",
            "--fixture",
            str(fixture_path),
            "--out-dir",
            str(tmp_path / "audit"),
        ]
    )

    assert code == 2

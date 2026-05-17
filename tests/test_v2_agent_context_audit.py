from __future__ import annotations

import json
from pathlib import Path

from muninn.v2.cli import main
from muninn.v2.eval import (
    load_agent_context_fixture,
    render_agent_context,
    run_agent_context_audit,
    validate_rehydrate_response,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
RESPONSE_FIXTURE = (
    REPO_ROOT
    / "docs/contracts/muninn_v2/v1/examples/valid/rehydrate-response.shadow-preview.v1.json"
)


def _write_fixture(tmp_path: Path, *, response_path: Path, v1_context: str | None = None) -> Path:
    payload = {
        "schema_version": "muninn.v2.agent_context_audit_fixture.v1",
        "name": "phase b fixture",
        "version": 1,
        "defaults": {
            "min_coverage": 1.0,
            "ignored_overinclude_terms": ["friday", "project", "resume", "current", "state", "next", "steps"],
        },
        "cases": [
            {
                "id": "friday-resume",
                "project": "Friday",
                "task": "resume Friday project current state and next steps",
                "response_path": str(response_path),
                "v1_context": v1_context,
                "expected_needs": [
                    {
                        "id": "coder-route",
                        "description": "Agent knows direct chat routes code prompts to coder.",
                        "all_terms": ["direct chat", "coder"],
                        "any_terms": ["repo file context", "file context"],
                    },
                    {
                        "id": "stack-runbook",
                        "description": "Agent knows stack lifecycle is explicit.",
                        "required": False,
                        "any_terms": ["docker compose", "compose scripts", "stack lifecycle"],
                    },
                ],
                "confusing_terms": [
                    {"term": "unrelated production cutover", "reason": "Would confuse the preview", "blocking": True}
                ],
            }
        ],
    }
    path = tmp_path / "agent_context_fixture.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_rehydrate_response_fixture_validates_and_renders_context() -> None:
    response = json.loads(RESPONSE_FIXTURE.read_text(encoding="utf-8"))

    validate_rehydrate_response(response)
    context = render_agent_context(response)

    assert "BEGIN MUNINN V2 AGENT CONTEXT" in context
    assert "PRIMARY MEMORY" in context
    assert "Friday coder auto route" in context
    assert "degraded: true" in context


def test_agent_context_audit_scores_v2_and_v1_context(tmp_path) -> None:
    fixture_path = _write_fixture(
        tmp_path,
        response_path=RESPONSE_FIXTURE,
        v1_context="Friday direct chat routes code prompts to coder with repo file context.",
    )

    report = run_agent_context_audit(load_agent_context_fixture(fixture_path))
    case = report["cases"][0]

    assert report["summary"]["cases"] == 1
    assert case["decision"] == "go"
    assert case["v2_context"]["coverage_score"] == 1.0
    assert case["v1_style_context"]["coverage_score"] == 1.0
    assert case["comparison"]["same_good_decision_supported"] is True


def test_agent_context_audit_reports_v1_to_v2_regression(tmp_path) -> None:
    response = json.loads(RESPONSE_FIXTURE.read_text(encoding="utf-8"))
    response["selected_memory"]["cards"][0]["title"] = "Friday route"
    response["selected_memory"]["cards"][0]["summary"] = "Direct chat route is present."
    response["selected_memory"]["cards"][0]["body_excerpt"] = ""
    response["selected_memory"]["cards"][0]["evidence"] = []
    response["selected_memory"]["evidence"] = []
    response["agent_briefing"]["bullets"] = ["Primary match: Friday route - Direct chat route is present."]
    response_path = tmp_path / "response.json"
    response_path.write_text(json.dumps(response, indent=2), encoding="utf-8")
    fixture_path = _write_fixture(
        tmp_path,
        response_path=response_path,
        v1_context="Friday direct chat routes code prompts to coder with repo file context.",
    )

    report = run_agent_context_audit(load_agent_context_fixture(fixture_path))
    case = report["cases"][0]

    assert case["decision"] == "no_go"
    assert case["v2_context"]["missing_required"] == ["coder-route"]
    assert case["comparison"]["regressions"] == ["coder-route"]


def test_agent_context_audit_cli_writes_reports_without_v1_connector(tmp_path, monkeypatch, capsys) -> None:
    fixture_path = _write_fixture(
        tmp_path,
        response_path=RESPONSE_FIXTURE,
        v1_context="Friday direct chat routes code prompts to coder with repo file context.",
    )
    out_dir = tmp_path / "audit"

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("v1 connector should not be used")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)

    code = main(
        [
            "agent-context-audit",
            "--fixture",
            str(fixture_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["mode"] == "agent_context_audit"
    assert payload["summary"]["go_cases"] == 1
    assert (out_dir / "agent_context_audit_report.json").exists()
    assert (out_dir / "agent_context_audit_report.md").exists()
    assert (out_dir / "agent_context_blocks" / "friday-resume.md").exists()


def test_agent_context_audit_is_separate_from_retrieval_fixture_loader(tmp_path) -> None:
    fixture_path = _write_fixture(tmp_path, response_path=RESPONSE_FIXTURE)

    fixture = load_agent_context_fixture(fixture_path)

    assert fixture.cases[0].case_id == "friday-resume"
    assert fixture.cases[0].expected_needs[0].need_id == "coder-route"

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from jsonschema import Draft202012Validator

from ..bridge.contracts import file_hash, payload_hash
from ..core.models import utc_now
from .agent_context import (
    CoverageNeed,
    WatchTerm,
    _coverage_needs,
    _flag_payload,
    _load_context_text,
    _overincluded_cards,
    _required_text,
    _resolve_path,
    _score_context,
    _selected_card_ids,
    _term_hits,
    _text_list,
    _watch_terms,
    render_agent_context,
    validate_rehydrate_response,
)

BRIDGE_CONSUMER_EVAL_SCHEMA_VERSION = "muninn.v2.bridge_consumer_eval.v1"
BRIDGE_CONSUMER_FIXTURE_SCHEMA_VERSION = "muninn.v2.bridge_consumer_eval_fixture.v1"
BRIDGE_RESPONSE_SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs/contracts/muninn_v2_bridge/v1/schemas/bridge-response.v1.schema.json"
)


class BridgeConsumerEvalError(RuntimeError):
    """Raised when the read-only bridge consumer evaluation cannot run safely."""


@dataclass(frozen=True)
class BridgeConsumerEvalCase:
    case_id: str
    project: str
    task: str
    bridge_response_path: str
    bridge_audit_path: str | None
    bridge_request_path: str | None
    bridge_policy_path: str | None
    v2_db_path: str | None
    expected_needs: tuple[CoverageNeed, ...]
    v1_context: str | None = None
    min_coverage: float = 0.85
    require_all_required: bool = True
    stale_terms: tuple[WatchTerm, ...] = ()
    confusing_terms: tuple[WatchTerm, ...] = ()
    ignored_overinclude_terms: tuple[str, ...] = ()
    require_replay_verified: bool = True
    require_provenance: bool = True


@dataclass(frozen=True)
class BridgeConsumerEvalFixture:
    name: str
    version: int
    cases: tuple[BridgeConsumerEvalCase, ...]
    source_path: str


def load_bridge_consumer_fixture(path: str | Path) -> BridgeConsumerEvalFixture:
    fixture_path = Path(path).expanduser().resolve()
    payload = _read_json(fixture_path)
    if not isinstance(payload, dict):
        raise BridgeConsumerEvalError("bridge consumer fixture must be a JSON object")
    if payload.get("schema_version") != BRIDGE_CONSUMER_FIXTURE_SCHEMA_VERSION:
        raise BridgeConsumerEvalError("unsupported bridge consumer fixture schema_version")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise BridgeConsumerEvalError("bridge consumer fixture cases must be a non-empty list")
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    cases: list[BridgeConsumerEvalCase] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_cases):
        if not isinstance(raw, dict):
            raise BridgeConsumerEvalError(f"cases[{index}] must be an object")
        case_id = _required_text(raw, "id", f"cases[{index}]")
        if case_id in seen:
            raise BridgeConsumerEvalError(f"duplicate case id: {case_id}")
        seen.add(case_id)
        cases.append(
            BridgeConsumerEvalCase(
                case_id=case_id,
                project=str(raw.get("project") or ""),
                task=_required_text(raw, "task", case_id),
                bridge_response_path=str(
                    _resolve_path(fixture_path.parent, _required_text(raw, "bridge_response_path", case_id))
                ),
                bridge_audit_path=_optional_path(fixture_path.parent, raw.get("bridge_audit_path")),
                bridge_request_path=_optional_path(fixture_path.parent, raw.get("bridge_request_path")),
                bridge_policy_path=_optional_path(fixture_path.parent, raw.get("bridge_policy_path")),
                v2_db_path=_optional_path(fixture_path.parent, raw.get("v2_db_path")),
                expected_needs=tuple(_coverage_needs(raw.get("expected_needs"), case_id)),
                v1_context=_load_context_text(raw, base_dir=fixture_path.parent),
                min_coverage=float(raw.get("min_coverage", defaults.get("min_coverage", 0.85))),
                require_all_required=bool(
                    raw.get("require_all_required", defaults.get("require_all_required", True))
                ),
                stale_terms=tuple(_watch_terms(raw.get("stale_terms"), default_blocking=True)),
                confusing_terms=tuple(_watch_terms(raw.get("confusing_terms"), default_blocking=False)),
                ignored_overinclude_terms=tuple(
                    _text_list(raw.get("ignored_overinclude_terms") or defaults.get("ignored_overinclude_terms") or [])
                ),
                require_replay_verified=bool(
                    raw.get("require_replay_verified", defaults.get("require_replay_verified", True))
                ),
                require_provenance=bool(raw.get("require_provenance", defaults.get("require_provenance", True))),
            )
        )
    return BridgeConsumerEvalFixture(
        name=str(payload.get("name") or fixture_path.stem),
        version=int(payload.get("version") or 1),
        cases=tuple(cases),
        source_path=str(fixture_path),
    )


def validate_bridge_response(
    payload: dict[str, Any],
    *,
    schema_path: str | Path | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise BridgeConsumerEvalError("BridgeResponseV1 payload must be an object")
    if payload.get("schema_version") != "BridgeResponseV1":
        raise BridgeConsumerEvalError("unsupported BridgeResponseV1 schema_version")
    schema_file = Path(schema_path).expanduser().resolve() if schema_path else BRIDGE_RESPONSE_SCHEMA_PATH
    schema = _read_json(schema_file)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def run_bridge_consumer_eval(
    fixture: BridgeConsumerEvalFixture,
    *,
    bridge_schema_path: str | Path | None = None,
    rehydrate_schema_path: str | Path | None = None,
) -> dict[str, Any]:
    case_reports: list[dict[str, Any]] = []
    context_blocks: dict[str, str] = {}
    for case in fixture.cases:
        bridge_response = _read_bridge_response(case.bridge_response_path, schema_path=bridge_schema_path)
        rehydrate_response = _extract_rehydrate_response(bridge_response)
        validate_rehydrate_response(rehydrate_response, schema_path=rehydrate_schema_path)
        context_block = render_agent_context(rehydrate_response)
        selected_ids = _selected_card_ids(rehydrate_response)
        v2_score = _score_context(
            context_block,
            case.expected_needs,
            selected_card_ids=selected_ids,
            min_coverage=case.min_coverage,
            require_all_required=case.require_all_required,
        )
        v1_score = (
            _score_context(
                case.v1_context,
                case.expected_needs,
                selected_card_ids=set(),
                min_coverage=case.min_coverage,
                require_all_required=case.require_all_required,
            )
            if case.v1_context is not None
            else None
        )
        replay = _verify_replay(case, bridge_response)
        provenance = _provenance_status(bridge_response, rehydrate_response)
        stale = _term_hits(context_block, case.stale_terms)
        confusing = _term_hits(context_block, case.confusing_terms)
        overincluded = _overincluded_cards(
            rehydrate_response,
            case.expected_needs,
            case.ignored_overinclude_terms,
        )
        omissions = [
            {
                "need_id": item["id"],
                "description": item["description"],
                "missing_all_terms": item["missing_all_terms"],
                "missing_evidence_terms": item["missing_evidence_terms"],
                "card_id_hit": item["card_id_hit"],
            }
            for item in v2_score["need_results"]
            if item["required"] and not item["covered"]
        ]
        blocking_flags = [
            *[_flag_payload(item) for item in stale if item["blocking"]],
            *[_flag_payload(item) for item in confusing if item["blocking"]],
        ]
        regression = _comparison(v1_score=v1_score, v2_score=v2_score)
        v2_pass = bool(v2_score["pass"] and not blocking_flags)
        replay_pass = bool(replay["verified"] or not case.require_replay_verified)
        provenance_pass = bool(provenance["sufficient"] or not case.require_provenance)
        bridge_pass = bool(
            bridge_response.get("status") == "ok"
            and bridge_response.get("operation") == "rehydrate"
            and bridge_response.get("policy_decision", {}).get("allowed") is True
            and not bridge_response.get("result", {}).get("adaptive_scoring", {}).get("enabled")
        )
        same_good = bool(v2_pass and not regression["regressions"] and replay_pass and provenance_pass and bridge_pass)
        report = {
            "id": case.case_id,
            "project": case.project,
            "task": case.task,
            "bridge_response_path": case.bridge_response_path,
            "bridge_audit_path": case.bridge_audit_path,
            "bridge_request_path": case.bridge_request_path,
            "bridge_policy_path": case.bridge_policy_path,
            "v2_db_path": case.v2_db_path,
            "bridge": {
                "request_id": bridge_response.get("request_id"),
                "status": bridge_response.get("status"),
                "policy_allowed": bridge_response.get("policy_decision", {}).get("allowed"),
                "degraded": bridge_response.get("degradation", {}).get("degraded"),
                "degradation_reason_codes": bridge_response.get("degradation", {}).get("reason_codes") or [],
                "adaptive_enabled": bridge_response.get("result", {}).get("adaptive_scoring", {}).get("enabled"),
            },
            "v2_context": {
                "coverage_score": v2_score["coverage_score"],
                "covered_required": v2_score["covered_required"],
                "required_needs": v2_score["required_needs"],
                "missing_required": v2_score["missing_required"],
                "pass": v2_pass,
                "context_block_chars": len(context_block),
            },
            "v1_style_context": (
                {
                    "provided": True,
                    "coverage_score": v1_score["coverage_score"],
                    "covered_required": v1_score["covered_required"],
                    "required_needs": v1_score["required_needs"],
                    "missing_required": v1_score["missing_required"],
                    "pass": v1_score["pass"],
                }
                if v1_score is not None
                else {"provided": False}
            ),
            "comparison": {
                **regression,
                "same_good_decision_supported": same_good,
            },
            "need_results": v2_score["need_results"],
            "omissions": omissions,
            "stale": [_flag_payload(item) for item in stale],
            "confusing": [_flag_payload(item) for item in confusing],
            "over_included_cards": overincluded,
            "provenance": provenance,
            "audit_replay": replay,
            "selected_cards": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "stage": item.get("selection", {}).get("stage"),
                    "evidence_count": item.get("evidence_count"),
                }
                for item in rehydrate_response["selected_memory"].get("cards", [])
            ],
            "decision": "go" if same_good else "no_go",
        }
        case_reports.append(report)
        context_blocks[case.case_id] = context_block
    summary = _summary(case_reports)
    return {
        "schema_version": BRIDGE_CONSUMER_EVAL_SCHEMA_VERSION,
        "record_type": "muninn_v2_bridge_consumer_eval_report",
        "generated_at": utc_now(),
        "fixture": {
            "name": fixture.name,
            "version": fixture.version,
            "source_path": fixture.source_path,
        },
        "summary": summary,
        "cases": case_reports,
        "context_blocks": context_blocks,
        "status": {
            "bridge_shadow_consumption": "GO" if summary["no_go_cases"] == 0 else "NO-GO",
            "live_cutover": "NO-GO",
            "writes": "NO-GO",
            "adaptive_default": "NO-GO",
        },
        "safety": {
            "mode": "offline_read_only_bridge_consumer_eval",
            "live_mcp_integration": False,
            "v1_writes": False,
            "default_context_source_changed": False,
            "adaptive_default_enabled": False,
        },
    }


def write_bridge_consumer_eval_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "bridge_consumer_eval_report.json"
    md_path = directory / "bridge_consumer_eval_report.md"
    json_path.write_text(
        json.dumps(_report_without_context_blocks(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    context_dir = directory / "rendered_context_blocks"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_paths: dict[str, str] = {}
    for case_id, context_block in sorted(report.get("context_blocks", {}).items()):
        path = context_dir / f"{_safe_file_name(case_id)}.md"
        path.write_text(context_block, encoding="utf-8")
        context_paths[case_id] = str(path)
    return {"json": str(json_path), "markdown": str(md_path), "context_blocks": context_paths}


def _read_bridge_response(path: str | Path, *, schema_path: str | Path | None = None) -> dict[str, Any]:
    payload = _read_json(Path(path).expanduser().resolve())
    validate_bridge_response(payload, schema_path=schema_path)
    return payload


def _extract_rehydrate_response(bridge_response: dict[str, Any]) -> dict[str, Any]:
    if bridge_response.get("operation") != "rehydrate":
        raise BridgeConsumerEvalError("bridge consumer eval requires rehydrate BridgeResponseV1 artifacts")
    if bridge_response.get("status") != "ok":
        raise BridgeConsumerEvalError("bridge rehydrate response must have status ok")
    result = bridge_response.get("result")
    if not isinstance(result, dict):
        raise BridgeConsumerEvalError("bridge response result must be an object")
    response = result.get("rehydrate_response")
    if not isinstance(response, dict):
        raise BridgeConsumerEvalError("bridge response missing result.rehydrate_response")
    return response


def _verify_replay(case: BridgeConsumerEvalCase, bridge_response: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    expected_response_hash = payload_hash(
        {**bridge_response, "audit": {**bridge_response["audit"], "response_hash": None}}
    )
    response_hash_ok = bridge_response["audit"]["response_hash"] == expected_response_hash
    checks.append({"name": "response_hash", "ok": response_hash_ok})
    audit_payload: dict[str, Any] | None = None
    if case.bridge_audit_path:
        audit_payload = _read_json(Path(case.bridge_audit_path))
        checks.extend(
            [
                {
                    "name": "audit_schema",
                    "ok": audit_payload.get("schema_version") == "BridgeAuditV1",
                },
                {
                    "name": "audit_response_hash",
                    "ok": audit_payload.get("response_hash") == bridge_response["audit"]["response_hash"],
                },
                {
                    "name": "audit_request_hash",
                    "ok": audit_payload.get("request_hash") == bridge_response["audit"]["input_hash"],
                },
                {
                    "name": "audit_policy_hash",
                    "ok": audit_payload.get("policy_hash") == bridge_response["audit"].get("policy_hash"),
                },
                {
                    "name": "audit_trace_id",
                    "ok": audit_payload.get("trace_id") == bridge_response["audit"].get("trace_id"),
                },
                {
                    "name": "audit_db_unchanged",
                    "ok": not any(bool(value) for value in audit_payload.get("db", {}).get("changed", {}).values()),
                },
            ]
        )
        if case.v2_db_path and audit_payload.get("db", {}).get("hash"):
            checks.append(
                {
                    "name": "audit_db_hash",
                    "ok": audit_payload["db"]["hash"] == file_hash(case.v2_db_path),
                }
            )
    if case.bridge_request_path:
        request_payload = _read_json(Path(case.bridge_request_path))
        checks.append(
            {
                "name": "request_hash",
                "ok": payload_hash(request_payload) == bridge_response["audit"]["input_hash"],
            }
        )
    if case.bridge_policy_path:
        policy_payload = _read_json(Path(case.bridge_policy_path))
        checks.append(
            {
                "name": "policy_hash",
                "ok": payload_hash(policy_payload) == bridge_response["audit"].get("policy_hash"),
            }
        )
    failed = [item["name"] for item in checks if not item["ok"]]
    return {
        "verified": not failed,
        "failed_checks": failed,
        "checks": checks,
        "trace_id": bridge_response["audit"].get("trace_id"),
        "request_hash": bridge_response["audit"].get("input_hash"),
        "policy_hash": bridge_response["audit"].get("policy_hash"),
        "response_hash": bridge_response["audit"].get("response_hash"),
    }


def _provenance_status(bridge_response: dict[str, Any], rehydrate_response: dict[str, Any]) -> dict[str, Any]:
    cards = rehydrate_response["selected_memory"].get("cards", [])
    evidence = rehydrate_response["selected_memory"].get("evidence", [])
    explanations = rehydrate_response.get("explanations", {})
    cards_with_explanations = sum(1 for card in cards if isinstance(card.get("explanation"), dict))
    cards_with_evidence = sum(1 for card in cards if int(card.get("evidence_count") or 0) > 0)
    degradation = bridge_response.get("degradation", {})
    retrieval = rehydrate_response.get("retrieval_provenance", {})
    return {
        "sufficient": bool(cards and cards_with_explanations and bridge_response.get("audit", {}).get("trace_id")),
        "selected_card_count": len(cards),
        "evidence_ref_count": len(evidence),
        "cards_with_evidence": cards_with_evidence,
        "cards_with_explanations": cards_with_explanations,
        "explanations_included": bool(explanations.get("included")),
        "bridge_trace_id": bridge_response.get("audit", {}).get("trace_id"),
        "bridge_degraded": bool(degradation.get("degraded")),
        "bridge_degradation_reason_codes": degradation.get("reason_codes") or [],
        "retrieval_backend": retrieval.get("backend"),
        "retrieval_degraded": bool(retrieval.get("degraded")),
        "retrieval_degradation_reasons": retrieval.get("degradation_reasons") or [],
    }


def _comparison(*, v1_score: dict[str, Any] | None, v2_score: dict[str, Any]) -> dict[str, Any]:
    if v1_score is None:
        return {
            "v1_context_provided": False,
            "coverage_delta_v2_minus_v1": None,
            "regressions": [],
        }
    v1_missing = set(v1_score["missing_required"])
    v2_missing = set(v2_score["missing_required"])
    return {
        "v1_context_provided": True,
        "coverage_delta_v2_minus_v1": round(
            float(v2_score["coverage_score"]) - float(v1_score["coverage_score"]),
            6,
        ),
        "regressions": sorted(v2_missing - v1_missing),
    }


def _summary(cases: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    go = sum(1 for case in cases if case["decision"] == "go")
    average = (
        round(sum(float(case["v2_context"]["coverage_score"]) for case in cases) / total, 6)
        if total
        else None
    )
    return {
        "cases": total,
        "go_cases": go,
        "no_go_cases": total - go,
        "average_v2_coverage_score": average,
        "same_good_decision_supported_count": sum(
            1 for case in cases if case["comparison"]["same_good_decision_supported"]
        ),
        "cases_with_v1_comparison": sum(1 for case in cases if case["comparison"]["v1_context_provided"]),
        "replay_verified_count": sum(1 for case in cases if case["audit_replay"]["verified"]),
        "provenance_sufficient_count": sum(1 for case in cases if case["provenance"]["sufficient"]),
        "missing_required_total": sum(len(case["v2_context"]["missing_required"]) for case in cases),
        "omission_total": sum(len(case["omissions"]) for case in cases),
        "stale_flag_total": sum(len(case["stale"]) for case in cases),
        "confusing_flag_total": sum(len(case["confusing"]) for case in cases),
        "over_included_card_total": sum(len(case["over_included_cards"]) for case in cases),
        "adaptive_enabled_cases": sum(1 for case in cases if case["bridge"]["adaptive_enabled"]),
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Muninn v2 Bridge Consumer Evaluation",
        "",
        f"- Fixture: `{report['fixture']['name']}`",
        f"- Cases: {summary['cases']}",
        f"- GO cases: {summary['go_cases']}",
        f"- NO-GO cases: {summary['no_go_cases']}",
        f"- Average v2 coverage: `{summary['average_v2_coverage_score']}`",
        f"- Same-good-decision supported: {summary['same_good_decision_supported_count']}",
        f"- Replay verified: {summary['replay_verified_count']}",
        f"- Provenance sufficient: {summary['provenance_sufficient_count']}",
        f"- Missing required needs: {summary['missing_required_total']}",
        f"- Omissions: {summary['omission_total']}",
        f"- Confusing flags: {summary['confusing_flag_total']}",
        f"- Over-included cards: {summary['over_included_card_total']}",
        f"- Adaptive-enabled cases: {summary['adaptive_enabled_cases']}",
        "",
        "## Cases",
        "",
    ]
    for case in report["cases"]:
        lines.extend(
            [
                f"### {case['id']}",
                "",
                f"- Project: `{case['project']}`",
                f"- Decision: `{case['decision']}`",
                f"- Bridge status: `{case['bridge']['status']}` policy_allowed=`{case['bridge']['policy_allowed']}` degraded=`{case['bridge']['degraded']}`",
                f"- Degradation reasons: `{case['bridge']['degradation_reason_codes']}`",
                f"- V2 coverage: `{case['v2_context']['coverage_score']}`",
                f"- Missing required: `{case['v2_context']['missing_required']}`",
                f"- V1 comparison: `{case['comparison']}`",
                f"- Replay verified: `{case['audit_replay']['verified']}` failed=`{case['audit_replay']['failed_checks']}`",
                f"- Provenance: evidence_refs=`{case['provenance']['evidence_ref_count']}` explanations=`{case['provenance']['explanations_included']}`",
                f"- Confusing flags: `{case['confusing']}`",
                f"- Over-included cards: {len(case['over_included_cards'])}",
                "",
            ]
        )
        if case["omissions"]:
            lines.append("Omissions:")
            for item in case["omissions"]:
                lines.append(f"- `{item['need_id']}` missing all={item['missing_all_terms']} evidence={item['missing_evidence_terms']}")
            lines.append("")
        if case["over_included_cards"]:
            lines.append("Over-included candidates:")
            for item in case["over_included_cards"][:12]:
                lines.append(f"- `{item.get('id')}` {item.get('title')} ({item.get('stage')})")
            lines.append("")
    lines.extend(
        [
            "## Status",
            "",
            f"- BRIDGE SHADOW CONSUMPTION: {report['status']['bridge_shadow_consumption']}",
            f"- LIVE CUTOVER: {report['status']['live_cutover']}",
            f"- WRITES: {report['status']['writes']}",
            f"- ADAPTIVE DEFAULT: {report['status']['adaptive_default']}",
            "",
            "## Safety",
            "",
            "- Offline bridge consumer evaluation only.",
            "- Consumes BridgeResponseV1 artifacts and does not call live MCP.",
            "- Does not write to v1, project repositories, or default context settings.",
        ]
    )
    return "\n".join(lines) + "\n"


def _optional_path(base_dir: Path, value: Any) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(_resolve_path(base_dir, str(value)))


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise BridgeConsumerEvalError(f"file_not_found:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_file_name(value: str) -> str:
    import re

    out = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value).strip("_")
    return out or "case"


def _report_without_context_blocks(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    out.pop("context_blocks", None)
    return out

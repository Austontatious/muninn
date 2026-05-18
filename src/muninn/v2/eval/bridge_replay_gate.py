from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..bridge.contracts import payload_hash, safe_request_id
from ..core.models import utc_now
from .bridge_consumer import validate_bridge_response

BRIDGE_REPLAY_GATE_SCHEMA_VERSION = "muninn.v2.bridge_replay_gate.v1"


class BridgeReplayGateError(RuntimeError):
    """Raised when a bridge replay gate input is invalid."""


@dataclass(frozen=True)
class ReplayGateOptions:
    drill_report: str
    out_dir: str
    v1_safety_report: str | None = None
    min_required_coverage: float = 1.0
    min_budget_coverage: float = 0.5
    run_failure_drills: bool = False
    require_human_signoff: bool = False


def run_bridge_replay_gate(options: ReplayGateOptions) -> dict[str, Any]:
    drill_path = Path(options.drill_report).expanduser().resolve()
    report = _read_json(drill_path)
    if report.get("record_type") != "muninn_v2_bridge_ops_drill_report":
        raise BridgeReplayGateError("bridge replay gate requires a bridge ops drill report")
    out_dir = Path(options.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    drill_out_dir = Path(str(report.get("out_dir") or drill_path.parent)).expanduser()
    v1_safety_path = _v1_safety_path(options, drill_out_dir)

    artifacts = _load_mode_artifacts(report, drill_out_dir)
    gates = [
        _gate_status_boundaries(report),
        _gate_task_outcomes(report),
        _gate_required_context(report, min_required_coverage=options.min_required_coverage),
        _gate_budget_pressure(report, min_budget_coverage=options.min_budget_coverage),
        _gate_contamination(report),
        _gate_adaptive(report),
        _gate_degradation_markers(report),
        _gate_operator_review(report, drill_out_dir, require_human_signoff=options.require_human_signoff),
        _gate_audit_replay(artifacts),
        _gate_evidence(artifacts),
        _gate_v1_safety(v1_safety_path),
    ]
    failure_drills = _run_failure_drills(report, artifacts) if options.run_failure_drills else []
    if options.run_failure_drills:
        gates.append(_gate_failure_drills(failure_drills))

    technical_go = all(item["ok"] for item in gates)
    human_review = next(item for item in gates if item["name"] == "operator_review")
    gate_report = {
        "schema_version": BRIDGE_REPLAY_GATE_SCHEMA_VERSION,
        "record_type": "muninn_v2_bridge_replay_gate_report",
        "mode": "offline_shadow_bridge_replay_gate",
        "generated_at": utc_now(),
        "source": {
            "drill_report": str(drill_path),
            "drill_out_dir": str(drill_out_dir),
            "v1_safety_report": str(v1_safety_path) if v1_safety_path else None,
        },
        "thresholds": {
            "min_required_coverage": float(options.min_required_coverage),
            "min_budget_coverage": float(options.min_budget_coverage),
            "require_human_signoff": bool(options.require_human_signoff),
        },
        "summary": _summary(gates, failure_drills),
        "gates": gates,
        "failure_drills": failure_drills,
        "status": {
            "technical_replay_gate": "GO" if technical_go else "NO-GO",
            "live_shadow_trial": "GO" if technical_go and human_review["ok"] and options.require_human_signoff else "NO-GO",
            "bridge_shadow_consumption": report.get("status", {}).get("bridge_shadow_consumption", "NO-GO"),
            "live_cutover": "NO-GO",
            "writes": "NO-GO",
            "adaptive_default": "NO-GO",
        },
        "safety": {
            "offline_only": True,
            "v1_writes": False,
            "live_mcp_integration": False,
            "default_context_source_changed": False,
            "adaptive_default_enabled": False,
            "canonical_memory_writes": False,
        },
    }
    gate_report["artifacts"] = write_bridge_replay_gate_reports(gate_report, out_dir)
    return gate_report


def write_bridge_replay_gate_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "bridge_replay_gate_report.json"
    md_path = directory / "bridge_replay_gate_report.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _gate_status_boundaries(report: dict[str, Any]) -> dict[str, Any]:
    status = report.get("status") if isinstance(report.get("status"), dict) else {}
    expected = {
        "bridge_shadow_consumption": "GO",
        "live_cutover": "NO-GO",
        "writes": "NO-GO",
        "adaptive_default": "NO-GO",
    }
    failures = [key for key, value in expected.items() if status.get(key) != value]
    return _gate("status_boundaries", not failures, {"expected": expected, "actual": status, "failures": failures})


def _gate_task_outcomes(report: dict[str, Any]) -> dict[str, Any]:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    ok = int(summary.get("no_go_tasks") or 0) == 0 and int(summary.get("audit_replay_failures") or 0) == 0
    return _gate(
        "task_outcomes",
        ok,
        {
            "go_tasks": summary.get("go_tasks"),
            "no_go_tasks": summary.get("no_go_tasks"),
            "audit_replay_failures": summary.get("audit_replay_failures"),
        },
    )


def _gate_required_context(report: dict[str, Any], *, min_required_coverage: float) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    for task in _tasks(report):
        for mode in task.get("modes", []):
            if mode.get("mode") != "adaptive_off":
                continue
            context = mode.get("v2_context") if isinstance(mode.get("v2_context"), dict) else {}
            coverage = float(context.get("coverage_score") or 0.0)
            missing = list(context.get("missing_required") or [])
            if coverage < float(min_required_coverage) or missing:
                failures.append({"task": task.get("id"), "coverage": coverage, "missing_required": missing})
    return _gate("required_context_retention", not failures, {"min_required_coverage": min_required_coverage, "failures": failures})


def _gate_budget_pressure(report: dict[str, Any], *, min_budget_coverage: float) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    omitted = 0
    for task in _tasks(report):
        for mode in task.get("modes", []):
            if mode.get("mode") != "budget_pressure":
                continue
            context = mode.get("v2_context") if isinstance(mode.get("v2_context"), dict) else {}
            budget = mode.get("budget") if isinstance(mode.get("budget"), dict) else {}
            coverage = float(context.get("coverage_score") or 0.0)
            omitted += int(budget.get("omitted_for_budget") or 0)
            if coverage < float(min_budget_coverage):
                failures.append({"task": task.get("id"), "coverage": coverage})
    return _gate("budget_pressure_retention", not failures, {"min_budget_coverage": min_budget_coverage, "omitted_for_budget": omitted, "failures": failures})


def _gate_contamination(report: dict[str, Any]) -> dict[str, Any]:
    failures = [item for item in report.get("contamination_checks", []) if not _contamination_ok(item)]
    return _gate("cross_project_contamination_denied", not failures, {"checks": len(report.get("contamination_checks", [])), "failures": failures})


def _gate_adaptive(report: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    counts = {"adaptive_off_enabled": 0, "adaptive_on_enabled": 0, "adaptive_on_runs": 0}
    for task in _tasks(report):
        for mode in task.get("modes", []):
            adaptive = mode.get("adaptive_scoring") if isinstance(mode.get("adaptive_scoring"), dict) else {}
            mode_name = str(mode.get("mode") or "")
            if mode_name == "adaptive_off" and adaptive.get("enabled"):
                counts["adaptive_off_enabled"] += 1
                failures.append({"task": task.get("id"), "mode": mode_name, "reason": "adaptive_enabled_in_off_mode"})
            if mode_name == "adaptive_on":
                counts["adaptive_on_runs"] += 1
                if adaptive.get("enabled"):
                    counts["adaptive_on_enabled"] += 1
                if not _adaptive_state_ok(adaptive, required=True):
                    failures.append({"task": task.get("id"), "mode": mode_name, "reason": "invalid_or_missing_adaptive_state"})
    return _gate("adaptive_state_opt_in", not failures, {"counts": counts, "failures": failures})


def _gate_degradation_markers(report: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    degraded = 0
    for task in _tasks(report):
        for mode in task.get("modes", []):
            if mode.get("degraded"):
                degraded += 1
                if not mode.get("degradation_reason_codes"):
                    failures.append({"task": task.get("id"), "mode": mode.get("mode"), "reason": "missing_degradation_reason_codes"})
    return _gate("degradation_markers_visible", not failures, {"degraded_runs": degraded, "failures": failures})


def _gate_operator_review(report: dict[str, Any], drill_out_dir: Path, *, require_human_signoff: bool) -> dict[str, Any]:
    review = report.get("operator_review") if isinstance(report.get("operator_review"), dict) else {}
    review_path = drill_out_dir / "operator_review_notes.md"
    human_signoff = bool(review.get("human_signoff_recorded"))
    ok = review_path.exists() and (human_signoff or not require_human_signoff)
    return _gate(
        "operator_review",
        ok,
        {
            "operator_review_notes_exists": review_path.exists(),
            "human_signoff_recorded": human_signoff,
            "human_signoff_required": bool(require_human_signoff),
            "review_items": len(review.get("items") or []),
        },
    )


def _gate_audit_replay(artifacts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for item in artifacts:
        checks = _verify_artifact_hashes(item)
        failed = [check["name"] for check in checks if not check["ok"]]
        if failed:
            failures.append({"request_id": item["request_id"], "failed_checks": failed})
    return _gate("audit_trace_replay", not failures, {"artifact_sets": len(artifacts), "failures": failures})


def _gate_evidence(artifacts: Sequence[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for item in artifacts:
        if not _response_evidence_ok(item["response"], item["policy"], item["request"]):
            failures.append({"request_id": item["request_id"], "reason": "required_evidence_missing"})
    return _gate("evidence_required_when_policy_requires_it", not failures, {"failures": failures})


def _gate_v1_safety(v1_safety_path: Path | None) -> dict[str, Any]:
    if v1_safety_path is None or not v1_safety_path.exists():
        return _gate("v1_untouched", False, {"reason": "v1_safety_report_missing", "path": str(v1_safety_path) if v1_safety_path else None})
    payload = _read_json(v1_safety_path)
    failures = [
        key
        for key in ("row_counts_changed", "size_changed", "mtime_changed")
        if bool(payload.get(key))
    ]
    return _gate("v1_untouched", not failures, {"path": str(v1_safety_path), "failures": failures})


def _gate_failure_drills(failure_drills: Sequence[dict[str, Any]]) -> dict[str, Any]:
    missed = [item for item in failure_drills if not item.get("detected")]
    return _gate("failure_drills_detect_expected_failures", not missed, {"drills": len(failure_drills), "missed": missed})


def _run_failure_drills(report: dict[str, Any], artifacts: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    drills: list[dict[str, Any]] = []
    mode_sample = _first_mode(report)
    adaptive_sample = _first_mode(report, mode_name="adaptive_on")
    contamination_sample = copy.deepcopy((report.get("contamination_checks") or [{}])[0])
    artifact_sample = copy.deepcopy(artifacts[0]) if artifacts else None

    corrupted_adaptive = copy.deepcopy(adaptive_sample)
    corrupted_adaptive["adaptive_scoring"] = {
        "requested": True,
        "enabled": True,
        "default": False,
        "state_version": None,
        "state_count": 0,
    }
    drills.append(_drill("corrupted_adaptive_state", not _adaptive_state_ok(corrupted_adaptive["adaptive_scoring"], required=True), "adaptive state enabled without version/count"))

    contamination_sample.update({"status": "ok", "policy_allowed": True, "decision": "no_go", "reason_codes": []})
    drills.append(_drill("contamination_attempt", not _contamination_ok(contamination_sample), "cross-project request allowed"))

    stale_replay = copy.deepcopy(artifact_sample)
    if stale_replay:
        stale_replay["audit"]["trace_id"] = "stale-trace"
        drills.append(_drill("stale_replay_artifact", bool(_failed_names(stale_replay)), "audit trace no longer matches response"))

    denied_bypass = copy.deepcopy((report.get("contamination_checks") or [{}])[0])
    denied_bypass.update({"status": "denied", "policy_allowed": True, "decision": "no_go"})
    drills.append(_drill("denied_policy_bypass", not _contamination_ok(denied_bypass), "denied response reports policy allowed"))

    degraded = copy.deepcopy(mode_sample)
    degraded["degraded"] = True
    degraded["degradation_reason_codes"] = []
    degraded_report = {"tasks": [{"modes": [degraded]}]}
    drills.append(_drill("degraded_index_marker_missing", not _gate_degradation_markers(degraded_report)["ok"], "degraded run omitted reason codes"))

    missing_evidence = copy.deepcopy(artifact_sample)
    if missing_evidence:
        rehydrate = missing_evidence["response"].get("result", {}).get("rehydrate_response", {})
        if isinstance(rehydrate, dict):
            rehydrate.setdefault("selected_memory", {})["evidence"] = []
        missing_evidence["policy"]["require_evidence"] = True
        missing_evidence["request"]["include_evidence"] = True
        drills.append(_drill("missing_evidence", not _response_evidence_ok(missing_evidence["response"], missing_evidence["policy"], missing_evidence["request"]), "policy requires evidence but payload has none"))

    hash_mismatch = copy.deepcopy(artifact_sample)
    if hash_mismatch:
        hash_mismatch["response"]["audit"]["response_hash"] = "wrong"
        drills.append(_drill("replay_hash_mismatch", bool(_failed_names(hash_mismatch)), "response hash mismatch"))

    return drills


def _load_mode_artifacts(report: dict[str, Any], drill_out_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for task in _tasks(report):
        pilot = str(task.get("pilot") or "")
        session = str(task.get("session") or "")
        task_id = str(task.get("task") or "")
        for mode in task.get("modes", []):
            mode_name = str(mode.get("mode") or "")
            request_id = safe_request_id(str(mode.get("request_id") or ""))
            base = drill_out_dir / pilot / session / task_id / mode_name
            paths = {
                "request": base / "bridge_request.json",
                "policy": base / "bridge_policy.json",
                "response": base / f"bridge_response_{request_id}.json",
                "audit": base / f"bridge_audit_{request_id}.json",
            }
            missing = [name for name, path in paths.items() if not path.exists()]
            if missing:
                artifacts.append({"request_id": request_id, "paths": {k: str(v) for k, v in paths.items()}, "missing": missing})
                continue
            response = _read_json(paths["response"])
            validate_bridge_response(response)
            artifacts.append(
                {
                    "request_id": request_id,
                    "paths": {key: str(path) for key, path in paths.items()},
                    "missing": [],
                    "request": _read_json(paths["request"]),
                    "policy": _read_json(paths["policy"]),
                    "response": response,
                    "audit": _read_json(paths["audit"]),
                }
            )
    return artifacts


def _verify_artifact_hashes(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    if artifact.get("missing"):
        return [{"name": f"{name}_exists", "ok": False} for name in artifact["missing"]]
    request = artifact["request"]
    policy = artifact["policy"]
    response = artifact["response"]
    audit = artifact["audit"]
    response_hash = payload_hash({**response, "audit": {**response["audit"], "response_hash": None}})
    checks = [
        {"name": "response_hash", "ok": response_hash == response["audit"].get("response_hash")},
        {"name": "request_hash", "ok": payload_hash(request) == response["audit"].get("input_hash")},
        {"name": "policy_hash", "ok": payload_hash(policy) == response["audit"].get("policy_hash")},
        {"name": "audit_schema", "ok": audit.get("schema_version") == "BridgeAuditV1"},
        {"name": "audit_response_hash", "ok": audit.get("response_hash") == response["audit"].get("response_hash")},
        {"name": "audit_request_hash", "ok": audit.get("request_hash") == response["audit"].get("input_hash")},
        {"name": "audit_policy_hash", "ok": audit.get("policy_hash") == response["audit"].get("policy_hash")},
        {"name": "audit_trace_id", "ok": audit.get("trace_id") == response["audit"].get("trace_id")},
        {
            "name": "audit_db_unchanged",
            "ok": not any(bool(value) for value in audit.get("db", {}).get("changed", {}).values()),
        },
    ]
    return checks


def _response_evidence_ok(response: dict[str, Any], policy: dict[str, Any], request: dict[str, Any]) -> bool:
    if not bool(policy.get("require_evidence")):
        return True
    if request.get("include_evidence") is False:
        return False
    rehydrate = response.get("result", {}).get("rehydrate_response")
    if not isinstance(rehydrate, dict):
        return True
    selected = rehydrate.get("selected_memory") if isinstance(rehydrate.get("selected_memory"), dict) else {}
    return bool(selected.get("evidence"))


def _adaptive_state_ok(adaptive: dict[str, Any], *, required: bool) -> bool:
    if not adaptive.get("enabled"):
        return not required
    return bool(
        adaptive.get("requested") is True
        and adaptive.get("default") is False
        and adaptive.get("state_version")
        and int(adaptive.get("state_count") or 0) > 0
    )


def _contamination_ok(item: dict[str, Any]) -> bool:
    return bool(
        item.get("status") == "denied"
        and item.get("policy_allowed") is False
        and item.get("decision") == "go"
        and item.get("reason_codes")
    )


def _failed_names(artifact: dict[str, Any]) -> list[str]:
    return [item["name"] for item in _verify_artifact_hashes(artifact) if not item["ok"]]


def _drill(name: str, detected: bool, mutation: str) -> dict[str, Any]:
    return {"name": name, "detected": bool(detected), "mutation": mutation}


def _first_mode(report: dict[str, Any], *, mode_name: str | None = None) -> dict[str, Any]:
    for task in _tasks(report):
        for mode in task.get("modes", []):
            if mode_name is None or mode.get("mode") == mode_name:
                return copy.deepcopy(mode)
    raise BridgeReplayGateError("drill report has no matching mode entries")


def _tasks(report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks = report.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise BridgeReplayGateError("bridge ops drill report has no task entries")
    return [item for item in tasks if isinstance(item, dict)]


def _v1_safety_path(options: ReplayGateOptions, drill_out_dir: Path) -> Path | None:
    if options.v1_safety_report:
        return Path(options.v1_safety_report).expanduser().resolve()
    candidate = drill_out_dir.parent / "safety" / "v1_row_counts_before_after.json"
    return candidate if candidate.exists() else None


def _gate(name: str, ok: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "details": details}


def _summary(gates: Sequence[dict[str, Any]], failure_drills: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "gates": len(gates),
        "passed": sum(1 for item in gates if item["ok"]),
        "failed": sum(1 for item in gates if not item["ok"]),
        "failure_drills": len(failure_drills),
        "failure_drills_detected": sum(1 for item in failure_drills if item.get("detected")),
    }


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BridgeReplayGateError(f"expected JSON object: {path}")
    return payload


def _render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Muninn v2 Bridge Replay Gate",
        "",
        "## Summary",
        "",
        f"- Technical replay gate: `{report['status']['technical_replay_gate']}`",
        f"- Live shadow trial: `{report['status']['live_shadow_trial']}`",
        f"- Bridge shadow consumption: `{report['status']['bridge_shadow_consumption']}`",
        f"- Live cutover: `{report['status']['live_cutover']}`",
        f"- Writes: `{report['status']['writes']}`",
        f"- Adaptive default: `{report['status']['adaptive_default']}`",
        f"- Gates passed: {report['summary']['passed']} / {report['summary']['gates']}",
        "",
        "## Gates",
        "",
    ]
    for gate in report["gates"]:
        lines.append(f"- `{gate['name']}`: `{('pass' if gate['ok'] else 'fail')}`")
    if report.get("failure_drills"):
        lines.extend(["", "## Failure Drills", ""])
        for drill in report["failure_drills"]:
            lines.append(f"- `{drill['name']}` detected=`{str(drill['detected']).lower()}` mutation=`{drill['mutation']}`")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Offline replay gate only.",
            "- Does not call live MCP.",
            "- Does not write v1 or v2 canonical memory.",
            "- Does not authorize live cutover.",
        ]
    )
    return "\n".join(lines) + "\n"

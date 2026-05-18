from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..bridge import run_bridge_request
from ..bridge.contracts import file_hash, payload_hash, safe_request_id
from ..core.models import utc_now
from .agent_context import (
    CoverageNeed,
    WatchTerm,
    _coverage_needs,
    _flag_payload,
    _load_context_text,
    _overincluded_cards,
    _required_text,
    _score_context,
    _selected_card_ids,
    _term_hits,
    _text_list,
    _watch_terms,
    render_agent_context,
    validate_rehydrate_response,
)
from .bridge_consumer import validate_bridge_response

BRIDGE_OPS_DRILL_SCHEMA_VERSION = "muninn.v2.bridge_ops_drill.v1"
BRIDGE_OPS_DRILL_FIXTURE_SCHEMA_VERSION = "muninn.v2.bridge_ops_drill_fixture.v1"


class BridgeOpsDrillError(RuntimeError):
    """Raised when the shadow bridge operations drill cannot run safely."""


@dataclass(frozen=True)
class DrillTask:
    task_id: str
    query: str
    expected_needs: tuple[CoverageNeed, ...]
    v1_context: str | None
    stale_terms: tuple[WatchTerm, ...]
    confusing_terms: tuple[WatchTerm, ...]
    ignored_overinclude_terms: tuple[str, ...]
    min_coverage: float
    require_all_required: bool
    budget_max_context_chars: int | None
    budget_min_coverage: float


@dataclass(frozen=True)
class DrillSession:
    session_id: str
    continuity_needs: tuple[CoverageNeed, ...]
    tasks: tuple[DrillTask, ...]


@dataclass(frozen=True)
class DrillPilot:
    pilot_id: str
    project: str
    v2_db: str
    space_key: str
    project_path: str
    consumer_id: str
    policy: dict[str, Any]
    request_defaults: dict[str, Any]
    sessions: tuple[DrillSession, ...]


@dataclass(frozen=True)
class BridgeOpsDrillFixture:
    name: str
    version: int
    pilots: tuple[DrillPilot, ...]
    source_path: str


def load_bridge_ops_drill_fixture(path: str | Path) -> BridgeOpsDrillFixture:
    fixture_path = Path(path).expanduser().resolve()
    payload = _read_json(fixture_path)
    if not isinstance(payload, dict):
        raise BridgeOpsDrillError("bridge ops drill fixture must be a JSON object")
    if payload.get("schema_version") != BRIDGE_OPS_DRILL_FIXTURE_SCHEMA_VERSION:
        raise BridgeOpsDrillError("unsupported bridge ops drill fixture schema_version")
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    raw_pilots = payload.get("pilots")
    if not isinstance(raw_pilots, list) or not raw_pilots:
        raise BridgeOpsDrillError("bridge ops drill fixture pilots must be a non-empty list")
    pilots: list[DrillPilot] = []
    for index, raw in enumerate(raw_pilots):
        if not isinstance(raw, dict):
            raise BridgeOpsDrillError(f"pilots[{index}] must be an object")
        pilot_id = _required_text(raw, "id", f"pilots[{index}]")
        base_dir = fixture_path.parent
        pilot_defaults = {**defaults, **(raw.get("defaults") if isinstance(raw.get("defaults"), dict) else {})}
        sessions = _sessions(raw.get("sessions"), pilot_defaults, base_dir=base_dir, pilot_id=pilot_id)
        policy = raw.get("policy")
        if not isinstance(policy, dict):
            raise BridgeOpsDrillError(f"{pilot_id}.policy must be an object")
        pilots.append(
            DrillPilot(
                pilot_id=pilot_id,
                project=str(raw.get("project") or pilot_id),
                v2_db=str(_resolve_path(base_dir, _required_text(raw, "v2_db", pilot_id))),
                space_key=_required_text(raw, "space_key", pilot_id),
                project_path=_required_text(raw, "project_path", pilot_id),
                consumer_id=str(raw.get("consumer_id") or policy.get("consumer_id") or "codex-shadow"),
                policy=dict(policy),
                request_defaults=dict(raw.get("request_defaults") or {}),
                sessions=tuple(sessions),
            )
        )
    return BridgeOpsDrillFixture(
        name=str(payload.get("name") or fixture_path.stem),
        version=int(payload.get("version") or 1),
        pilots=tuple(pilots),
        source_path=str(fixture_path),
    )


def run_bridge_ops_drill(
    fixture: BridgeOpsDrillFixture,
    *,
    out_dir: str | Path,
) -> dict[str, Any]:
    output_dir = Path(out_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    task_reports: list[dict[str, Any]] = []
    contamination_reports: list[dict[str, Any]] = []
    context_blocks: dict[str, str] = {}
    operator_items: list[dict[str, Any]] = []
    pilots = list(fixture.pilots)
    for pilot_index, pilot in enumerate(pilots):
        for session in pilot.sessions:
            previous_primary_ids: set[str] | None = None
            for task in session.tasks:
                mode_reports: list[dict[str, Any]] = []
                for mode in ("adaptive_off", "budget_pressure", "adaptive_on"):
                    request = _request_for_mode(pilot, session, task, mode=mode)
                    policy = _policy_for_mode(pilot.policy, mode=mode)
                    paths = _write_request_policy(output_dir, pilot, session, task, mode, request, policy)
                    response = run_bridge_request(
                        v2_db=pilot.v2_db,
                        policy=policy,
                        request=request,
                        out_dir=paths["bridge_dir"],
                    )
                    bridge_paths = _bridge_artifact_paths(paths["bridge_dir"], response["request_id"])
                    case_report, context_block = _evaluate_rehydrate_response(
                        pilot=pilot,
                        session=session,
                        task=task,
                        mode=mode,
                        request=request,
                        policy=policy,
                        response=response,
                        bridge_paths=bridge_paths,
                        previous_primary_ids=previous_primary_ids,
                    )
                    mode_reports.append(case_report)
                    if context_block is not None:
                        key = f"{pilot.pilot_id}/{session.session_id}/{task.task_id}/{mode}"
                        context_blocks[key] = context_block
                        context_path = output_dir / "rendered_context_blocks" / f"{_safe_file_name(key)}.md"
                        operator_items.append(
                            {
                                "key": key,
                                "project": pilot.project,
                                "session": session.session_id,
                                "task": task.task_id,
                                "mode": mode,
                                "context_block_path": str(context_path),
                                "decision": case_report["decision"],
                                "missing_required": case_report.get("v2_context", {}).get("missing_required", []),
                                "flags": case_report.get("flags", []),
                            }
                        )
                off = next(item for item in mode_reports if item["mode"] == "adaptive_off")
                primary_ids = {
                    str(item.get("id"))
                    for item in off.get("selected_cards", [])
                    if item.get("stage") == "primary_retrieval"
                }
                previous_primary_ids = primary_ids
                task_reports.append(
                    {
                        "id": f"{pilot.pilot_id}:{session.session_id}:{task.task_id}",
                        "pilot": pilot.pilot_id,
                        "project": pilot.project,
                        "session": session.session_id,
                        "task": task.task_id,
                        "query": task.query,
                        "modes": mode_reports,
                        "decision": _task_decision(mode_reports),
                    }
                )
        contamination_reports.append(
            _run_contamination_check(
                output_dir=output_dir,
                pilot=pilot,
                other=pilots[(pilot_index + 1) % len(pilots)] if len(pilots) > 1 else pilot,
            )
        )
    summary = _summary(task_reports, contamination_reports)
    report = {
        "schema_version": BRIDGE_OPS_DRILL_SCHEMA_VERSION,
        "record_type": "muninn_v2_bridge_ops_drill_report",
        "generated_at": utc_now(),
        "fixture": {
            "name": fixture.name,
            "version": fixture.version,
            "source_path": fixture.source_path,
        },
        "out_dir": str(output_dir),
        "summary": summary,
        "tasks": task_reports,
        "contamination_checks": contamination_reports,
        "operator_review": {
            "status": "generated",
            "human_signoff_recorded": False,
            "items": operator_items,
        },
        "context_blocks": context_blocks,
        "status": {
            "bridge_shadow_consumption": "GO" if _drill_go(summary) else "NO-GO",
            "live_cutover": "NO-GO",
            "writes": "NO-GO",
            "adaptive_default": "NO-GO",
        },
        "safety": {
            "mode": "offline_shadow_bridge_operations_drill",
            "live_mcp_integration": False,
            "v1_writes": False,
            "default_context_source_changed": False,
            "adaptive_default_enabled": False,
            "canonical_memory_writes": False,
        },
    }
    report["artifacts"] = write_bridge_ops_drill_reports(report, output_dir)
    return report


def write_bridge_ops_drill_reports(report: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "bridge_ops_drill_report.json"
    md_path = directory / "bridge_ops_drill_report.md"
    review_path = directory / "operator_review_notes.md"
    json_path.write_text(json.dumps(_report_without_context_blocks(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    context_dir = directory / "rendered_context_blocks"
    context_dir.mkdir(parents=True, exist_ok=True)
    context_paths: dict[str, str] = {}
    for key, context_block in sorted(report.get("context_blocks", {}).items()):
        path = context_dir / f"{_safe_file_name(key)}.md"
        path.write_text(context_block, encoding="utf-8")
        context_paths[key] = str(path)
    review_path.write_text(_render_operator_review(report, context_paths), encoding="utf-8")
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "operator_review": str(review_path),
        "context_blocks": context_paths,
    }


def _sessions(raw: Any, defaults: dict[str, Any], *, base_dir: Path, pilot_id: str) -> list[DrillSession]:
    if not isinstance(raw, list) or not raw:
        raise BridgeOpsDrillError(f"{pilot_id}.sessions must be a non-empty list")
    sessions: list[DrillSession] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BridgeOpsDrillError(f"{pilot_id}.sessions[{index}] must be an object")
        session_id = _required_text(item, "id", f"{pilot_id}.sessions[{index}]")
        session_defaults = {**defaults, **(item.get("defaults") if isinstance(item.get("defaults"), dict) else {})}
        continuity_needs = tuple(_coverage_needs(item.get("continuity_needs"), session_id)) if item.get("continuity_needs") else ()
        sessions.append(
            DrillSession(
                session_id=session_id,
                continuity_needs=continuity_needs,
                tasks=tuple(_tasks(item.get("tasks"), session_defaults, base_dir=base_dir, session_id=session_id)),
            )
        )
    return sessions


def _tasks(raw: Any, defaults: dict[str, Any], *, base_dir: Path, session_id: str) -> list[DrillTask]:
    if not isinstance(raw, list) or not raw:
        raise BridgeOpsDrillError(f"{session_id}.tasks must be a non-empty list")
    tasks: list[DrillTask] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise BridgeOpsDrillError(f"{session_id}.tasks[{index}] must be an object")
        task_id = _required_text(item, "id", f"{session_id}.tasks[{index}]")
        tasks.append(
            DrillTask(
                task_id=task_id,
                query=_required_text(item, "query", task_id),
                expected_needs=tuple(_coverage_needs(item.get("expected_needs"), task_id)),
                v1_context=_load_context_text(item, base_dir=base_dir),
                stale_terms=tuple(_watch_terms(item.get("stale_terms"), default_blocking=True)),
                confusing_terms=tuple(_watch_terms(item.get("confusing_terms"), default_blocking=False)),
                ignored_overinclude_terms=tuple(
                    _text_list(item.get("ignored_overinclude_terms") or defaults.get("ignored_overinclude_terms") or [])
                ),
                min_coverage=float(item.get("min_coverage", defaults.get("min_coverage", 0.85))),
                require_all_required=bool(item.get("require_all_required", defaults.get("require_all_required", True))),
                budget_max_context_chars=_optional_positive_int(
                    item.get("budget_max_context_chars", defaults.get("budget_max_context_chars"))
                ),
                budget_min_coverage=float(item.get("budget_min_coverage", defaults.get("budget_min_coverage", 0.5))),
            )
        )
    return tasks


def _request_for_mode(pilot: DrillPilot, session: DrillSession, task: DrillTask, *, mode: str) -> dict[str, Any]:
    defaults = {
        "limit": 12,
        "primary_limit": 3,
        "max_context_chars": 12000,
        "retrieval_mode": "hybrid",
        "include_evidence": True,
        "include_explanations": True,
        "recent_supplement": True,
        "strict": True,
    }
    defaults.update(pilot.request_defaults)
    if mode == "budget_pressure" and task.budget_max_context_chars:
        defaults["max_context_chars"] = int(task.budget_max_context_chars)
    request = {
        "schema_version": "BridgeRequestV1",
        "request_id": safe_request_id(f"{pilot.pilot_id}-{session.session_id}-{task.task_id}-{mode}"),
        "operation": "rehydrate",
        "consumer_id": pilot.consumer_id,
        "query": task.query,
        "space_key": pilot.space_key,
        "project_path": pilot.project_path,
        "allow_adaptive_scoring": mode == "adaptive_on",
        **defaults,
    }
    return request


def _policy_for_mode(policy: dict[str, Any], *, mode: str) -> dict[str, Any]:
    out = dict(policy)
    out["allow_adaptive_scoring"] = mode == "adaptive_on"
    out["allow_reinforcement_write"] = False
    return out


def _write_request_policy(
    output_dir: Path,
    pilot: DrillPilot,
    session: DrillSession,
    task: DrillTask,
    mode: str,
    request: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Path]:
    base = output_dir / pilot.pilot_id / session.session_id / task.task_id / mode
    base.mkdir(parents=True, exist_ok=True)
    request_path = base / "bridge_request.json"
    policy_path = base / "bridge_policy.json"
    request_path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    policy_path.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"bridge_dir": base, "request": request_path, "policy": policy_path}


def _bridge_artifact_paths(bridge_dir: Path, request_id: str) -> dict[str, Path]:
    return {
        "response": bridge_dir / f"bridge_response_{safe_request_id(request_id)}.json",
        "audit": bridge_dir / f"bridge_audit_{safe_request_id(request_id)}.json",
    }


def _evaluate_rehydrate_response(
    *,
    pilot: DrillPilot,
    session: DrillSession,
    task: DrillTask,
    mode: str,
    request: dict[str, Any],
    policy: dict[str, Any],
    response: dict[str, Any],
    bridge_paths: dict[str, Path],
    previous_primary_ids: set[str] | None,
) -> tuple[dict[str, Any], str | None]:
    validate_bridge_response(response)
    if response.get("status") != "ok":
        return (
            {
                "mode": mode,
                "request_id": response.get("request_id"),
                "status": response.get("status"),
                "decision": "no_go",
                "error": response.get("error"),
                "audit_replay": _verify_bridge_artifacts(response, request, policy, bridge_paths, pilot.v2_db),
            },
            None,
        )
    rehydrate_response = response.get("result", {}).get("rehydrate_response")
    if not isinstance(rehydrate_response, dict):
        raise BridgeOpsDrillError("bridge response missing rehydrate_response")
    validate_rehydrate_response(rehydrate_response)
    context_block = render_agent_context(rehydrate_response)
    selected_ids = _selected_card_ids(rehydrate_response)
    v2_score = _score_context(
        context_block,
        task.expected_needs,
        selected_card_ids=selected_ids,
        min_coverage=task.min_coverage,
        require_all_required=task.require_all_required,
    )
    v1_score = (
        _score_context(
            task.v1_context,
            task.expected_needs,
            selected_card_ids=set(),
            min_coverage=task.min_coverage,
            require_all_required=task.require_all_required,
        )
        if task.v1_context is not None
        else None
    )
    continuity_score = (
        _score_context(
            context_block,
            session.continuity_needs,
            selected_card_ids=selected_ids,
            min_coverage=task.min_coverage,
            require_all_required=True,
        )
        if session.continuity_needs
        else None
    )
    stale = _term_hits(context_block, task.stale_terms)
    confusing = _term_hits(context_block, task.confusing_terms)
    overincluded = _overincluded_cards(rehydrate_response, task.expected_needs, task.ignored_overinclude_terms)
    replay = _verify_bridge_artifacts(response, request, policy, bridge_paths, pilot.v2_db)
    regression = _comparison(v1_score=v1_score, v2_score=v2_score)
    budget = rehydrate_response["budget"]
    selected_cards = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "stage": item.get("selection", {}).get("stage"),
            "score": item.get("selection", {}).get("score"),
        }
        for item in rehydrate_response["selected_memory"].get("cards", [])
    ]
    primary_ids = {
        str(item.get("id"))
        for item in selected_cards
        if item.get("stage") == "primary_retrieval"
    }
    overlap_with_previous = sorted(primary_ids & previous_primary_ids) if previous_primary_ids else []
    blocking_flags = [
        *[_flag_payload(item) for item in stale if item["blocking"]],
        *[_flag_payload(item) for item in confusing if item["blocking"]],
    ]
    coverage_pass = bool(v2_score["pass"] and not regression["regressions"] and not blocking_flags)
    if mode == "budget_pressure":
        coverage_pass = bool(float(v2_score["coverage_score"]) >= task.budget_min_coverage and not blocking_flags)
    adaptive = response.get("result", {}).get("adaptive_scoring", {})
    flags = []
    if mode == "adaptive_on" and not adaptive.get("enabled"):
        flags.append("adaptive_requested_but_not_enabled")
    if mode == "adaptive_off" and adaptive.get("enabled"):
        flags.append("adaptive_enabled_in_off_mode")
    if continuity_score and continuity_score["missing_required"]:
        flags.append("continuity_need_missing")
    decision = "go" if coverage_pass and replay["verified"] and not flags else "no_go"
    return (
        {
            "mode": mode,
            "request_id": response.get("request_id"),
            "status": response.get("status"),
            "policy_allowed": response.get("policy_decision", {}).get("allowed"),
            "degraded": response.get("degradation", {}).get("degraded"),
            "degradation_reason_codes": response.get("degradation", {}).get("reason_codes") or [],
            "adaptive_scoring": adaptive,
            "v2_context": {
                "coverage_score": v2_score["coverage_score"],
                "missing_required": v2_score["missing_required"],
                "pass": v2_score["pass"],
                "context_block_chars": len(context_block),
            },
            "v1_style_context": (
                {
                    "provided": True,
                    "coverage_score": v1_score["coverage_score"],
                    "missing_required": v1_score["missing_required"],
                    "pass": v1_score["pass"],
                }
                if v1_score is not None
                else {"provided": False}
            ),
            "comparison": regression,
            "continuity": (
                {
                    "coverage_score": continuity_score["coverage_score"],
                    "missing_required": continuity_score["missing_required"],
                    "overlap_with_previous_primary_ids": overlap_with_previous,
                }
                if continuity_score is not None
                else {"configured": False, "overlap_with_previous_primary_ids": overlap_with_previous}
            ),
            "budget": {
                "max_chars": budget["max_chars"],
                "used_chars": budget["used_chars"],
                "selected_total": budget["selected_total"],
                "omitted_for_budget": budget["omitted_for_budget"],
                "omitted_for_limit": budget["omitted_for_limit"],
            },
            "stale": [_flag_payload(item) for item in stale],
            "confusing": [_flag_payload(item) for item in confusing],
            "over_included_cards": overincluded,
            "audit_replay": replay,
            "selected_cards": selected_cards,
            "flags": flags,
            "decision": decision,
        },
        context_block,
    )


def _run_contamination_check(output_dir: Path, *, pilot: DrillPilot, other: DrillPilot) -> dict[str, Any]:
    other_space_key = other.space_key
    other_project_path = other.project_path
    attempted_project = other.project
    if other.pilot_id == pilot.pilot_id:
        other_space_key = f"{pilot.space_key}:wrong-project"
        other_project_path = f"{pilot.project_path.rstrip('/')}-wrong-project"
        attempted_project = f"{pilot.project} synthetic wrong project"
    request = {
        "schema_version": "BridgeRequestV1",
        "request_id": safe_request_id(f"{pilot.pilot_id}-contamination-wrong-project"),
        "operation": "rehydrate",
        "consumer_id": pilot.consumer_id,
        "query": f"attempt cross project access from {pilot.project} to {attempted_project}",
        "space_key": other_space_key,
        "project_path": other_project_path,
        "limit": 6,
        "primary_limit": 2,
        "max_context_chars": 6000,
        "retrieval_mode": "hybrid",
        "include_evidence": True,
        "include_explanations": True,
        "allow_adaptive_scoring": False,
        "recent_supplement": True,
        "strict": True,
    }
    policy = _policy_for_mode(pilot.policy, mode="adaptive_off")
    base = output_dir / pilot.pilot_id / "contamination_wrong_project"
    base.mkdir(parents=True, exist_ok=True)
    (base / "bridge_request.json").write_text(json.dumps(request, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (base / "bridge_policy.json").write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    response = run_bridge_request(v2_db=pilot.v2_db, policy=policy, request=request, out_dir=base)
    expected_denied = response.get("status") == "denied" and response.get("policy_decision", {}).get("allowed") is False
    return {
        "pilot": pilot.pilot_id,
        "project": pilot.project,
        "attempted_project": attempted_project,
        "request_id": response.get("request_id"),
        "status": response.get("status"),
        "policy_allowed": response.get("policy_decision", {}).get("allowed"),
        "reason_codes": response.get("policy_decision", {}).get("reason_codes") or [],
        "decision": "go" if expected_denied else "no_go",
    }


def _verify_bridge_artifacts(
    response: dict[str, Any],
    request: dict[str, Any],
    policy: dict[str, Any],
    bridge_paths: dict[str, Path],
    v2_db: str,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    response_hash = payload_hash({**response, "audit": {**response["audit"], "response_hash": None}})
    checks.append({"name": "response_hash", "ok": response_hash == response["audit"]["response_hash"]})
    checks.append({"name": "request_hash", "ok": payload_hash(request) == response["audit"]["input_hash"]})
    checks.append({"name": "policy_hash", "ok": payload_hash(policy) == response["audit"].get("policy_hash")})
    audit_path = bridge_paths["audit"]
    if audit_path.exists():
        audit = _read_json(audit_path)
        checks.extend(
            [
                {"name": "audit_schema", "ok": audit.get("schema_version") == "BridgeAuditV1"},
                {"name": "audit_response_hash", "ok": audit.get("response_hash") == response["audit"]["response_hash"]},
                {"name": "audit_request_hash", "ok": audit.get("request_hash") == response["audit"]["input_hash"]},
                {"name": "audit_policy_hash", "ok": audit.get("policy_hash") == response["audit"].get("policy_hash")},
                {"name": "audit_trace_id", "ok": audit.get("trace_id") == response["audit"].get("trace_id")},
                {
                    "name": "audit_db_unchanged",
                    "ok": not any(bool(value) for value in audit.get("db", {}).get("changed", {}).values()),
                },
            ]
        )
        if audit.get("db", {}).get("hash"):
            checks.append({"name": "audit_db_hash", "ok": audit["db"]["hash"] == file_hash(v2_db)})
    else:
        checks.append({"name": "audit_file_exists", "ok": False})
    failed = [item["name"] for item in checks if not item["ok"]]
    return {
        "verified": not failed,
        "failed_checks": failed,
        "checks": checks,
        "trace_id": response["audit"].get("trace_id"),
        "request_hash": response["audit"].get("input_hash"),
        "policy_hash": response["audit"].get("policy_hash"),
        "response_hash": response["audit"].get("response_hash"),
    }


def _task_decision(mode_reports: Sequence[dict[str, Any]]) -> str:
    off = next(item for item in mode_reports if item["mode"] == "adaptive_off")
    budget = next(item for item in mode_reports if item["mode"] == "budget_pressure")
    adaptive = next(item for item in mode_reports if item["mode"] == "adaptive_on")
    if off["decision"] != "go":
        return "no_go"
    if not budget["audit_replay"]["verified"] or not adaptive["audit_replay"]["verified"]:
        return "no_go"
    if adaptive.get("flags"):
        return "no_go"
    return "go"


def _comparison(*, v1_score: dict[str, Any] | None, v2_score: dict[str, Any]) -> dict[str, Any]:
    if v1_score is None:
        return {"v1_context_provided": False, "coverage_delta_v2_minus_v1": None, "regressions": []}
    v1_missing = set(v1_score["missing_required"])
    v2_missing = set(v2_score["missing_required"])
    return {
        "v1_context_provided": True,
        "coverage_delta_v2_minus_v1": round(float(v2_score["coverage_score"]) - float(v1_score["coverage_score"]), 6),
        "regressions": sorted(v2_missing - v1_missing),
    }


def _summary(tasks: Sequence[dict[str, Any]], contamination: Sequence[dict[str, Any]]) -> dict[str, Any]:
    modes = [mode for task in tasks for mode in task["modes"]]
    off_modes = [mode for mode in modes if mode["mode"] == "adaptive_off"]
    budget_modes = [mode for mode in modes if mode["mode"] == "budget_pressure"]
    adaptive_modes = [mode for mode in modes if mode["mode"] == "adaptive_on"]
    return {
        "pilots": len({task["pilot"] for task in tasks}),
        "tasks": len(tasks),
        "mode_runs": len(modes),
        "go_tasks": sum(1 for task in tasks if task["decision"] == "go"),
        "no_go_tasks": sum(1 for task in tasks if task["decision"] != "go"),
        "adaptive_off_go": sum(1 for mode in off_modes if mode["decision"] == "go"),
        "budget_pressure_runs": len(budget_modes),
        "budget_pressure_go": sum(1 for mode in budget_modes if mode["decision"] == "go"),
        "adaptive_on_runs": len(adaptive_modes),
        "adaptive_on_enabled": sum(1 for mode in adaptive_modes if mode.get("adaptive_scoring", {}).get("enabled")),
        "adaptive_default_enabled": sum(1 for mode in off_modes if mode.get("adaptive_scoring", {}).get("enabled")),
        "audit_replay_verified": sum(1 for mode in modes if mode["audit_replay"]["verified"]),
        "audit_replay_failures": sum(1 for mode in modes if not mode["audit_replay"]["verified"]),
        "missing_required_total": sum(len(mode.get("v2_context", {}).get("missing_required", [])) for mode in off_modes),
        "stale_flag_total": sum(len(mode.get("stale", [])) for mode in off_modes),
        "confusing_flag_total": sum(len(mode.get("confusing", [])) for mode in off_modes),
        "over_included_card_total": sum(len(mode.get("over_included_cards", [])) for mode in off_modes),
        "contamination_checks": len(contamination),
        "contamination_denied": sum(1 for item in contamination if item["decision"] == "go"),
        "sqlite_vec_degraded_runs": sum(
            1
            for mode in modes
            if "sqlite_vec_unavailable_using_json_vector_fallback" in mode.get("degradation_reason_codes", [])
        ),
    }


def _drill_go(summary: dict[str, Any]) -> bool:
    return bool(
        summary["no_go_tasks"] == 0
        and summary["audit_replay_failures"] == 0
        and summary["contamination_denied"] == summary["contamination_checks"]
        and summary["adaptive_default_enabled"] == 0
    )


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Muninn v2 Phase G Bridge Operations Drill",
        "",
        "## Summary",
        "",
        f"- Pilots: {summary['pilots']}",
        f"- Tasks: {summary['tasks']}",
        f"- GO tasks: {summary['go_tasks']}",
        f"- NO-GO tasks: {summary['no_go_tasks']}",
        f"- Mode runs: {summary['mode_runs']}",
        f"- Adaptive-on enabled: {summary['adaptive_on_enabled']} / {summary['adaptive_on_runs']}",
        f"- Adaptive default enabled: {summary['adaptive_default_enabled']}",
        f"- Audit replay failures: {summary['audit_replay_failures']}",
        f"- Contamination denied: {summary['contamination_denied']} / {summary['contamination_checks']}",
        f"- Over-included cards: {summary['over_included_card_total']}",
        "",
        "## Tasks",
        "",
    ]
    for task in report["tasks"]:
        lines.extend([f"### {task['id']}", "", f"- Decision: `{task['decision']}`", f"- Query: `{task['query']}`"])
        for mode in task["modes"]:
            lines.append(
                f"- `{mode['mode']}` status=`{mode['status']}` decision=`{mode['decision']}` "
                f"coverage=`{mode.get('v2_context', {}).get('coverage_score')}` "
                f"adaptive=`{mode.get('adaptive_scoring', {}).get('enabled')}` "
                f"budget_omitted=`{mode.get('budget', {}).get('omitted_for_budget')}`"
            )
        lines.append("")
    lines.extend(
        [
            "## Contamination Checks",
            "",
        ]
    )
    for item in report["contamination_checks"]:
        lines.append(
            f"- `{item['pilot']}` attempted `{item['attempted_project']}` -> "
            f"status=`{item['status']}` decision=`{item['decision']}` reasons=`{item['reason_codes']}`"
        )
    lines.extend(
        [
            "",
            "## Status",
            "",
            f"- BRIDGE SHADOW CONSUMPTION: {report['status']['bridge_shadow_consumption']}",
            f"- LIVE CUTOVER: {report['status']['live_cutover']}",
            f"- WRITES: {report['status']['writes']}",
            f"- ADAPTIVE DEFAULT: {report['status']['adaptive_default']}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_operator_review(report: dict[str, Any], context_paths: dict[str, str]) -> str:
    lines = [
        "# Phase G Operator Review Notes",
        "",
        "Status: generated for offline review; human sign-off is not recorded in this artifact.",
        "",
        "Review each rendered context block for omissions, stale context, noise, provenance, and budget clipping.",
        "",
    ]
    for item in report["operator_review"]["items"]:
        path = context_paths.get(item["key"], item["context_block_path"])
        lines.extend(
            [
                f"## {item['key']}",
                "",
                f"- Project: `{item['project']}`",
                f"- Mode: `{item['mode']}`",
                f"- Decision: `{item['decision']}`",
                f"- Missing required: `{item['missing_required']}`",
                f"- Flags: `{item['flags']}`",
                f"- Context block: `{path}`",
                "- Operator finding: pending",
                "",
            ]
        )
    return "\n".join(lines)


def _optional_positive_int(value: Any) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    return parsed if parsed > 0 else None


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise BridgeOpsDrillError(f"file_not_found:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_file_name(value: str) -> str:
    import re

    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-") or "case"


def _report_without_context_blocks(report: dict[str, Any]) -> dict[str, Any]:
    out = dict(report)
    out.pop("context_blocks", None)
    return out

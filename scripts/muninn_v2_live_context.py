#!/usr/bin/env python3
"""Render local Phase J Muninn v2 bridge context for Codex-style sessions.

This helper is intentionally local and read-only. It selects a project-scoped
v2 shadow DB from configs/muninn_v2_live_trial.json, runs the v2 bridge
rehydrate operation, writes bridge audit artifacts under logs/live_trial/, and
prints a deterministic context block for the operator/agent.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from muninn.v2.bridge import run_bridge_request  # noqa: E402
from muninn.v2.bridge.contracts import safe_request_id  # noqa: E402


DEFAULT_CONFIG = REPO_ROOT / "configs" / "muninn_v2_live_trial.json"


class LiveContextError(RuntimeError):
    """Raised when the local v2 live-trial context path cannot run."""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render Muninn v2 local live-trial context.")
    parser.add_argument("--query", required=True, help="Task/query text for context retrieval.")
    parser.add_argument("--cwd", default=os.getcwd(), help="Project cwd to resolve; defaults to current directory.")
    parser.add_argument("--project", help="Explicit configured project name override.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Phase J live-trial config JSON.")
    parser.add_argument("--out-dir", help="Override output artifact directory.")
    parser.add_argument("--limit", type=int, help="Override result limit within policy cap.")
    parser.add_argument("--max-chars", type=int, help="Override context budget within policy cap.")
    parser.add_argument("--retrieval-mode", choices=["hybrid", "lexical", "vector"], help="Retrieval mode.")
    parser.add_argument("--no-recent-supplement", action="store_true", help="Disable recent supplement stage.")
    parser.add_argument("--request-id", help="Stable request id for replay/audit.")
    parser.add_argument("--json", action="store_true", help="Print bridge response JSON instead of Markdown context.")
    args = parser.parse_args(argv)

    try:
        config = _load_config(Path(args.config))
        project = _select_project(config, cwd=Path(args.cwd), project_name=args.project)
        out_dir = _output_dir(config, project, args.out_dir, args.request_id)
        policy = _build_policy(config, project)
        request = _build_request(config, project, args)
        response = run_bridge_request(
            v2_db=_resolve_repo_path(project["v2_db"]),
            policy=policy,
            request=request,
            out_dir=out_dir,
        )
        context = _render_context(response, project)
        _write_event(config, project, request, response, out_dir)
        if args.json:
            print(json.dumps(response, indent=2, sort_keys=True))
        else:
            print(context)
        return 0 if response.get("status") == "ok" else 2
    except Exception as exc:
        _write_error_event(Path(args.config), args, exc)
        print(f"Muninn v2 live-trial context failed: {exc}", file=sys.stderr)
        return 1


def _load_config(path: Path) -> dict[str, Any]:
    target = _resolve_repo_path(path)
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "muninn.v2.live_trial_config.v1":
        raise LiveContextError("unsupported_live_trial_config_schema")
    if payload.get("adaptive_default") is not False:
        raise LiveContextError("adaptive_default_must_be_false")
    return payload


def _select_project(config: dict[str, Any], *, cwd: Path, project_name: str | None) -> dict[str, Any]:
    projects = [item for item in config.get("projects", []) if item.get("enabled_for_live_trial")]
    if project_name:
        matches = [item for item in projects if str(item.get("name")).lower() == project_name.lower()]
        if not matches:
            raise LiveContextError(f"project_not_configured:{project_name}")
        return matches[0]

    current = cwd.expanduser().resolve()
    matched: list[tuple[int, dict[str, Any]]] = []
    for project in projects:
        root = Path(str(project.get("project_path") or "")).expanduser()
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if current == resolved or resolved in current.parents:
            matched.append((len(str(resolved)), project))
    if not matched:
        raise LiveContextError(f"no_live_trial_project_for_cwd:{current}")
    matched.sort(key=lambda item: item[0], reverse=True)
    return matched[0][1]


def _build_policy(config: dict[str, Any], project: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "BridgeCapabilityPolicyV1",
        "consumer_id": config["consumer_id"],
        "allowed_operations": ["health", "search", "rehydrate", "explain"],
        "allowed_space_keys": [project["space_key"]],
        "allowed_project_paths": [project["project_path"]],
        "max_results": int(config.get("max_results") or 12),
        "max_context_chars": int(config.get("max_context_chars") or 12000),
        "allow_adaptive_scoring": False,
        "allow_reinforcement_read": True,
        "allow_reinforcement_write": False,
        "allow_cross_project": False,
        "require_evidence": bool(project.get("require_evidence", config.get("include_evidence", True))),
        "require_explanations": True,
        "audit_log_required": True,
    }


def _build_request(config: dict[str, Any], project: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    request_id = safe_request_id(
        args.request_id
        or f"phase-j-{_slug(project['name'])}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    )
    return {
        "schema_version": "BridgeRequestV1",
        "operation": "rehydrate",
        "consumer_id": config["consumer_id"],
        "request_id": request_id,
        "query": args.query,
        "space_key": project["space_key"],
        "project_path": project["project_path"],
        "limit": int(args.limit or config.get("max_results") or 12),
        "primary_limit": int(config.get("primary_limit") or 3),
        "retrieval_mode": args.retrieval_mode or config.get("retrieval_mode") or "hybrid",
        "max_context_chars": int(args.max_chars or config.get("max_context_chars") or 12000),
        "include_evidence": bool(config.get("include_evidence", True)),
        "include_explanations": bool(config.get("include_explanations", True)),
        "allow_adaptive_scoring": False,
        "allow_reinforcement_write": False,
        "recent_supplement": not args.no_recent_supplement,
        "strict": bool(config.get("strict", True)),
    }


def _output_dir(
    config: dict[str, Any],
    project: dict[str, Any],
    override: str | None,
    request_id: str | None,
) -> Path:
    if override:
        return _resolve_repo_path(override)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rid = safe_request_id(request_id or stamp)
    return _resolve_repo_path(config.get("artifact_dir") or "logs/live_trial/artifacts") / _slug(project["name"]) / rid


def _render_context(response: dict[str, Any], project: dict[str, Any]) -> str:
    lines = [
        "# Muninn v2 Live-Trial Context",
        "",
        f"- Project: {project['name']}",
        f"- Status: `{response.get('status')}`",
        f"- Request: `{response.get('request_id')}`",
        f"- Policy allowed: `{response.get('policy_decision', {}).get('allowed')}`",
        f"- Degraded: `{response.get('degradation', {}).get('degraded')}` "
        f"{response.get('degradation', {}).get('reason_codes') or []}",
    ]
    if response.get("status") != "ok":
        lines.extend(["", "## Error", "", json.dumps(response.get("error"), indent=2, sort_keys=True)])
        return "\n".join(lines) + "\n"

    rehydrate = response.get("result", {}).get("rehydrate_response", {})
    selected = rehydrate.get("selected_memory", {})
    cards = selected.get("cards") or []
    briefing = rehydrate.get("agent_briefing", {})
    uncertainty = rehydrate.get("uncertainty", {})

    lines.extend(
        [
            "",
            "## Agent Briefing",
            "",
        ]
    )
    bullets = briefing.get("bullets") or []
    if bullets:
        lines.extend(f"- {item}" for item in bullets)
    else:
        lines.append("- No briefing bullets were generated from selected memory.")

    lines.extend(["", "## Selected Memory", ""])
    for idx, card in enumerate(cards, 1):
        explanation = card.get("explanation") or {}
        reason = explanation.get("reason_code") or explanation.get("retrieval_path") or "selected"
        lines.extend(
            [
                f"{idx}. {card.get('title') or card.get('id')}",
                f"   - id: `{card.get('id')}` kind: `{card.get('kind')}` reason: `{reason}`",
                f"   - summary: {card.get('summary') or card.get('body_excerpt') or '(no summary)'}",
            ]
        )
        evidence = card.get("evidence") or []
        if evidence:
            refs = [str(item.get("ref") or item.get("id")) for item in evidence[:3]]
            lines.append(f"   - evidence: {', '.join(refs)}")
        if explanation:
            lines.append(f"   - path: `{explanation.get('retrieval_path')}` vector_used: `{explanation.get('vector_used')}`")

    gaps = uncertainty.get("context_gaps") or rehydrate.get("context_gaps") or []
    lines.extend(["", "## Context Gaps / Uncertainty", ""])
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- No explicit context gaps were reported by the v2 response.")

    lines.extend(
        [
            "",
            "## Audit",
            "",
            f"- trace_id: `{response.get('audit', {}).get('trace_id')}`",
            f"- input_hash: `{response.get('audit', {}).get('input_hash')}`",
            f"- policy_hash: `{response.get('audit', {}).get('policy_hash')}`",
            f"- response_hash: `{response.get('audit', {}).get('response_hash')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_event(
    config: dict[str, Any],
    project: dict[str, Any],
    request: dict[str, Any],
    response: dict[str, Any],
    out_dir: Path,
) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "v2_live_trial_context_read",
        "project": project.get("name"),
        "project_path": project.get("project_path"),
        "space_key": project.get("space_key"),
        "request_id": request.get("request_id"),
        "query": request.get("query"),
        "status": response.get("status"),
        "policy_allowed": response.get("policy_decision", {}).get("allowed"),
        "degraded": response.get("degradation", {}).get("degraded"),
        "degradation_reasons": response.get("degradation", {}).get("reason_codes") or [],
        "adaptive_default": False,
        "adaptive_requested": bool(request.get("allow_adaptive_scoring")),
        "write_path": config.get("write_path"),
        "out_dir": str(out_dir),
        "response_hash": response.get("audit", {}).get("response_hash"),
    }
    _append_jsonl(_resolve_repo_path(config.get("log_dir") or "logs/live_trial") / "muninn_v2_live_trial_events.jsonl", event)


def _write_error_event(config_path: Path, args: argparse.Namespace, exc: Exception) -> None:
    try:
        config = _load_config(config_path)
        log_dir = _resolve_repo_path(config.get("log_dir") or "logs/live_trial")
    except Exception:
        log_dir = REPO_ROOT / "logs" / "live_trial"
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "v2_live_trial_context_error",
        "cwd": args.cwd,
        "project": args.project,
        "query": args.query,
        "error": str(exc),
        "fallback_required": "v1_mcp_manual_after_logged_v2_failure",
    }
    _append_jsonl(log_dir / "muninn_v2_live_trial_events.jsonl", event)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else REPO_ROOT / path


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "project"


if __name__ == "__main__":
    raise SystemExit(main())

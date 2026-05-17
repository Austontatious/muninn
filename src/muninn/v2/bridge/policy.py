from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import BRIDGE_POLICY_SCHEMA_VERSION, SUPPORTED_OPERATIONS, load_json_object


@dataclass
class PolicyDecision:
    allowed: bool
    reason_codes: list[str] = field(default_factory=list)
    clamps: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": bool(self.allowed),
            "reason_codes": list(self.reason_codes),
            "clamps": dict(self.clamps),
        }


def load_bridge_policy(path: str | Path) -> dict[str, Any]:
    policy = load_json_object(path)
    if policy.get("schema_version") != BRIDGE_POLICY_SCHEMA_VERSION:
        raise ValueError("unsupported_bridge_policy_schema_version")
    return policy


def evaluate_policy(request: dict[str, Any], policy: dict[str, Any]) -> PolicyDecision:
    reasons: list[str] = []
    clamps: dict[str, Any] = {}
    operation = str(request.get("operation") or "")
    consumer_id = str(request.get("consumer_id") or "").strip()

    if not consumer_id:
        reasons.append("missing_consumer_id")
    elif consumer_id != str(policy.get("consumer_id") or ""):
        reasons.append("consumer_not_allowed")

    allowed_operations = set(str(item) for item in policy.get("allowed_operations") or [])
    if operation not in SUPPORTED_OPERATIONS:
        reasons.append("unsupported_operation")
    elif operation not in allowed_operations:
        reasons.append("operation_not_allowed")

    if operation in {"search", "rehydrate", "explain"}:
        _check_project_scope(request, policy, reasons)

    if bool(request.get("allow_adaptive_scoring")) and not bool(policy.get("allow_adaptive_scoring")):
        reasons.append("adaptive_scoring_not_allowed")
    if bool(request.get("allow_reinforcement_write")):
        reasons.append("reinforcement_write_not_allowed")
    if bool(policy.get("require_evidence")) and request.get("include_evidence") is False:
        reasons.append("evidence_required")
    if bool(policy.get("require_explanations")) and request.get("include_explanations") is False:
        reasons.append("explanations_required")

    max_results = _positive_int(policy.get("max_results"))
    requested_limit = _positive_int(request.get("limit"))
    if max_results and requested_limit and requested_limit > max_results:
        clamps["limit"] = {"requested": requested_limit, "applied": max_results}
    max_context = _positive_int(policy.get("max_context_chars"))
    requested_context = _positive_int(request.get("max_context_chars"))
    if max_context and requested_context and requested_context > max_context:
        clamps["max_context_chars"] = {"requested": requested_context, "applied": max_context}

    return PolicyDecision(allowed=not reasons, reason_codes=reasons, clamps=clamps)


def effective_limit(request: dict[str, Any], policy: dict[str, Any], decision: PolicyDecision) -> int:
    if "limit" in decision.clamps:
        return int(decision.clamps["limit"]["applied"])
    value = _positive_int(request.get("limit")) or _positive_int(policy.get("max_results")) or 10
    max_results = _positive_int(policy.get("max_results"))
    return min(value, max_results) if max_results else value


def effective_max_context_chars(request: dict[str, Any], policy: dict[str, Any], decision: PolicyDecision) -> int | None:
    if "max_context_chars" in decision.clamps:
        return int(decision.clamps["max_context_chars"]["applied"])
    value = _positive_int(request.get("max_context_chars"))
    max_context = _positive_int(policy.get("max_context_chars"))
    if value and max_context:
        return min(value, max_context)
    return value or max_context


def _check_project_scope(request: dict[str, Any], policy: dict[str, Any], reasons: list[str]) -> None:
    space_key = str(request.get("space_key") or "").strip()
    project_path = str(request.get("project_path") or "").strip()
    if not space_key or not project_path:
        reasons.append("missing_project_scope")
        return
    allowed_spaces = [str(item) for item in policy.get("allowed_space_keys") or []]
    allowed_paths = [str(item) for item in policy.get("allowed_project_paths") or []]
    allow_cross_project = bool(policy.get("allow_cross_project"))
    if not allow_cross_project:
        if not allowed_spaces:
            reasons.append("no_allowed_space_keys_configured")
        elif space_key not in allowed_spaces:
            reasons.append("space_not_allowed")
        if not allowed_paths:
            reasons.append("no_allowed_project_paths_configured")
        elif project_path not in allowed_paths:
            reasons.append("project_path_not_allowed")


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None

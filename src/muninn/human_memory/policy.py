from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal

from .cards import card_upsert, cards_recent
from .interactions import (
    count_similar_interaction_events,
    derive_signal_key,
    link_promoted_card,
    record_interaction_event,
)
from .spaces import resolve_space_lookup_keys

PolicyKind = Literal[
    "policy.directive",
    "policy.preference",
    "policy.anti_pattern",
    "workflow.heuristic",
    "tooling.preference",
    "rehydration.priority",
]
SignalType = Literal["evaluative", "directive", "mixed"]
OutcomeType = Literal["success", "partial", "failure", "corrected"]

POLICY_KINDS: tuple[PolicyKind, ...] = (
    "policy.directive",
    "policy.preference",
    "policy.anti_pattern",
    "workflow.heuristic",
    "tooling.preference",
    "rehydration.priority",
)
SIGNAL_TYPES: tuple[SignalType, ...] = ("evaluative", "directive", "mixed")
OUTCOME_TYPES: tuple[OutcomeType, ...] = ("success", "partial", "failure", "corrected")


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _normalize_optional_text(value: Any) -> str | None:
    text = " ".join(str(value or "").strip().split())
    return text or None


def _normalize_kind(value: str) -> PolicyKind:
    normalized = _normalize_text(value)
    if normalized not in POLICY_KINDS:
        allowed = ",".join(POLICY_KINDS)
        raise ValueError(f"invalid_policy_kind:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_signal_type(value: str | None) -> SignalType:
    normalized = _normalize_text(value or "directive")
    if normalized not in SIGNAL_TYPES:
        allowed = ",".join(SIGNAL_TYPES)
        raise ValueError(f"invalid_signal_type:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_outcome_type(value: str | None) -> OutcomeType:
    normalized = _normalize_text(value or "success")
    if normalized not in OUTCOME_TYPES:
        allowed = ",".join(OUTCOME_TYPES)
        raise ValueError(f"invalid_outcome_type:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _coerce_confidence(value: Any, *, default: float = 0.65) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = default
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _normalize_scope(scope_type: str | None, scope_key: str | None) -> dict[str, str | None]:
    normalized_scope_type = _normalize_text(scope_type or "project") or "project"
    normalized_scope_key = _normalize_optional_text(scope_key)
    return {"type": normalized_scope_type, "key": normalized_scope_key}


def _normalize_tag_names(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        name = _normalize_text(raw)
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _policy_tags(
    *,
    kind: PolicyKind,
    scope_type: str,
    signal_type: SignalType,
    tool_name: str | None,
    task_type: str | None,
    tags: list[str] | None,
) -> list[str]:
    out = ["policy-state", kind, scope_type, signal_type]
    if tool_name:
        out.append(f"tool:{_normalize_text(tool_name)}")
    if task_type:
        out.append(f"task:{_normalize_text(task_type)}")
    out.extend(_normalize_tag_names(tags))
    return _normalize_tag_names(out)


def _parse_context_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _extract_policy_state(row: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    context = _parse_context_json(row.get("context_json"))
    raw_policy = context.get("policy_state")
    if not isinstance(raw_policy, dict):
        return None, "missing_policy_state"
    kind = _normalize_text(row.get("kind"))
    if kind not in POLICY_KINDS:
        return None, "kind_not_policy"
    scope = raw_policy.get("scope") if isinstance(raw_policy.get("scope"), dict) else {}
    try:
        return (
            {
                "kind": kind,
                "signal_type": _normalize_signal_type(str(raw_policy.get("signal_type") or "directive")),
                "outcome": _normalize_outcome_type(str(raw_policy.get("outcome") or "success")),
                "scope": {
                    "type": _normalize_text(scope.get("type") or "project") or "project",
                    "key": _normalize_optional_text(scope.get("key")),
                },
                "lesson": _normalize_optional_text(raw_policy.get("lesson")),
                "preferred_behavior": _normalize_optional_text(raw_policy.get("preferred_behavior")),
                "anti_pattern": _normalize_optional_text(raw_policy.get("anti_pattern")),
                "confidence": _coerce_confidence(raw_policy.get("confidence"), default=0.65),
                "repetition_count": max(1, int(raw_policy.get("repetition_count") or 1)),
                "tool_name": _normalize_optional_text(raw_policy.get("tool_name")),
                "task_type": _normalize_optional_text(raw_policy.get("task_type")),
                "source_interaction_id": _normalize_optional_text(raw_policy.get("source_interaction_id")),
                "signal_key": _normalize_optional_text(raw_policy.get("signal_key")),
                "supersedes_card_id": _normalize_optional_text(raw_policy.get("supersedes_card_id")),
            },
            None,
        )
    except ValueError as exc:
        return None, str(exc)


def _parse_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    if "T" not in normalized and " " in normalized:
        normalized = normalized.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _recency_score(updated_at: Any) -> float:
    parsed = _parse_ts(updated_at)
    if parsed is None:
        return 0.0
    age_days = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)
    return max(0.0, 0.2 - min(0.2, age_days * 0.01))


def _token_overlap_score(query: str | None, row: dict[str, Any], policy_state: dict[str, Any]) -> float:
    text = _normalize_text(query)
    if not text:
        return 0.0
    tokens = {token for token in text.split() if token}
    haystack = " ".join(
        filter(
            None,
            [
                _normalize_text(row.get("title")),
                _normalize_text(row.get("summary")),
                _normalize_text(row.get("body")),
                _normalize_text(policy_state.get("lesson")),
                _normalize_text(policy_state.get("preferred_behavior")),
                _normalize_text(policy_state.get("anti_pattern")),
                " ".join(_normalize_tag_names(row.get("tags"))),
            ],
        )
    )
    if not haystack:
        return 0.0
    matched = sum(1 for token in tokens if token in haystack)
    return min(0.35, 0.07 * matched)


def policy_card_upsert(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    kind: str,
    title: str,
    summary: str,
    body: str,
    signal_type: str = "directive",
    outcome: str = "success",
    scope_type: str = "project",
    scope_key: str | None = None,
    lesson: str | None = None,
    preferred_behavior: str | None = None,
    anti_pattern: str | None = None,
    confidence: float = 0.65,
    repetition_count: int = 1,
    tool_name: str | None = None,
    task_type: str | None = None,
    signal_key: str | None = None,
    source_interaction_id: str | None = None,
    supersedes_card_id: str | None = None,
    tags: list[str] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    created_by_client_name: str | None = None,
    status: str = "active",
    salience: float = 0.7,
    card_id: str | None = None,
    context_json: dict[str, Any] | None = None,
    dedupe_by_fingerprint: bool = True,
    commit: bool = True,
) -> str:
    normalized_kind = _normalize_kind(kind)
    normalized_signal_type = _normalize_signal_type(signal_type)
    normalized_outcome = _normalize_outcome_type(outcome)
    normalized_scope = _normalize_scope(scope_type, scope_key)
    normalized_tool_name = _normalize_optional_text(tool_name)
    normalized_task_type = _normalize_optional_text(task_type)
    normalized_confidence = _coerce_confidence(confidence)
    normalized_lesson = _normalize_optional_text(lesson)
    normalized_preferred = _normalize_optional_text(preferred_behavior)
    normalized_anti_pattern = _normalize_optional_text(anti_pattern)
    normalized_signal_key = _normalize_optional_text(signal_key) or derive_signal_key(
        normalized_kind,
        normalized_scope["type"],
        normalized_scope["key"],
        normalized_lesson,
        normalized_preferred,
        normalized_anti_pattern,
        normalized_tool_name,
        normalized_task_type,
    )

    merged_context = dict(context_json or {})
    merged_context["policy_state"] = {
        "schema_version": 1,
        "signal_type": normalized_signal_type,
        "outcome": normalized_outcome,
        "scope": normalized_scope,
        "lesson": normalized_lesson,
        "preferred_behavior": normalized_preferred,
        "anti_pattern": normalized_anti_pattern,
        "confidence": normalized_confidence,
        "repetition_count": max(1, int(repetition_count)),
        "tool_name": normalized_tool_name,
        "task_type": normalized_task_type,
        "signal_key": normalized_signal_key,
        "source_interaction_id": _normalize_optional_text(source_interaction_id),
        "supersedes_card_id": _normalize_optional_text(supersedes_card_id),
    }

    return card_upsert(
        conn,
        user_id=user_id,
        space_key=space_key,
        kind=normalized_kind,
        title=title,
        summary=summary,
        body=body,
        status=status,
        salience=salience,
        tags=_policy_tags(
            kind=normalized_kind,
            scope_type=normalized_scope["type"] or "project",
            signal_type=normalized_signal_type,
            tool_name=normalized_tool_name,
            task_type=normalized_task_type,
            tags=tags,
        ),
        created_by_client_name=created_by_client_name,
        source_confidence=normalized_confidence,
        context_json=merged_context,
        card_id=card_id,
        evidence_refs=evidence_refs,
        dedupe_by_fingerprint=dedupe_by_fingerprint,
        commit=commit,
    )


def _query_rows_for_space(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    limit: int,
    include_body: bool,
) -> list[dict[str, Any]]:
    return cards_recent(
        conn,
        user_id=user_id,
        space_key=space_key,
        kinds=list(POLICY_KINDS),
        limit=limit,
        include_body=include_body,
        include_context=True,
    )


def query_policy_cards(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    query: str | None = None,
    scope_types: list[str] | None = None,
    scope_key: str | None = None,
    tool_name: str | None = None,
    task_type: str | None = None,
    include_global: bool = True,
    limit: int = 10,
    include_body: bool = False,
) -> dict[str, Any]:
    lookup_keys = resolve_space_lookup_keys(conn, user_id=user_id, space_key=space_key)
    canonical_key = lookup_keys[0]
    if include_global and "global" not in lookup_keys:
        lookup_keys.append("global")

    normalized_scope_types = {_normalize_text(item) for item in (scope_types or []) if _normalize_text(item)}
    normalized_scope_key = _normalize_optional_text(scope_key)
    normalized_tool_name = _normalize_optional_text(tool_name)
    normalized_task_type = _normalize_optional_text(task_type)
    max_results = max(1, int(limit))
    scan_limit = min(200, max(max_results * 4, 20))

    ranked: list[tuple[float, dict[str, Any]]] = []
    seen: set[str] = set()
    diagnostics = {
        "scanned_rows": 0,
        "invalid_policy_rows": 0,
        "invalid_reasons": {},
    }
    for key in lookup_keys:
        for row in _query_rows_for_space(
            conn,
            user_id=user_id,
            space_key=key,
            limit=scan_limit,
            include_body=include_body,
        ):
            diagnostics["scanned_rows"] += 1
            card_id = str(row.get("id", ""))
            if not card_id or card_id in seen:
                continue
            policy_state, error_reason = _extract_policy_state(row)
            if policy_state is None:
                diagnostics["invalid_policy_rows"] += 1
                if error_reason:
                    diagnostics["invalid_reasons"][error_reason] = (
                        int(diagnostics["invalid_reasons"].get(error_reason) or 0) + 1
                    )
                continue
            scope = policy_state.get("scope") or {}
            if normalized_scope_types and str(scope.get("type") or "") not in normalized_scope_types:
                continue
            if normalized_scope_key and str(scope.get("key") or "") != normalized_scope_key:
                continue
            if normalized_tool_name and policy_state.get("tool_name") != normalized_tool_name:
                continue
            if normalized_task_type and policy_state.get("task_type") != normalized_task_type:
                continue
            base_score = 0.8 if key == canonical_key else 0.55
            if key == "global":
                base_score = 0.35
            evidence_bonus = min(0.2, 0.05 * int(row.get("evidence_count") or 0))
            confidence_bonus = min(0.3, 0.3 * float(policy_state.get("confidence") or 0.0))
            repetition_bonus = min(0.2, 0.05 * max(0, int(policy_state.get("repetition_count") or 1) - 1))
            total_score = (
                base_score
                + evidence_bonus
                + confidence_bonus
                + repetition_bonus
                + _recency_score(row.get("updated_at"))
                + _token_overlap_score(query, row, policy_state)
            )
            ranked.append(
                (
                    total_score,
                    {
                        "id": card_id,
                        "space_key": str(row.get("space_key", "")),
                        "kind": str(row.get("kind", "")),
                        "title": str(row.get("title", "")),
                        "summary": str(row.get("summary", "")),
                        "body": row.get("body"),
                        "updated_at": row.get("updated_at"),
                        "created_at": row.get("created_at"),
                        "tags": row.get("tags", []),
                        "evidence_count": int(row.get("evidence_count") or 0),
                        "has_evidence": bool(row.get("has_evidence")),
                        "policy": policy_state,
                        "score": round(total_score, 6),
                    },
                )
            )
            seen.add(card_id)

    ranked.sort(
        key=lambda item: (
            -item[0],
            -int(item[1].get("evidence_count", 0)),
            str(item[1].get("updated_at") or ""),
        )
    )
    cards = [item[1] for item in ranked[:max_results]]
    if not include_body:
        for card in cards:
            card.pop("body", None)
    return {
        "cards": cards,
        "filters": {
            "query": query,
            "scope_types": sorted(normalized_scope_types),
            "scope_key": normalized_scope_key,
            "tool_name": normalized_tool_name,
            "task_type": normalized_task_type,
            "lookup_keys": lookup_keys,
            "limit": max_results,
        },
        "diagnostics": diagnostics,
    }


def _infer_behavior_hints(summary: str) -> tuple[str | None, str | None]:
    normalized = _normalize_text(summary)
    if "check the repo" in normalized or "check the file" in normalized:
        return (
            "Check repo/files before relying on recalled summaries for implementation questions.",
            "Do not answer implementation-detail questions from stale memory alone.",
        )
    if "exact commands" in normalized and "not a summary" in normalized:
        return (
            "Prefer exact executable commands over high-level summaries when troubleshooting terminal or infrastructure tasks.",
            "Do not replace executable troubleshooting steps with abstract summaries in terminal-first contexts.",
        )
    if "narrower query" in normalized and "succeeds" in normalized:
        return (
            "Start with narrower, concrete queries for this tool/context before broadening.",
            "Broad exploratory queries have poor yield in this context.",
        )
    return None, None


def _choose_policy_kind(
    *,
    signal_type: SignalType,
    preferred_behavior: str | None,
    anti_pattern: str | None,
    tool_name: str | None,
    task_type: str | None,
) -> PolicyKind:
    if task_type and _normalize_text(task_type) == "rehydration":
        return "rehydration.priority"
    if tool_name:
        return "tooling.preference"
    if anti_pattern and signal_type == "evaluative":
        return "policy.anti_pattern"
    if preferred_behavior and signal_type in {"directive", "mixed"}:
        return "policy.directive"
    if preferred_behavior:
        return "policy.preference"
    return "workflow.heuristic"


def _existing_policy_card(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    signal_key: str,
) -> dict[str, Any] | None:
    payload = query_policy_cards(
        conn,
        user_id=user_id,
        space_key=space_key,
        include_global=False,
        limit=50,
        include_body=True,
    )
    for row in payload["cards"]:
        policy_state = row.get("policy") or {}
        if str(policy_state.get("signal_key") or "") == signal_key:
            return row
    return None


def learn_policy_signal(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    summary: str,
    signal_type: str,
    outcome: str,
    scope_type: str = "project",
    scope_key: str | None = None,
    lesson: str | None = None,
    preferred_behavior: str | None = None,
    anti_pattern: str | None = None,
    confidence: float | None = None,
    tool_name: str | None = None,
    task_type: str | None = None,
    session_id: str | None = None,
    created_by_client_name: str | None = None,
    tags: list[str] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    promotion_threshold_confidence = 0.82
    promotion_threshold_repetition = 2
    normalized_signal_type = _normalize_signal_type(signal_type)
    normalized_outcome = _normalize_outcome_type(outcome)
    normalized_scope = _normalize_scope(scope_type, scope_key)
    normalized_summary = _normalize_optional_text(summary)
    if not normalized_summary:
        raise ValueError("invalid_policy_summary")

    inferred_preferred, inferred_anti_pattern = _infer_behavior_hints(normalized_summary)
    normalized_lesson = _normalize_optional_text(lesson) or normalized_summary
    normalized_preferred = _normalize_optional_text(preferred_behavior) or inferred_preferred
    normalized_anti_pattern = _normalize_optional_text(anti_pattern) or inferred_anti_pattern
    normalized_tool_name = _normalize_optional_text(tool_name)
    normalized_task_type = _normalize_optional_text(task_type)

    signal_key = derive_signal_key(
        normalized_signal_type,
        normalized_scope["type"],
        normalized_scope["key"],
        normalized_lesson,
        normalized_preferred,
        normalized_anti_pattern,
        normalized_tool_name,
        normalized_task_type,
    )
    interaction_id = record_interaction_event(
        conn,
        user_id=user_id,
        space_key=space_key,
        event_type="policy_signal",
        actor="agent",
        summary=normalized_summary,
        payload=raw_payload
        or {
            "lesson": normalized_lesson,
            "preferred_behavior": normalized_preferred,
            "anti_pattern": normalized_anti_pattern,
            "tool_name": normalized_tool_name,
            "task_type": normalized_task_type,
        },
        signal_type=normalized_signal_type,
        outcome_type=normalized_outcome,
        scope_type=normalized_scope["type"] or "project",
        scope_key=normalized_scope["key"],
        signal_key=signal_key,
        session_id=session_id,
        created_by_client_name=created_by_client_name,
        commit=False,
    )
    repetition_count = count_similar_interaction_events(
        conn,
        user_id=user_id,
        space_key=space_key,
        signal_key=signal_key,
        scope_type=normalized_scope["type"],
        scope_key=normalized_scope["key"],
    )
    effective_confidence = _coerce_confidence(confidence, default=0.62)
    if normalized_signal_type in {"directive", "mixed"}:
        effective_confidence = max(effective_confidence, 0.78)
    if repetition_count > 1:
        effective_confidence = min(1.0, effective_confidence + min(0.2, 0.08 * (repetition_count - 1)))

    promotion_attempted = bool(normalized_preferred or normalized_anti_pattern)
    should_promote = promotion_attempted and (
        normalized_signal_type in {"directive", "mixed"}
        or repetition_count >= promotion_threshold_repetition
        or effective_confidence >= promotion_threshold_confidence
    )
    promotion_reason = "insufficient_signal"
    if not promotion_attempted:
        promotion_reason = "no_behavior_hint"
    elif normalized_signal_type in {"directive", "mixed"}:
        promotion_reason = "directive_signal"
    elif repetition_count >= promotion_threshold_repetition:
        promotion_reason = "repetition_threshold_met"
    elif effective_confidence >= promotion_threshold_confidence:
        promotion_reason = "confidence_threshold_met"
    if not should_promote:
        conn.commit()
        return {
            "interaction_id": interaction_id,
            "interaction_event_captured": True,
            "promoted": False,
            "policy_card_id": None,
            "confidence": round(effective_confidence, 4),
            "repetition_count": repetition_count,
            "signal_key": signal_key,
            "promotion": {
                "attempted": promotion_attempted,
                "reason": promotion_reason,
                "threshold_confidence": promotion_threshold_confidence,
                "threshold_repetition": promotion_threshold_repetition,
                "updated_existing": False,
            },
        }

    kind = _choose_policy_kind(
        signal_type=normalized_signal_type,
        preferred_behavior=normalized_preferred,
        anti_pattern=normalized_anti_pattern,
        tool_name=normalized_tool_name,
        task_type=normalized_task_type,
    )
    title = normalized_preferred or normalized_anti_pattern or normalized_lesson
    summary_text = normalized_preferred or normalized_lesson
    body_lines = [
        f"Lesson: {normalized_lesson}",
        f"Preferred behavior: {normalized_preferred or 'n/a'}",
        f"Anti-pattern: {normalized_anti_pattern or 'n/a'}",
        f"Outcome: {normalized_outcome}",
        f"Scope: {normalized_scope['type']}:{normalized_scope['key'] or '*'}",
        f"Confidence: {round(effective_confidence, 4)}",
        f"Repetition count: {repetition_count}",
    ]
    if normalized_tool_name:
        body_lines.append(f"Tool: {normalized_tool_name}")
    if normalized_task_type:
        body_lines.append(f"Task type: {normalized_task_type}")
    body = "\n".join(body_lines)

    existing = _existing_policy_card(conn, user_id=user_id, space_key=space_key, signal_key=signal_key)
    if existing is not None:
        existing_policy = existing.get("policy") or {}
        repetition_count = max(repetition_count, int(existing_policy.get("repetition_count") or 1))
        effective_confidence = max(
            effective_confidence,
            _coerce_confidence(existing_policy.get("confidence"), default=effective_confidence),
        )
        promotion_reason = "update_existing_policy_card"

    augmented_evidence = list(evidence_refs or [])
    augmented_evidence.append(
        {
            "type": "log",
            "ref": f"interaction:{interaction_id}",
            "excerpt": normalized_summary[:200],
            "meta_json": {
                "signal_key": signal_key,
                "signal_type": normalized_signal_type,
                "outcome": normalized_outcome,
                "scope_type": normalized_scope["type"],
                "scope_key": normalized_scope["key"],
            },
            "created_by_client_name": created_by_client_name,
        }
    )

    card_id = policy_card_upsert(
        conn,
        user_id=user_id,
        space_key=space_key,
        kind=kind,
        title=title,
        summary=summary_text,
        body=body,
        signal_type=normalized_signal_type,
        outcome=normalized_outcome,
        scope_type=normalized_scope["type"] or "project",
        scope_key=normalized_scope["key"],
        lesson=normalized_lesson,
        preferred_behavior=normalized_preferred,
        anti_pattern=normalized_anti_pattern,
        confidence=effective_confidence,
        repetition_count=repetition_count,
        tool_name=normalized_tool_name,
        task_type=normalized_task_type,
        signal_key=signal_key,
        source_interaction_id=interaction_id,
        tags=tags,
        evidence_refs=augmented_evidence,
        created_by_client_name=created_by_client_name,
        card_id=str(existing.get("id")) if existing is not None else None,
        commit=False,
    )
    link_promoted_card(conn, interaction_id=interaction_id, promoted_card_id=card_id, commit=False)
    conn.commit()
    return {
        "interaction_id": interaction_id,
        "interaction_event_captured": True,
        "promoted": True,
        "policy_card_id": card_id,
        "confidence": round(effective_confidence, 4),
        "repetition_count": repetition_count,
        "signal_key": signal_key,
        "kind": kind,
        "promotion": {
            "attempted": promotion_attempted,
            "reason": promotion_reason,
            "threshold_confidence": promotion_threshold_confidence,
            "threshold_repetition": promotion_threshold_repetition,
            "updated_existing": existing is not None,
            "existing_policy_card_id": str(existing.get("id")) if existing is not None else None,
        },
    }

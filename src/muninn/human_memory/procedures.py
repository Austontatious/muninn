from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, Literal

from .cards import card_supersede, card_upsert, cards_recent

ProcedureOutcomeStatus = Literal["success", "partial_success", "failure"]
ProcedureValidationStatus = Literal["candidate", "validated", "needs_review", "deprecated"]

PROCEDURE_KIND = "procedure.card"
PROCEDURE_TAGS_BASE: tuple[str, ...] = ("procedure", "procedural_memory")
PROCEDURE_VALIDATION_VALUES: tuple[ProcedureValidationStatus, ...] = (
    "candidate",
    "validated",
    "needs_review",
    "deprecated",
)

_VALIDATION_SET = set(PROCEDURE_VALIDATION_VALUES)
_TOKEN_RE = re.compile(r"[a-z0-9_]+")
PROCEDURE_MIN_RETRIEVAL_CONFIDENCE = 0.28
PROCEDURE_UPDATE_MATCH_THRESHOLD = 0.55
PROCEDURE_EVIDENCE_ONLY_MATCH_THRESHOLD = 0.78
PROCEDURE_SUPERSEDE_FAILURE_THRESHOLD = 3
PROCEDURE_CREATE_MIN_ACTIONS = 2
PROCEDURE_MAX_RETURN = 3
_STRUCTURED_EVIDENCE_ALLOWED_TYPES = frozenset({"chat", "log", "diff", "file", "url", "commit", "test"})
_STRUCTURED_EVIDENCE_ALLOWED_KEYS = frozenset({"type", "ref", "excerpt", "meta"})


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _normalize_structured_evidence(
    reflection: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    metadata = reflection.get("metadata")
    if not isinstance(metadata, dict):
        return [], []
    raw_items = metadata.get("structured_evidence")
    if raw_items is None:
        return [], []
    if not isinstance(raw_items, list):
        return [], [
            {
                "code": "invalid_structured_evidence_type",
                "message": "metadata.structured_evidence must be a list of objects",
            }
        ]

    normalized: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    for idx, raw_item in enumerate(raw_items):
        field_prefix = f"metadata.structured_evidence[{idx}]"
        if not isinstance(raw_item, dict):
            warnings.append(
                {
                    "code": "invalid_structured_evidence_item",
                    "message": f"{field_prefix} must be an object",
                }
            )
            continue

        extra_keys = sorted(set(raw_item.keys()) - _STRUCTURED_EVIDENCE_ALLOWED_KEYS)
        if extra_keys:
            warnings.append(
                {
                    "code": "invalid_structured_evidence_extra_keys",
                    "message": f"{field_prefix} has unsupported keys: {','.join(extra_keys)}",
                }
            )
            continue

        evidence_type = _normalize_text(raw_item.get("type")).lower()
        if evidence_type not in _STRUCTURED_EVIDENCE_ALLOWED_TYPES:
            allowed = ",".join(sorted(_STRUCTURED_EVIDENCE_ALLOWED_TYPES))
            warnings.append(
                {
                    "code": "invalid_structured_evidence_type_value",
                    "message": f"{field_prefix}.type must be one of {allowed}",
                }
            )
            continue

        ref_value = raw_item.get("ref")
        if ref_value is not None and not isinstance(ref_value, str):
            warnings.append(
                {
                    "code": "invalid_structured_evidence_ref",
                    "message": f"{field_prefix}.ref must be a string when provided",
                }
            )
            continue

        excerpt_value = raw_item.get("excerpt")
        if excerpt_value is not None and not isinstance(excerpt_value, str):
            warnings.append(
                {
                    "code": "invalid_structured_evidence_excerpt",
                    "message": f"{field_prefix}.excerpt must be a string when provided",
                }
            )
            continue

        meta_value = raw_item.get("meta")
        if meta_value is not None and not isinstance(meta_value, dict):
            warnings.append(
                {
                    "code": "invalid_structured_evidence_meta",
                    "message": f"{field_prefix}.meta must be an object when provided",
                }
            )
            continue

        normalized.append(
            {
                "type": evidence_type,
                "ref": _normalize_text(ref_value) or None,
                "excerpt": _normalize_text(excerpt_value) or None,
                "meta_json": dict(meta_value) if isinstance(meta_value, dict) else None,
            }
        )

    return normalized, warnings


def _normalize_text_list(values: list[Any] | None, *, lower: bool = False) -> list[str]:
    if not values:
        return []
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _normalize_text(raw)
        if not value:
            continue
        dedupe_key = value.lower() if lower else value
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        output.append(value)
    return output


def _normalize_validation_status(value: Any) -> ProcedureValidationStatus:
    normalized = str(value or "candidate").strip().lower() or "candidate"
    if normalized not in _VALIDATION_SET:
        allowed = ",".join(PROCEDURE_VALIDATION_VALUES)
        raise ValueError(f"invalid_procedure_validation_status:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_scope(scope: dict[str, Any] | str | None) -> dict[str, str | None]:
    if scope is None:
        return {"type": "global", "id": None}
    if isinstance(scope, str):
        raw_type = scope
        raw_id = None
    elif isinstance(scope, dict):
        raw_type = scope.get("type")
        raw_id = scope.get("id")
    else:
        raise ValueError("invalid_procedure_scope")

    scope_type = str(raw_type or "global").strip().lower() or "global"
    scope_id = _normalize_text(raw_id) or None
    return {"type": scope_type, "id": scope_id}


def _coerce_confidence(value: Any, *, default: float = 0.65) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = float(default)
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


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


def _tokens(*parts: Any) -> set[str]:
    joined = " ".join(_normalize_text(part).lower() for part in parts if _normalize_text(part))
    return {token for token in _TOKEN_RE.findall(joined) if token}


def _token_overlap_score(query: set[str], *parts: Any) -> float:
    if not query:
        return 0.0
    haystack = _tokens(*parts)
    if not haystack:
        return 0.0
    overlap = len(query.intersection(haystack))
    return min(0.45, overlap * 0.06)


def _validation_bonus(validation_status: ProcedureValidationStatus) -> float:
    if validation_status == "validated":
        return 0.18
    if validation_status == "candidate":
        return 0.08
    if validation_status == "needs_review":
        return -0.08
    return -0.2


def _staleness_penalty(updated_at: Any, *, stale_after_days: int) -> float:
    parsed = _parse_ts(updated_at)
    if parsed is None:
        return 0.05
    age_days = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)
    if age_days <= stale_after_days:
        return 0.0
    return min(0.25, (age_days - stale_after_days) * 0.004)


def _scope_bonus(scope: dict[str, Any]) -> float:
    scope_type = str(scope.get("type") or "").strip().lower()
    if scope_type == "project":
        return 0.08
    if scope_type == "global":
        return 0.03
    if scope_type in {"session", "thread", "one_off"}:
        return -0.08
    return 0.0


def _normalize_context(raw_context: Any) -> dict[str, Any]:
    if isinstance(raw_context, dict):
        return dict(raw_context)
    if isinstance(raw_context, str) and raw_context.strip():
        try:
            loaded = json.loads(raw_context)
            if isinstance(loaded, dict):
                return loaded
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_procedure(row: dict[str, Any]) -> dict[str, Any] | None:
    context = _normalize_context(row.get("context_json"))
    raw_procedure = context.get("procedure")
    if not isinstance(raw_procedure, dict):
        return None

    title = _normalize_text(row.get("title"))
    summary = _normalize_text(row.get("summary"))
    if not title or not summary:
        return None

    trigger_conditions = _normalize_text_list(raw_procedure.get("trigger_conditions"), lower=True)
    steps = _normalize_text_list(raw_procedure.get("steps"))
    if not steps:
        return None

    validation_status = _normalize_validation_status(raw_procedure.get("validation_status"))
    confidence = _coerce_confidence(raw_procedure.get("confidence"), default=_coerce_confidence(row.get("source_confidence")))

    return {
        "schema_version": int(raw_procedure.get("schema_version", 1) or 1),
        "title": title,
        "summary": summary,
        "trigger_conditions": trigger_conditions,
        "scope": _normalize_scope(raw_procedure.get("scope")),
        "steps": steps,
        "tool_requirements": _normalize_text_list(raw_procedure.get("tool_requirements"), lower=True),
        "pitfalls": _normalize_text_list(raw_procedure.get("pitfalls")),
        "verification_checks": _normalize_text_list(raw_procedure.get("verification_checks")),
        "confidence": confidence,
        "validation_status": validation_status,
        "task_types": _normalize_text_list(raw_procedure.get("task_types"), lower=True),
        "provenance": raw_procedure.get("provenance") if isinstance(raw_procedure.get("provenance"), dict) else {},
        "supersedes_card_id": _normalize_text(raw_procedure.get("supersedes_card_id")) or None,
        "superseded_by_card_id": _normalize_text(raw_procedure.get("superseded_by_card_id")) or None,
    }


def _provenance_events(provenance: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(provenance, dict):
        return []
    raw = provenance.get("events")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
    return out


def _failure_count(provenance: dict[str, Any] | None) -> int:
    count = 0
    for event in _provenance_events(provenance):
        if str(event.get("outcome_status") or "").strip().lower() == "failure":
            count += 1
    return count


def _is_reflection_nontrivial(
    *,
    task_label: str,
    actions_taken: list[str],
    tool_requirements: list[str],
    what_failed: str,
    changed_outcome: str,
) -> bool:
    if len(actions_taken) >= PROCEDURE_CREATE_MIN_ACTIONS:
        return True
    if len(tool_requirements) >= 1:
        return True
    if bool(what_failed.strip()) or bool(changed_outcome.strip()):
        return True
    if len(task_label.split()) >= 4:
        return True
    return False


def _material_change_detected(
    *,
    existing: dict[str, Any],
    actions_taken: list[str],
    what_failed: str,
    changed_outcome: str,
) -> bool:
    current_steps = {item.lower() for item in _normalize_text_list(existing.get("steps"))}
    new_steps = [item for item in actions_taken if item.lower() not in current_steps]
    if len(new_steps) >= 2:
        return True
    if bool(what_failed.strip()) and what_failed.strip().lower() not in {
        item.lower() for item in _normalize_text_list(existing.get("pitfalls"))
    }:
        return True
    if bool(changed_outcome.strip()):
        return True
    return False


def _procedure_tags(
    *,
    validation_status: ProcedureValidationStatus,
    scope_type: str,
    task_types: list[str],
    tags: list[str] | None,
) -> list[str]:
    merged = [
        *PROCEDURE_TAGS_BASE,
        f"procedure.validation.{validation_status}",
        f"scope.{scope_type}",
        *task_types,
        *(_normalize_text_list(tags, lower=True) if tags else []),
    ]
    return _normalize_text_list(merged, lower=True)


def procedure_card_upsert(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    title: str,
    summary: str,
    trigger_conditions: list[str],
    scope: dict[str, Any] | str | None,
    steps: list[str],
    tool_requirements: list[str] | None = None,
    pitfalls: list[str] | None = None,
    verification_checks: list[str] | None = None,
    confidence: float = 0.65,
    validation_status: str = "candidate",
    task_types: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
    supersedes_card_id: str | None = None,
    tags: list[str] | None = None,
    body: str | None = None,
    status: str = "active",
    salience: float = 0.7,
    created_by_client_name: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    card_id: str | None = None,
    dedupe_by_fingerprint: bool = True,
    commit: bool = True,
) -> str:
    normalized_title = _normalize_text(title)
    normalized_summary = _normalize_text(summary)
    normalized_steps = _normalize_text_list(steps)
    normalized_triggers = _normalize_text_list(trigger_conditions, lower=True)
    if not normalized_title:
        raise ValueError("invalid_procedure_title")
    if not normalized_summary:
        raise ValueError("invalid_procedure_summary")
    if not normalized_steps:
        raise ValueError("invalid_procedure_steps")

    normalized_scope = _normalize_scope(scope)
    normalized_validation = _normalize_validation_status(validation_status)
    normalized_tools = _normalize_text_list(tool_requirements, lower=True)
    normalized_pitfalls = _normalize_text_list(pitfalls)
    normalized_checks = _normalize_text_list(verification_checks)
    normalized_task_types = _normalize_text_list(task_types, lower=True)
    normalized_confidence = _coerce_confidence(confidence)

    normalized_body = _normalize_text(body)
    if not normalized_body:
        normalized_body = "\n".join(f"{idx + 1}. {step}" for idx, step in enumerate(normalized_steps))

    context_json = {
        "procedure": {
            "schema_version": 1,
            "trigger_conditions": normalized_triggers,
            "scope": normalized_scope,
            "steps": normalized_steps,
            "tool_requirements": normalized_tools,
            "pitfalls": normalized_pitfalls,
            "verification_checks": normalized_checks,
            "confidence": normalized_confidence,
            "validation_status": normalized_validation,
            "task_types": normalized_task_types,
            "provenance": dict(provenance or {}),
            "supersedes_card_id": _normalize_text(supersedes_card_id) or None,
            "superseded_by_card_id": None,
        }
    }

    merged_tags = _procedure_tags(
        validation_status=normalized_validation,
        scope_type=str(normalized_scope.get("type") or "global"),
        task_types=normalized_task_types,
        tags=tags,
    )

    if supersedes_card_id:
        result = card_supersede(
            conn,
            user_id=user_id,
            space_key=space_key,
            old_card_id=supersedes_card_id,
            kind=PROCEDURE_KIND,
            title=normalized_title,
            summary=normalized_summary,
            body=normalized_body,
            status=status,
            salience=salience,
            tags=merged_tags,
            created_by_client_name=created_by_client_name,
            source_confidence=normalized_confidence,
            context_json=context_json,
            evidence_refs=evidence_refs,
            relation_type="supersedes",
        )
        return str(result["new_card_id"])

    return card_upsert(
        conn,
        user_id=user_id,
        space_key=space_key,
        kind=PROCEDURE_KIND,
        title=normalized_title,
        summary=normalized_summary,
        body=normalized_body,
        status=status,
        salience=salience,
        tags=merged_tags,
        created_by_client_name=created_by_client_name,
        source_confidence=normalized_confidence,
        context_json=context_json,
        card_id=card_id,
        evidence_refs=evidence_refs,
        dedupe_by_fingerprint=dedupe_by_fingerprint,
        commit=commit,
    )


def query_procedure_cards(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    task_label: str,
    context_summary: str = "",
    task_type: str | None = None,
    tool_names: list[str] | None = None,
    limit: int = 3,
    max_scan: int = 120,
    stale_after_days: int = 90,
) -> dict[str, Any]:
    bounded_limit = max(1, min(int(limit), PROCEDURE_MAX_RETURN))
    normalized_task_type = _normalize_text(task_type).lower() if task_type else ""
    normalized_tools = _normalize_text_list(tool_names, lower=True)
    task_tokens = _tokens(task_label, context_summary, normalized_task_type, " ".join(normalized_tools))

    rows = cards_recent(
        conn,
        user_id=user_id,
        space_key=space_key,
        kinds=[PROCEDURE_KIND],
        status="active",
        limit=max(10, min(max_scan, 400)),
        include_body=False,
        include_context=True,
    )

    ranked: list[dict[str, Any]] = []
    skipped = 0
    filtered_low_confidence = 0
    for row in rows:
        procedure = _extract_procedure(row)
        if procedure is None:
            skipped += 1
            continue
        if procedure.get("superseded_by_card_id"):
            skipped += 1
            continue

        validation_status = procedure["validation_status"]
        confidence = float(procedure["confidence"])
        if confidence < PROCEDURE_MIN_RETRIEVAL_CONFIDENCE:
            filtered_low_confidence += 1
            continue
        task_types = procedure.get("task_types") or []
        required_tools = procedure.get("tool_requirements") or []
        scope = dict(procedure.get("scope") or {"type": "global", "id": None})

        lexical = _token_overlap_score(
            task_tokens,
            row.get("title"),
            row.get("summary"),
            " ".join(procedure.get("trigger_conditions") or []),
            " ".join(task_types),
            " ".join(required_tools),
            " ".join(procedure.get("pitfalls") or []),
        )
        task_type_bonus = 0.14 if normalized_task_type and normalized_task_type in task_types else 0.0
        tool_bonus = 0.0
        if normalized_tools and required_tools:
            overlap = len(set(normalized_tools).intersection(set(required_tools)))
            if overlap == 0:
                tool_bonus = -0.08
            else:
                tool_bonus = min(0.16, overlap * 0.08)

        score = (
            0.42 * confidence
            + float(row.get("salience") or 0.0) * 0.12
            + _validation_bonus(validation_status)
            + lexical
            + task_type_bonus
            + tool_bonus
            + _scope_bonus(scope)
            - _staleness_penalty(row.get("updated_at"), stale_after_days=stale_after_days)
        )

        if bool(row.get("is_unstable")):
            score -= 0.1

        if validation_status == "deprecated":
            score -= 0.3

        reasons: list[str] = []
        if lexical > 0.0:
            reasons.append(f"lexical={lexical:.2f}")
        if task_type_bonus > 0.0:
            reasons.append("task_type_match")
        if tool_bonus > 0.0:
            reasons.append("tool_overlap")
        if _scope_bonus(scope) > 0.0:
            reasons.append(f"scope={scope.get('type')}")
        if validation_status == "validated":
            reasons.append("validated")
        if not reasons:
            reasons.append("fallback_score")

        ranked.append(
            {
                "id": str(row.get("id", "")),
                "title": str(row.get("title", "")),
                "summary": str(row.get("summary", "")),
                "when_to_apply": list(procedure.get("trigger_conditions") or []),
                "scope": scope,
                "steps": list(procedure.get("steps") or []),
                "tool_requirements": list(required_tools),
                "pitfalls": list(procedure.get("pitfalls") or []),
                "verification_checks": list(procedure.get("verification_checks") or []),
                "confidence": confidence,
                "validation_status": validation_status,
                "task_types": list(task_types),
                "updated_at": row.get("updated_at"),
                "provenance": dict(procedure.get("provenance") or {}),
                "failure_count": _failure_count(procedure.get("provenance")),
                "selection_reasons": reasons,
                "score": round(score, 6),
            }
        )

    ranked.sort(
        key=lambda item: (
            float(item["score"]),
            float(item.get("confidence") or 0.0),
            str(item.get("updated_at") or ""),
            str(item.get("title") or ""),
        ),
        reverse=True,
    )
    deduped: list[dict[str, Any]] = []
    seen_signatures: set[str] = set()
    for item in ranked:
        signature = "|".join(
            [
                str(item.get("title", "")).strip().lower(),
                ",".join([part.strip().lower() for part in item.get("when_to_apply", [])[:2]]),
                ",".join([part.strip().lower() for part in item.get("steps", [])[:2]]),
            ]
        )
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        deduped.append(item)
    capped = [item for item in deduped if item["score"] > 0.05][:bounded_limit]

    compact = [
        {
            "id": item["id"],
            "title": item["title"],
            "when_to_apply": item["when_to_apply"][:3],
            "steps": item["steps"][:5],
            "pitfalls": item["pitfalls"][:3],
            "confidence": item["confidence"],
            "validation_status": item["validation_status"],
            "selection_reasons": list(item.get("selection_reasons", [])),
            "score": item["score"],
        }
        for item in capped
    ]

    return {
        "procedures": capped,
        "compact": compact,
        "diagnostics": {
            "scanned": len(rows),
            "parsed": len(ranked),
            "deduped": len(deduped),
            "skipped": skipped,
            "filtered_low_confidence": filtered_low_confidence,
            "returned": len(capped),
            "task_type": normalized_task_type,
            "tool_names": normalized_tools,
            "limit": bounded_limit,
        },
    }


def _append_provenance_event(existing: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
    provenance = dict(existing)
    events = provenance.get("events")
    if not isinstance(events, list):
        events = []
    events.append(event)
    provenance["events"] = events[-12:]
    return provenance


def _outcome_confidence_delta(status: ProcedureOutcomeStatus) -> float:
    if status == "success":
        return 0.08
    if status == "partial_success":
        return 0.03
    return -0.18


def ingest_procedure_reflection(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    reflection: dict[str, Any],
    actor: str = "laila",
) -> dict[str, Any]:
    evidence_refs, evidence_warnings = _normalize_structured_evidence(reflection)
    task_label = _normalize_text(reflection.get("task_label") or reflection.get("intent_label"))
    context_summary = _normalize_text(reflection.get("context_summary"))
    status_raw = str(reflection.get("outcome_status") or "partial_success").strip().lower()
    if status_raw not in {"success", "partial_success", "failure"}:
        status_raw = "partial_success"
    outcome_status: ProcedureOutcomeStatus = status_raw  # type: ignore[assignment]

    actions_taken = _normalize_text_list(reflection.get("actions_taken"))
    what_worked = _normalize_text(reflection.get("what_worked"))
    what_failed = _normalize_text(reflection.get("what_failed"))
    changed_outcome = _normalize_text(reflection.get("changed_outcome"))
    reusable = bool(reflection.get("reusable", False))
    nontrivial = _is_reflection_nontrivial(
        task_label=task_label,
        actions_taken=actions_taken,
        tool_requirements=_normalize_text_list(reflection.get("tool_requirements"), lower=True),
        what_failed=what_failed,
        changed_outcome=changed_outcome,
    )

    if not reusable and outcome_status != "failure":
        out = {
            "action": "ignored_non_reusable",
            "reason": "reflection_marked_non_reusable",
            "procedure_card_id": None,
            "outcome_status": outcome_status,
        }
        if evidence_warnings:
            out["warnings"] = evidence_warnings
            out["warning_codes"] = [item["code"] for item in evidence_warnings]
        return out

    candidate_id = _normalize_text(reflection.get("candidate_procedure_id")) or None
    tool_requirements = _normalize_text_list(reflection.get("tool_requirements"), lower=True)
    task_type = _normalize_text(reflection.get("task_type") or reflection.get("workflow_type")).lower() or None

    lookup = query_procedure_cards(
        conn,
        user_id=user_id,
        space_key=space_key,
        task_label=task_label or "task",
        context_summary=context_summary,
        task_type=task_type,
        tool_names=tool_requirements,
        limit=5,
        max_scan=160,
    )
    matches = list(lookup.get("procedures") or [])
    existing = None
    if candidate_id:
        for item in matches:
            if str(item.get("id")) == candidate_id:
                existing = item
                break
    if existing is None and matches:
        top = matches[0]
        if float(top.get("score") or 0.0) >= PROCEDURE_UPDATE_MATCH_THRESHOLD:
            existing = top

    provenance_event = {
        "task_label": task_label,
        "outcome_status": outcome_status,
        "actor": actor,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    if existing is not None:
        match_score = float(existing.get("score") or 0.0)
        updated_confidence = _coerce_confidence(float(existing.get("confidence") or 0.65) + _outcome_confidence_delta(outcome_status))
        updated_validation = str(existing.get("validation_status") or "candidate").strip().lower()
        if outcome_status == "failure" and updated_confidence < 0.55:
            updated_validation = "needs_review"
        elif outcome_status == "success" and updated_confidence >= 0.78 and updated_validation == "candidate":
            updated_validation = "validated"

        updated_pitfalls = list(existing.get("pitfalls") or [])
        if what_failed:
            updated_pitfalls.append(what_failed)
        if changed_outcome and outcome_status != "success":
            updated_pitfalls.append(f"Outcome changed by: {changed_outcome}")

        updated_steps = list(existing.get("steps") or [])
        if outcome_status == "success" and actions_taken:
            for action in actions_taken:
                if action not in updated_steps:
                    updated_steps.append(action)

        event_enriched_provenance = _append_provenance_event(
            existing=existing.get("provenance") if isinstance(existing.get("provenance"), dict) else {"events": []},
            event={
                **provenance_event,
                "what_worked": what_worked,
                "what_failed": what_failed,
                "changed_outcome": changed_outcome,
            },
        )
        failure_count = _failure_count(event_enriched_provenance)
        if failure_count >= PROCEDURE_SUPERSEDE_FAILURE_THRESHOLD:
            updated_validation = "deprecated"

        material_change = _material_change_detected(
            existing=existing,
            actions_taken=actions_taken,
            what_failed=what_failed,
            changed_outcome=changed_outcome,
        )
        evidence_only = (
            match_score >= PROCEDURE_EVIDENCE_ONLY_MATCH_THRESHOLD
            and not material_change
            and not actions_taken
            and not what_failed
            and not changed_outcome
        )
        should_supersede = material_change and outcome_status in {"success", "partial_success"} and match_score >= PROCEDURE_UPDATE_MATCH_THRESHOLD

        card_id = procedure_card_upsert(
            conn,
            user_id=user_id,
            space_key=space_key,
            card_id=None if should_supersede else str(existing.get("id")),
            title=str(existing.get("title")),
            summary=str(existing.get("summary")),
            trigger_conditions=list(existing.get("when_to_apply") or []),
            scope=existing.get("scope") or {"type": "global", "id": None},
            steps=updated_steps,
            tool_requirements=list(existing.get("tool_requirements") or []),
            pitfalls=updated_pitfalls,
            verification_checks=list(existing.get("verification_checks") or []),
            confidence=updated_confidence,
            validation_status=updated_validation,
            task_types=list(existing.get("task_types") or ([task_type] if task_type else [])),
            provenance=event_enriched_provenance,
            body="\n".join(updated_steps),
            supersedes_card_id=str(existing.get("id")) if should_supersede else None,
            dedupe_by_fingerprint=False,
            evidence_refs=evidence_refs or None,
        )
        action = "updated_existing_procedure"
        if evidence_only:
            action = "attached_evidence_existing_procedure"
        if should_supersede:
            action = "superseded_existing_procedure"
        if failure_count >= PROCEDURE_SUPERSEDE_FAILURE_THRESHOLD:
            action = "invalidated_procedure_after_failures"
        out = {
            "action": action,
            "procedure_card_id": card_id,
            "outcome_status": outcome_status,
            "confidence": updated_confidence,
            "validation_status": updated_validation,
            "reason": f"match_score={match_score:.2f}",
            "evidence_count": len(evidence_refs),
        }
        if evidence_warnings:
            out["warnings"] = evidence_warnings
            out["warning_codes"] = [item["code"] for item in evidence_warnings]
        return out

    if not reusable and outcome_status == "failure":
        out = {
            "action": "ignored_failure_non_reusable",
            "reason": "failure_without_reusable_pattern",
            "procedure_card_id": None,
            "outcome_status": outcome_status,
        }
        if evidence_warnings:
            out["warnings"] = evidence_warnings
            out["warning_codes"] = [item["code"] for item in evidence_warnings]
        return out

    if not nontrivial:
        out = {
            "action": "ignored_low_signal_reflection",
            "reason": "insufficient_nontrivial_signal",
            "procedure_card_id": None,
            "outcome_status": outcome_status,
        }
        if evidence_warnings:
            out["warnings"] = evidence_warnings
            out["warning_codes"] = [item["code"] for item in evidence_warnings]
        return out

    if not actions_taken and what_worked:
        actions_taken = [what_worked]
    if not actions_taken:
        actions_taken = ["Review previous successful run and apply conservative defaults."]

    title = task_label or "Reusable procedure candidate"
    summary_parts = [
        f"Outcome: {outcome_status}.",
        what_worked or changed_outcome or context_summary or "Derived from reflected task outcome.",
    ]
    new_confidence = {
        "success": 0.72,
        "partial_success": 0.58,
        "failure": 0.35,
    }[outcome_status]
    validation = "candidate" if outcome_status != "failure" else "needs_review"

    card_id = procedure_card_upsert(
        conn,
        user_id=user_id,
        space_key=space_key,
        title=title,
        summary=" ".join(part for part in summary_parts if part),
        trigger_conditions=[context_summary or task_label or "similar task context"],
        scope={"type": "project", "id": None},
        steps=actions_taken,
        tool_requirements=tool_requirements,
        pitfalls=[item for item in [what_failed, changed_outcome] if item],
        verification_checks=_normalize_text_list(reflection.get("verification_checks")),
        confidence=new_confidence,
        validation_status=validation,
        task_types=[task_type] if task_type else None,
        provenance={"events": [{**provenance_event, "what_worked": what_worked, "what_failed": what_failed}]},
        body="\n".join(actions_taken),
        dedupe_by_fingerprint=True,
        evidence_refs=evidence_refs or None,
    )
    out = {
        "action": "created_new_procedure",
        "procedure_card_id": card_id,
        "outcome_status": outcome_status,
        "confidence": new_confidence,
        "validation_status": validation,
        "evidence_count": len(evidence_refs),
    }
    if evidence_warnings:
        out["warnings"] = evidence_warnings
        out["warning_codes"] = [item["code"] for item in evidence_warnings]
    return out

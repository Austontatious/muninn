from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from .cards import card_upsert, cards_recent

AdaptationMemoryType = Literal[
    "preference.direct",
    "preference.inferred",
    "override.scoped",
    "correction",
    "outcome",
]
AdaptationPersistence = Literal["durable", "one_off", "session_only"]
AdaptationView = Literal[
    "all",
    "durable_preferences",
    "recent_overrides",
    "corrections",
    "outcomes",
    "prompt_state",
]

ADAPTATION_MEMORY_TYPES: tuple[AdaptationMemoryType, ...] = (
    "preference.direct",
    "preference.inferred",
    "override.scoped",
    "correction",
    "outcome",
)
ADAPTATION_PERSISTENCE_VALUES: tuple[AdaptationPersistence, ...] = ("durable", "one_off", "session_only")
ADAPTATION_VIEWS: tuple[AdaptationView, ...] = (
    "all",
    "durable_preferences",
    "recent_overrides",
    "corrections",
    "outcomes",
    "prompt_state",
)
ADAPTATION_KIND_PREFIX = "adaptation."
ADAPTATION_KINDS: tuple[str, ...] = tuple(
    f"{ADAPTATION_KIND_PREFIX}{memory_type}" for memory_type in ADAPTATION_MEMORY_TYPES
)

# Recommended taxonomy for adaptation cards. These are conventions, not strict policy.
ADAPTATION_TAG_HINTS: tuple[str, ...] = (
    "adaptation",
    "preference.direct",
    "preference.inferred",
    "override.scoped",
    "correction",
    "outcome",
    "voice",
    "tone",
    "topic",
    "business_goal",
    "cta_tolerance",
    "humor",
    "polish",
    "cadence",
    "budget_preference",
    "social",
    "video",
    "campaign",
    "one_off",
    "durable_candidate",
    "session_only",
)

_MEMORY_TYPE_SET = set(ADAPTATION_MEMORY_TYPES)
_PERSISTENCE_SET = set(ADAPTATION_PERSISTENCE_VALUES)
_VIEW_SET = set(ADAPTATION_VIEWS)
_KIND_TO_MEMORY_TYPE = {
    f"{ADAPTATION_KIND_PREFIX}{memory_type}": memory_type for memory_type in ADAPTATION_MEMORY_TYPES
}

_VIEW_DEFAULTS: dict[AdaptationView, dict[str, Any]] = {
    "all": {},
    "durable_preferences": {
        "memory_types": ["preference.direct", "preference.inferred"],
        "persistence": ["durable"],
    },
    "recent_overrides": {
        "memory_types": ["override.scoped"],
        "persistence": ["one_off", "session_only"],
        "max_age_days": 14,
    },
    "corrections": {
        "memory_types": ["correction"],
    },
    "outcomes": {
        "memory_types": ["outcome"],
    },
    "prompt_state": {},
}


def _normalize_tag_names(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        name = str(raw).strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _normalize_text_list(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    out = _normalize_tag_names(values)
    return out or None


def _normalize_memory_type(value: str) -> AdaptationMemoryType:
    normalized = str(value or "").strip().lower()
    if normalized not in _MEMORY_TYPE_SET:
        allowed = ",".join(ADAPTATION_MEMORY_TYPES)
        raise ValueError(f"invalid_adaptation_memory_type:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_view(value: str | None) -> AdaptationView:
    normalized = str(value or "all").strip().lower()
    if normalized not in _VIEW_SET:
        allowed = ",".join(ADAPTATION_VIEWS)
        raise ValueError(f"invalid_adaptation_view:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_persistence(value: str | None) -> AdaptationPersistence:
    normalized = str(value or "durable").strip().lower()
    if normalized not in _PERSISTENCE_SET:
        allowed = ",".join(ADAPTATION_PERSISTENCE_VALUES)
        raise ValueError(f"invalid_adaptation_persistence:{normalized}:allowed={allowed}")
    return normalized  # type: ignore[return-value]


def _normalize_persistence_list(values: list[str] | None) -> list[AdaptationPersistence] | None:
    if values is None:
        return None
    out: list[AdaptationPersistence] = []
    seen: set[str] = set()
    for raw in values:
        normalized = _normalize_persistence(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out or None


def _normalize_memory_type_list(values: list[str] | None) -> list[AdaptationMemoryType] | None:
    if values is None:
        return None
    out: list[AdaptationMemoryType] = []
    seen: set[str] = set()
    for raw in values:
        normalized = _normalize_memory_type(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out or None


def _coerce_confidence(value: Any, *, fallback: float | None = None) -> float | None:
    if value is None:
        return fallback
    try:
        score = float(value)
    except (TypeError, ValueError):
        return fallback
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _parse_sqlite_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    if "T" not in normalized and " " in normalized:
        normalized = normalized.replace(" ", "T")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
        raise ValueError("invalid_adaptation_scope")

    scope_type = str(raw_type or "global").strip().lower() or "global"
    scope_id = str(raw_id or "").strip() or None
    return {"type": scope_type, "id": scope_id}


def _memory_type_from_kind(kind: Any) -> AdaptationMemoryType | None:
    return _KIND_TO_MEMORY_TYPE.get(str(kind or "").strip().lower())  # type: ignore[return-value]


def _build_adaptation_tags(
    *,
    memory_type: AdaptationMemoryType,
    category: str | None,
    persistence: AdaptationPersistence,
    scope_type: str,
    tags: list[str] | None,
    workflow_tags: list[str] | None,
) -> list[str]:
    persistence_tag = {
        "durable": "durable_candidate",
        "one_off": "one_off",
        "session_only": "session_only",
    }[persistence]
    out = [
        "adaptation",
        memory_type,
        persistence_tag,
        scope_type,
    ]
    if category:
        out.append(category)
    out.extend(_normalize_tag_names(tags))
    out.extend(_normalize_tag_names(workflow_tags))
    return _normalize_tag_names(out)


def adaptation_card_upsert(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    memory_type: str,
    subject_id: str,
    title: str,
    summary: str,
    body: str,
    category: str | None = None,
    scope: dict[str, Any] | str | None = None,
    persistence: str = "durable",
    source_type: str = "direct_feedback",
    confidence: float | None = None,
    tags: list[str] | None = None,
    workflow_tags: list[str] | None = None,
    session_id: str | None = None,
    provenance: dict[str, Any] | None = None,
    context_json: dict[str, Any] | None = None,
    status: str = "active",
    salience: float = 0.5,
    created_by_client_name: str | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
    card_id: str | None = None,
    dedupe_by_fingerprint: bool = True,
    commit: bool = True,
) -> str:
    normalized_memory_type = _normalize_memory_type(memory_type)
    normalized_subject = str(subject_id or "").strip().lower()
    if not normalized_subject:
        raise ValueError("invalid_adaptation_subject_id")
    normalized_persistence = _normalize_persistence(persistence)
    normalized_scope = _normalize_scope(scope)
    normalized_category = str(category or "").strip().lower() or None
    normalized_source_type = str(source_type or "").strip().lower() or "unspecified"
    normalized_session_id = str(session_id or "").strip() or None
    normalized_confidence = _coerce_confidence(confidence)

    merged_context: dict[str, Any] = {}
    if isinstance(context_json, dict):
        merged_context.update(context_json)
    merged_context["adaptation"] = {
        "schema_version": 1,
        "memory_type": normalized_memory_type,
        "subject_id": normalized_subject,
        "category": normalized_category,
        "scope": normalized_scope,
        "persistence": normalized_persistence,
        "source_type": normalized_source_type,
        "confidence": normalized_confidence,
        "session_id": normalized_session_id,
        "workflow_tags": _normalize_tag_names(workflow_tags),
        "provenance": provenance if isinstance(provenance, dict) else None,
    }

    kind = f"{ADAPTATION_KIND_PREFIX}{normalized_memory_type}"
    merged_tags = _build_adaptation_tags(
        memory_type=normalized_memory_type,
        category=normalized_category,
        persistence=normalized_persistence,
        scope_type=normalized_scope["type"] or "global",
        tags=tags,
        workflow_tags=workflow_tags,
    )

    return card_upsert(
        conn,
        user_id=user_id,
        space_key=space_key,
        kind=kind,
        title=title,
        summary=summary,
        body=body,
        status=status,
        salience=salience,
        tags=merged_tags,
        created_by_client_name=created_by_client_name,
        source_confidence=normalized_confidence,
        context_json=merged_context,
        card_id=card_id,
        evidence_refs=evidence_refs,
        dedupe_by_fingerprint=dedupe_by_fingerprint,
        commit=commit,
    )


def _extract_adaptation(row: dict[str, Any]) -> dict[str, Any] | None:
    raw_context = row.get("context_json")
    context: dict[str, Any] = {}
    if isinstance(raw_context, str) and raw_context.strip():
        try:
            loaded = json.loads(raw_context)
            if isinstance(loaded, dict):
                context = loaded
        except json.JSONDecodeError:
            context = {}
    elif isinstance(raw_context, dict):
        context = raw_context

    raw_adaptation = context.get("adaptation")
    adaptation: dict[str, Any] = raw_adaptation if isinstance(raw_adaptation, dict) else {}
    memory_type_raw = adaptation.get("memory_type")
    if memory_type_raw:
        try:
            memory_type = _normalize_memory_type(str(memory_type_raw))
        except ValueError:
            return None
    else:
        memory_type = _memory_type_from_kind(row.get("kind"))
        if memory_type is None:
            return None

    subject_id = str(adaptation.get("subject_id") or "").strip().lower() or None
    category = str(adaptation.get("category") or "").strip().lower() or None
    scope = _normalize_scope(adaptation.get("scope"))
    persistence = _normalize_persistence(adaptation.get("persistence"))
    source_type = str(adaptation.get("source_type") or "").strip().lower() or "unspecified"
    session_id = str(adaptation.get("session_id") or "").strip() or None
    confidence = _coerce_confidence(
        adaptation.get("confidence"),
        fallback=_coerce_confidence(row.get("source_confidence")),
    )
    workflow_tags = _normalize_tag_names(adaptation.get("workflow_tags"))
    provenance = adaptation.get("provenance") if isinstance(adaptation.get("provenance"), dict) else None

    return {
        "memory_type": memory_type,
        "subject_id": subject_id,
        "category": category,
        "scope": scope,
        "persistence": persistence,
        "source_type": source_type,
        "confidence": confidence,
        "session_id": session_id,
        "workflow_tags": workflow_tags,
        "provenance": provenance,
    }


def _resolve_effective_filters(
    *,
    view: AdaptationView,
    memory_types: list[str] | None,
    persistence: list[str] | None,
    max_age_days: int | None,
) -> tuple[list[AdaptationMemoryType], list[AdaptationPersistence] | None, int | None]:
    defaults = _VIEW_DEFAULTS[view]
    effective_memory_types = _normalize_memory_type_list(memory_types)
    if effective_memory_types is None:
        effective_memory_types = _normalize_memory_type_list(defaults.get("memory_types"))
    if effective_memory_types is None:
        effective_memory_types = list(ADAPTATION_MEMORY_TYPES)

    effective_persistence = _normalize_persistence_list(persistence)
    if effective_persistence is None:
        effective_persistence = _normalize_persistence_list(defaults.get("persistence"))

    effective_max_age_days = max_age_days
    if effective_max_age_days is None:
        default_age = defaults.get("max_age_days")
        if isinstance(default_age, int):
            effective_max_age_days = default_age
    if effective_max_age_days is not None:
        effective_max_age_days = max(1, int(effective_max_age_days))

    return effective_memory_types, effective_persistence, effective_max_age_days


def _passes_recency(created_at: Any, updated_at: Any, max_age_days: int | None) -> bool:
    if max_age_days is None:
        return True
    # Recency is based on signal capture time; fall back to updated_at for back-compat rows.
    reference_ts = _parse_sqlite_ts(created_at) or _parse_sqlite_ts(updated_at)
    if reference_ts is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    return reference_ts >= cutoff


def _normalize_adaptation_row(row: dict[str, Any], adaptation: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "status": str(row.get("status", "")),
        "salience": float(row.get("salience", 0.0) or 0.0),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "body": row.get("body"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "tags": _normalize_tag_names(row.get("tags")),
        "created_by_client_name": row.get("created_by_client_name"),
        "adaptation": adaptation,
    }


def build_prompt_state_summary(cards: list[dict[str, Any]], *, per_bucket_limit: int = 3) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    def _entry(card: dict[str, Any]) -> dict[str, Any]:
        adaptation = card.get("adaptation") or {}
        return {
            "id": card.get("id"),
            "summary": card.get("summary"),
            "updated_at": card.get("updated_at"),
            "memory_type": adaptation.get("memory_type"),
            "persistence": adaptation.get("persistence"),
            "scope": adaptation.get("scope"),
            "tags": card.get("tags", []),
        }

    for card in cards:
        adaptation = card.get("adaptation") or {}
        category = str(adaptation.get("category") or "uncategorized")
        bucket = grouped.setdefault(
            category,
            {
                "category": category,
                "durable_preferences": [],
                "recent_overrides": [],
                "corrections": [],
                "outcomes": [],
            },
        )
        memory_type = adaptation.get("memory_type")
        persistence = adaptation.get("persistence")
        if memory_type in {"preference.direct", "preference.inferred"} and persistence == "durable":
            target = bucket["durable_preferences"]
        elif memory_type == "override.scoped":
            target = bucket["recent_overrides"]
        elif memory_type == "correction":
            target = bucket["corrections"]
        elif memory_type == "outcome":
            target = bucket["outcomes"]
        else:
            continue
        if len(target) < max(1, int(per_bucket_limit)):
            target.append(_entry(card))

    return [grouped[key] for key in sorted(grouped.keys())]


def query_adaptation_cards(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    subject_id: str | None = None,
    view: str = "all",
    categories: list[str] | None = None,
    memory_types: list[str] | None = None,
    persistence: list[str] | None = None,
    scope_types: list[str] | None = None,
    scope_id: str | None = None,
    source_types: list[str] | None = None,
    session_id: str | None = None,
    tags: list[str] | None = None,
    max_age_days: int | None = None,
    status: str = "active",
    limit: int = 20,
    include_body: bool = False,
) -> dict[str, Any]:
    normalized_view = _normalize_view(view)
    effective_memory_types, effective_persistence, effective_max_age_days = _resolve_effective_filters(
        view=normalized_view,
        memory_types=memory_types,
        persistence=persistence,
        max_age_days=max_age_days,
    )
    normalized_subject = str(subject_id or "").strip().lower() or None
    normalized_categories = _normalize_text_list(categories)
    normalized_scope_types = _normalize_text_list(scope_types)
    normalized_scope_id = str(scope_id or "").strip() or None
    normalized_source_types = _normalize_text_list(source_types)
    normalized_session_id = str(session_id or "").strip() or None
    normalized_tags = _normalize_tag_names(tags)
    max_results = max(1, int(limit))
    scan_limit = min(500, max(max_results, max_results * 5))

    rows = cards_recent(
        conn,
        user_id=user_id,
        space_key=space_key,
        kinds=[f"{ADAPTATION_KIND_PREFIX}{memory_type}" for memory_type in effective_memory_types],
        status=status,
        tags=normalized_tags or None,
        limit=scan_limit,
        include_body=include_body,
        include_context=True,
    )

    cards: list[dict[str, Any]] = []
    by_memory_type: dict[str, int] = {memory_type: 0 for memory_type in ADAPTATION_MEMORY_TYPES}
    by_persistence: dict[str, int] = {key: 0 for key in ADAPTATION_PERSISTENCE_VALUES}

    for row in rows:
        adaptation = _extract_adaptation(row)
        if adaptation is None:
            continue
        memory_type = adaptation["memory_type"]
        if memory_type not in effective_memory_types:
            continue
        if normalized_subject and adaptation.get("subject_id") != normalized_subject:
            continue
        if normalized_categories and adaptation.get("category") not in normalized_categories:
            continue
        if effective_persistence and adaptation.get("persistence") not in effective_persistence:
            continue
        scope = adaptation.get("scope") or {}
        if normalized_scope_types and str(scope.get("type") or "") not in normalized_scope_types:
            continue
        if normalized_scope_id and str(scope.get("id") or "") != normalized_scope_id:
            continue
        if normalized_source_types and adaptation.get("source_type") not in normalized_source_types:
            continue
        if normalized_session_id and adaptation.get("session_id") != normalized_session_id:
            continue
        if not _passes_recency(row.get("created_at"), row.get("updated_at"), effective_max_age_days):
            continue

        normalized_row = _normalize_adaptation_row(row, adaptation)
        if not include_body:
            normalized_row.pop("body", None)
        cards.append(normalized_row)
        by_memory_type[memory_type] += 1
        by_persistence[adaptation["persistence"]] += 1
        if len(cards) >= max_results:
            break

    return {
        "cards": cards,
        "counts": {
            "total": len(cards),
            "by_memory_type": by_memory_type,
            "by_persistence": by_persistence,
        },
        "filters": {
            "view": normalized_view,
            "subject_id": normalized_subject,
            "memory_types": list(effective_memory_types),
            "categories": normalized_categories or [],
            "persistence": list(effective_persistence or []),
            "scope_types": normalized_scope_types or [],
            "scope_id": normalized_scope_id,
            "source_types": normalized_source_types or [],
            "session_id": normalized_session_id,
            "tags": normalized_tags,
            "max_age_days": effective_max_age_days,
            "status": status,
            "limit": max_results,
        },
        "prompt_state": build_prompt_state_summary(cards),
    }

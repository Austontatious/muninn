from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from .cards import cards_recent, cards_search
from .policy import query_policy_cards
from .spaces import resolve_space_lookup_keys


def _normalize_tag_names(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in tags:
        name = " ".join(str(raw or "").strip().lower().split())
        if not name or name in seen:
            continue
        seen.add(name)
        normalized.append(name)
    return normalized


def _normalize_tokens(value: str | None) -> set[str]:
    text = " ".join(str(value or "").strip().lower().split())
    if not text:
        return set()
    return {token for token in text.split() if token}


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


def _recency_bonus(value: Any) -> float:
    parsed = _parse_ts(value)
    if parsed is None:
        return 0.0
    age_days = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0)
    return max(0.0, 0.18 - min(0.18, age_days * 0.012))


def _kind_bonus(kind: str) -> float:
    normalized = " ".join(str(kind or "").strip().lower().split())
    if normalized in {"constraint", "decision"}:
        return 0.12
    if normalized in {"runbook", "interface"}:
        return 0.08
    return 0.03


def _lexical_bonus(query: str, row: dict[str, Any]) -> float:
    tokens = _normalize_tokens(query)
    if not tokens:
        return 0.0
    haystack = " ".join(
        filter(
            None,
            [
                " ".join(str(row.get("title") or "").strip().lower().split()),
                " ".join(str(row.get("summary") or "").strip().lower().split()),
                " ".join(str(row.get("body") or "").strip().lower().split()),
                " ".join(_normalize_tag_names(row.get("tags"))),
            ],
        )
    )
    if not haystack:
        return 0.0
    matched = sum(1 for token in tokens if token in haystack)
    return min(0.35, 0.07 * matched)


def _normalize_project_card(row: dict[str, Any], *, stage: str, score: float) -> dict[str, Any]:
    normalized = {
        "id": str(row.get("id", "")),
        "space_key": str(row.get("space_key", "")),
        "kind": str(row.get("kind", "")),
        "status": str(row.get("status", "")),
        "title": str(row.get("title", "")),
        "summary": str(row.get("summary", "")),
        "body": row.get("body"),
        "updated_at": row.get("updated_at"),
        "tags": row.get("tags", []),
        "evidence_count": int(row.get("evidence_count") or 0),
        "has_evidence": bool(row.get("has_evidence")),
        "score": round(score, 6),
        "stage": stage,
    }
    return normalized


def _stage_zero_reason(stage: str) -> str:
    reasons = {
        "strict_search": "no_lexical_match_in_canonical_space",
        "recent_strict": "no_recent_cards_in_canonical_space",
        "soft_search": "no_relaxed_search_match_in_canonical_space",
        "alias_search": "no_alias_space_match",
        "recent_evidence": "no_recent_evidence_backed_cards_in_project_scope",
        "global_search": "no_global_fallback_match",
    }
    return reasons.get(stage, "no_stage_matches")


def _stage_rows(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    stage: str,
    space_keys: list[str],
    query: str,
    kinds: list[str] | None,
    status: str,
    tags: list[str] | None,
    limit: int,
    include_body: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    for space_key in space_keys:
        if stage in {"strict_search", "soft_search", "alias_search", "global_search"}:
            stage_rows = cards_search(
                conn,
                user_id=user_id,
                space_key=space_key,
                query=query,
                kinds=kinds,
                status=status,
                tags=tags,
                limit=limit,
                include_body=include_body,
                include_context=True,
            )
        else:
            stage_rows = cards_recent(
                conn,
                user_id=user_id,
                space_key=space_key,
                kinds=kinds,
                status=status,
                tags=tags,
                limit=limit,
                include_body=include_body,
                include_context=True,
            )
            if stage == "recent_evidence":
                stage_rows = [row for row in stage_rows if bool(row.get("has_evidence"))]
        rows.extend(stage_rows)
        diagnostics.append({"stage": stage, "space_key": space_key, "results": len(stage_rows)})
    return rows, diagnostics


def rehydrate_bundle(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
    query: str,
    kinds: list[str] | None = None,
    status: str = "active",
    tags: list[str] | None = None,
    limit: int = 12,
    include_body: bool = False,
    include_policy: bool = True,
    scope: str = "soft",
    tool_name: str | None = None,
    task_type: str | None = None,
) -> dict[str, Any]:
    max_results = max(1, int(limit))
    canonical_lookup = resolve_space_lookup_keys(conn, user_id=user_id, space_key=space_key)
    canonical_key = canonical_lookup[0]
    alias_keys = [key for key in canonical_lookup[1:] if key != "global"]
    stage_plan: list[dict[str, Any]] = [
        {
            "stage": "strict_search",
            "space_keys": [canonical_key],
            "kinds": kinds,
            "tags": tags,
            "skip_reason": None,
        },
        {
            "stage": "recent_strict",
            "space_keys": [canonical_key],
            "kinds": kinds,
            "tags": tags,
            "skip_reason": None,
        },
        {
            "stage": "soft_search",
            "space_keys": [canonical_key],
            "kinds": None,
            "tags": None,
            "skip_reason": None,
        },
        {
            "stage": "alias_search",
            "space_keys": alias_keys,
            "kinds": None,
            "tags": None,
            "skip_reason": None if alias_keys else "no_alias_space_keys",
        },
        {
            "stage": "recent_evidence",
            "space_keys": [canonical_key, *alias_keys],
            "kinds": kinds,
            "tags": tags,
            "skip_reason": None,
        },
        {
            "stage": "global_search",
            "space_keys": ["global"] if scope == "soft" else [],
            "kinds": None,
            "tags": None,
            "skip_reason": None if scope == "soft" else "soft_scope_disabled",
        },
    ]

    stage_weights = {
        "strict_search": 1.0,
        "recent_strict": 0.72,
        "soft_search": 0.58,
        "alias_search": 0.5,
        "recent_evidence": 0.45,
        "global_search": 0.28,
    }

    ranked: dict[str, dict[str, Any]] = {}
    stage_reports: list[dict[str, Any]] = []
    for stage_config in stage_plan:
        stage_name = str(stage_config["stage"])
        stage_space_keys = [str(key) for key in (stage_config.get("space_keys") or [])]
        stage_kinds = stage_config.get("kinds")
        stage_tags = stage_config.get("tags")
        skip_reason = stage_config.get("skip_reason")
        if skip_reason:
            stage_reports.append(
                {
                    "stage": stage_name,
                    "space_key": canonical_key,
                    "space_keys": stage_space_keys,
                    "results": 0,
                    "attempted": False,
                    "skipped": True,
                    "skip_reason": skip_reason,
                    "zero_reason": None,
                    "per_space_results": [],
                }
            )
            continue
        rows, diagnostics = _stage_rows(
            conn,
            user_id=user_id,
            stage=stage_name,
            space_keys=stage_space_keys,
            query=query,
            kinds=stage_kinds,
            status=status,
            tags=stage_tags,
            limit=max_results * 3,
            include_body=include_body,
        )
        total_results = sum(int(item.get("results") or 0) for item in diagnostics)
        stage_reports.append(
            {
                "stage": stage_name,
                "space_key": canonical_key,
                "space_keys": stage_space_keys,
                "results": total_results,
                "attempted": True,
                "skipped": False,
                "skip_reason": None,
                "zero_reason": _stage_zero_reason(stage_name) if total_results == 0 else None,
                "per_space_results": diagnostics,
            }
        )
        for row in rows:
            card_id = str(row.get("id", ""))
            if not card_id:
                continue
            score = (
                stage_weights.get(stage_name, 0.25)
                + _kind_bonus(str(row.get("kind", "")))
                + _lexical_bonus(query, row)
                + _recency_bonus(row.get("updated_at"))
                + min(0.18, 0.06 * int(row.get("evidence_count") or 0))
            )
            if str(row.get("space_key")) == canonical_key:
                score += 0.12
            elif str(row.get("space_key")) in alias_keys:
                score += 0.07
            normalized = _normalize_project_card(row, stage=stage_name, score=score)
            previous = ranked.get(card_id)
            if previous is None or float(normalized["score"]) > float(previous["score"]):
                ranked[card_id] = normalized

    project_cards = sorted(
        ranked.values(),
        key=lambda row: (-float(row["score"]), -int(row["evidence_count"]), str(row.get("updated_at") or "")),
    )[:max_results]

    policy_payload = {"cards": [], "filters": {}}
    if include_policy:
        policy_payload = query_policy_cards(
            conn,
            user_id=user_id,
            space_key=canonical_key,
            query=query,
            tool_name=tool_name,
            task_type=task_type,
            include_global=(scope == "soft"),
            limit=min(6, max(3, max_results // 2)),
            include_body=include_body,
        )

    constraints = [card for card in project_cards if card["kind"] == "constraint"]
    facts = [card for card in project_cards if card["kind"] != "constraint"]
    evidence_cards = [card for card in project_cards if card["has_evidence"]]
    policy_cards = list(policy_payload.get("cards", []))
    preferences = [
        card
        for card in policy_cards
        if card.get("kind") in {"policy.preference", "tooling.preference"}
    ]
    lessons = [
        card
        for card in policy_cards
        if card.get("kind") not in {"policy.preference", "tooling.preference"}
    ]

    return {
        "space": {
            "canonical_key": canonical_key,
            "lookup_keys": canonical_lookup,
            "scope": scope,
        },
        "query": query,
        "stages": stage_reports,
        "project_cards": project_cards,
        "policy_cards": policy_cards,
        "policy_diagnostics": policy_payload.get("diagnostics") or {},
        "summary": {
            "project_cards": len(project_cards),
            "policy_cards": len(policy_cards),
            "rehydration_empty": not project_cards and not policy_cards,
        },
        "bundle": {
            "facts": facts,
            "constraints": constraints,
            "evidence": evidence_cards,
            "lessons": lessons,
            "preferences": preferences,
        },
    }

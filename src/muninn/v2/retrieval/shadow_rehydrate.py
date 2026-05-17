from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..core.models import EvidenceRef, MemoryCard, utc_now
from ..indexes import DerivedIndexProvider
from .hybrid_recall import hybrid_recall
from .lexical_recall import lexical_recall
from .vector_recall import recall_with_fallback


RETRIEVAL_MODES = {"hybrid", "lexical", "vector"}
SHADOW_PREVIEW_SCHEMA_VERSION = "muninn.v2.shadow_rehydrate_preview.v1"


class ShadowPreviewError(RuntimeError):
    """Raised when a shadow preview cannot be produced safely."""


@dataclass(frozen=True)
class ShadowPreviewOptions:
    v2_db: str
    query: str
    limit: int = 12
    primary_limit: int = 3
    recent_limit: int = 9
    retrieval_mode: str = "hybrid"
    space_key: str | None = None
    project_path: str | None = None
    include_evidence: bool = False
    include_explanations: bool = False
    max_chars: int | None = None
    recent_supplement: bool = True
    strict: bool = False


def build_shadow_rehydrate_preview(
    records: Sequence[MemoryCard],
    *,
    provider: DerivedIndexProvider | None = None,
    options: ShadowPreviewOptions,
) -> dict[str, Any]:
    query = " ".join(str(options.query or "").split())
    if not query:
        raise ShadowPreviewError("query_required")
    mode = _retrieval_mode(options.retrieval_mode)
    limit = _positive_int(options.limit, "limit")
    primary_limit = min(_positive_int(options.primary_limit, "primary_limit"), limit)
    recent_limit = _positive_int(options.recent_limit, "recent_limit")
    max_chars = _max_chars(options.max_chars)

    active = [card for card in records if str(card.status or "active") == "active"]
    if not active:
        raise ShadowPreviewError("shadow_preview_no_active_v2_cards")

    inferred_space_key = _resolve_space_key(active, options.space_key, strict=options.strict)
    filtered = _filter_cards(active, space_key=inferred_space_key, project_path=options.project_path)
    if not filtered:
        if options.strict:
            raise ShadowPreviewError("shadow_preview_no_cards_after_filters")
        filtered = active

    retrieval = _recall(
        filtered,
        query,
        provider=provider,
        limit=max(limit, primary_limit),
        scope_key=inferred_space_key,
        retrieval_mode=mode,
    )
    cards_by_id = {card.id: card for card in filtered}
    primary_candidates = _primary_entries(
        retrieval.get("results", []),
        cards_by_id=cards_by_id,
        include_evidence=options.include_evidence,
        include_explanations=options.include_explanations,
        limit=primary_limit,
    )
    primary_ids = {entry["id"] for entry in primary_candidates}
    supplement_candidates: list[dict[str, Any]] = []
    duplicate_supplements = 0
    if options.recent_supplement and len(primary_candidates) < limit:
        recent_cards = _recent_cards(filtered, exclude_ids=primary_ids)
        duplicate_supplements = len(filtered) - len(primary_ids) - len(recent_cards)
        supplement_candidates = [
            _supplement_entry(
                card,
                include_evidence=options.include_evidence,
                include_explanations=options.include_explanations,
            )
            for card in recent_cards[: min(recent_limit, limit - len(primary_candidates))]
        ]

    budgeted = _apply_budget(
        primary_candidates,
        supplement_candidates,
        max_chars=max_chars,
        limit=limit,
    )
    primary_results = budgeted["primary_results"]
    recent_supplements = budgeted["recent_supplements"]
    context_gaps = _context_gaps(
        retrieval=retrieval,
        filtered_cards=filtered,
        primary_results=primary_results,
        recent_supplements=recent_supplements,
        max_chars=max_chars,
        omitted_for_budget=budgeted["omitted_for_budget"],
        recent_supplement_enabled=options.recent_supplement,
    )
    briefing = _agent_briefing(primary_results, recent_supplements, context_gaps)
    counts = {
        "primary": len(primary_results),
        "supplements": len(recent_supplements),
        "total": len(primary_results) + len(recent_supplements),
        "duplicates_removed": int(duplicate_supplements),
        "omitted_for_budget": int(budgeted["omitted_for_budget"]),
        "omitted_for_limit": int(budgeted["omitted_for_limit"]),
        "candidate_cards": len(filtered),
    }
    return {
        "schema_version": SHADOW_PREVIEW_SCHEMA_VERSION,
        "record_type": "muninn_v2_shadow_rehydrate_preview",
        "generated_at": utc_now(),
        "query": query,
        "source": {
            "v2_db": str(options.v2_db),
            "space_key": inferred_space_key,
            "project_path": options.project_path,
            "active_scope_keys": sorted({str(card.scope_key) for card in active if card.scope_key}),
        },
        "command_args": {
            "limit": limit,
            "primary_limit": primary_limit,
            "recent_limit": recent_limit,
            "retrieval_mode": mode,
            "include_evidence": bool(options.include_evidence),
            "include_explanations": bool(options.include_explanations),
            "max_chars": max_chars,
            "recent_supplement": bool(options.recent_supplement),
            "strict": bool(options.strict),
        },
        "composition": {
            "strategy": (
                "primary_retrieval_only"
                if not options.recent_supplement
                else "hybrid_primary_plus_recent_supplement"
            ),
            "retrieval_mode": mode,
            "limit": limit,
            "primary_limit": primary_limit,
            "recent_limit": recent_limit,
            "max_chars": max_chars,
            "stage_a": "primary_retrieval",
            "stage_b": "recent_in_scope_supplement" if options.recent_supplement else "disabled",
            "stage_c": "evidence_attachment" if options.include_evidence else "evidence_counts_only",
            "stage_d": "budget_enforced" if max_chars is not None else "limit_only",
            "stage_e": "deterministic_agent_briefing",
        },
        "retrieval": {
            "backend": retrieval.get("backend"),
            "fallback_used": bool(retrieval.get("fallback_used")),
            "status": retrieval.get("status"),
            "query_profile": retrieval.get("query_profile"),
        },
        "counts": counts,
        "primary_results": primary_results,
        "recent_supplements": recent_supplements,
        "context_gaps": context_gaps,
        "agent_briefing": briefing,
    }


def write_shadow_rehydrate_preview_reports(
    report: dict[str, Any],
    out_dir: str | Path,
    *,
    json_report: str | Path | None = None,
    md_report: str | Path | None = None,
) -> dict[str, str]:
    directory = Path(out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    json_path = Path(json_report).expanduser() if json_report else directory / "shadow_rehydrate_preview.json"
    md_path = Path(md_report).expanduser() if md_report else directory / "shadow_rehydrate_preview.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_shadow_rehydrate_preview_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_shadow_rehydrate_preview_markdown(report: dict[str, Any]) -> str:
    source = report["source"]
    composition = report["composition"]
    counts = report["counts"]
    retrieval = report["retrieval"]
    briefing = report["agent_briefing"]
    lines = [
        "# Muninn v2 Shadow Rehydration Preview",
        "",
        "## Executive Summary",
        "",
        f"- Usable: `{str(briefing['usable']).lower()}`",
        f"- Total cards: {counts['total']} ({counts['primary']} primary, {counts['supplements']} supplements)",
        f"- Retrieval backend: `{retrieval.get('backend')}`",
        f"- Fallback used: `{str(retrieval.get('fallback_used')).lower()}`",
        "",
        "## Query / Task",
        "",
        f"`{report['query']}`",
        "",
        "## Source",
        "",
        f"- v2 DB: `{source['v2_db']}`",
        f"- Space key: `{source.get('space_key')}`",
        f"- Project path: `{source.get('project_path')}`",
        "",
        "## Composition Strategy",
        "",
        f"- Strategy: `{composition['strategy']}`",
        f"- Retrieval mode: `{composition['retrieval_mode']}`",
        f"- Limit: {composition['limit']}",
        f"- Primary limit: {composition['primary_limit']}",
        f"- Recent limit: {composition['recent_limit']}",
        f"- Max chars: `{composition.get('max_chars')}`",
        "",
        "## Primary Retrieval Matches",
        "",
    ]
    if report["primary_results"]:
        for item in report["primary_results"]:
            lines.extend(_markdown_card(item, include_score=True))
    else:
        lines.append("- none")
    lines.extend(["", "## Recent In-Scope Supplements", ""])
    if report["recent_supplements"]:
        for item in report["recent_supplements"]:
            lines.extend(_markdown_card(item, include_score=False))
    else:
        lines.append("- none")
    lines.extend(["", "## Evidence / Provenance", ""])
    evidence_count = sum(int(item.get("evidence_count", 0)) for item in _all_items(report))
    included = sum(len(item.get("evidence", [])) for item in _all_items(report))
    lines.append(f"- Evidence refs available on preview cards: {evidence_count}")
    lines.append(f"- Evidence refs included in report: {included}")
    lines.extend(["", "## Explanation Notes", ""])
    lines.append(f"- Explanations included: `{str(bool(_any_explanations(report))).lower()}`")
    lines.append(f"- Duplicates removed: {counts['duplicates_removed']}")
    lines.append(f"- Omitted for budget: {counts['omitted_for_budget']}")
    lines.append(f"- Omitted for limit: {counts['omitted_for_limit']}")
    lines.extend(["", "## Context Gaps / Uncertainty", ""])
    if report["context_gaps"]:
        lines.extend(f"- {gap}" for gap in report["context_gaps"])
    else:
        lines.append("- none reported")
    lines.extend(["", "## Suggested Agent Briefing", ""])
    if briefing["bullets"]:
        lines.extend(f"- {bullet}" for bullet in briefing["bullets"])
    else:
        lines.append("- No briefing bullets generated.")
    lines.append("")
    return "\n".join(lines)


def _recall(
    records: Sequence[MemoryCard],
    query: str,
    *,
    provider: DerivedIndexProvider | None,
    limit: int,
    scope_key: str | None,
    retrieval_mode: str,
) -> dict[str, Any]:
    if retrieval_mode == "hybrid":
        return hybrid_recall(records, query, provider=provider, limit=limit, scope_key=scope_key)
    if retrieval_mode == "lexical":
        return {
            "backend": "lexical_fallback",
            "fallback_used": True,
            "status": provider.status().to_dict() if provider is not None else None,
            "results": lexical_recall(records, query, limit=limit, scope_key=scope_key),
        }
    return recall_with_fallback(records, query, provider=provider, limit=limit, scope_key=scope_key)


def _primary_entries(
    results: Sequence[dict[str, Any]],
    *,
    cards_by_id: dict[str, MemoryCard],
    include_evidence: bool,
    include_explanations: bool,
    limit: int,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        record_id = str(result.get("record_id") or "")
        if not record_id or record_id in seen:
            continue
        card = cards_by_id.get(record_id)
        if card is None:
            continue
        seen.add(record_id)
        out.append(
            _card_entry(
                card,
                stage="primary_retrieval",
                reason="query_match",
                score=result.get("score"),
                retrieval_rank=result.get("rank"),
                explanation=(result.get("explanation") if include_explanations else None),
                include_evidence=include_evidence,
            )
        )
        if len(out) >= limit:
            break
    return out


def _supplement_entry(
    card: MemoryCard,
    *,
    include_evidence: bool,
    include_explanations: bool,
) -> dict[str, Any]:
    explanation = None
    if include_explanations:
        explanation = {
            "retrieval_path": "recent_in_scope_shadow_supplement",
            "score_semantics": "continuity supplement, not query relevance",
            "candidate_sources": ["scope_key", "status", "updated_at"],
            "matched_tokens": [],
            "score_components": {"recent_active_project_card": 1.0},
            "penalties": {},
            "vector_used": False,
        }
    return _card_entry(
        card,
        stage="recent_in_scope_supplement",
        reason="recent_in_scope_supplement",
        score=None,
        retrieval_rank=None,
        explanation=explanation,
        include_evidence=include_evidence,
    )


def _card_entry(
    card: MemoryCard,
    *,
    stage: str,
    reason: str,
    score: Any,
    retrieval_rank: Any,
    explanation: Any,
    include_evidence: bool,
) -> dict[str, Any]:
    entry = {
        "id": card.id,
        "record_id": card.id,
        "stage": stage,
        "reason": reason,
        "kind": card.kind,
        "status": card.status,
        "title": card.title,
        "summary": card.summary,
        "body_excerpt": _body_excerpt(card.body),
        "scope_key": card.scope_key,
        "updated_at": card.updated_at,
        "score": score,
        "retrieval_rank": retrieval_rank,
        "evidence_count": len(card.evidence),
        "evidence": _evidence_payload(card.evidence) if include_evidence else [],
    }
    if explanation is not None:
        entry["explanation"] = explanation
    return entry


def _apply_budget(
    primary: list[dict[str, Any]],
    supplements: list[dict[str, Any]],
    *,
    max_chars: int | None,
    limit: int,
) -> dict[str, Any]:
    selected_primary: list[dict[str, Any]] = []
    selected_supplements: list[dict[str, Any]] = []
    omitted_for_budget = 0
    used = 0
    for bucket, selected in ((primary, selected_primary), (supplements, selected_supplements)):
        for item in bucket:
            if len(selected_primary) + len(selected_supplements) >= limit:
                continue
            item_chars = _item_chars(item)
            if max_chars is not None and selected and used + item_chars > max_chars:
                omitted_for_budget += 1
                continue
            if max_chars is not None and not selected and selected_primary and used + item_chars > max_chars:
                omitted_for_budget += 1
                continue
            if max_chars is not None and not selected_primary and not selected_supplements and item_chars > max_chars:
                clipped = dict(item)
                clipped["body_excerpt"] = ""
                clipped["budget_note"] = "body omitted to keep first primary card within max_chars"
                item = clipped
                item_chars = _item_chars(item)
            if max_chars is not None and used + item_chars > max_chars and selected_primary:
                omitted_for_budget += 1
                continue
            selected.append(item)
            used += item_chars
    omitted_for_limit = max(0, len(primary) + len(supplements) - len(selected_primary) - len(selected_supplements) - omitted_for_budget)
    return {
        "primary_results": selected_primary,
        "recent_supplements": selected_supplements,
        "omitted_for_budget": omitted_for_budget,
        "omitted_for_limit": omitted_for_limit,
    }


def _recent_cards(cards: Sequence[MemoryCard], *, exclude_ids: set[str]) -> list[MemoryCard]:
    out = [card for card in cards if card.id not in exclude_ids]
    out.sort(key=lambda card: str(card.id))
    out.sort(key=lambda card: str(card.updated_at or ""), reverse=True)
    return out


def _filter_cards(
    cards: Sequence[MemoryCard],
    *,
    space_key: str | None,
    project_path: str | None,
) -> list[MemoryCard]:
    out: list[MemoryCard] = []
    wanted_project = _normalize_path(project_path) if project_path else None
    for card in cards:
        if space_key and card.scope_key != space_key:
            continue
        if wanted_project and wanted_project not in _card_project_paths(card):
            continue
        out.append(card)
    return out


def _resolve_space_key(cards: Sequence[MemoryCard], requested: str | None, *, strict: bool) -> str | None:
    value = str(requested or "").strip() or None
    if value:
        if strict and all(card.scope_key != value for card in cards):
            raise ShadowPreviewError(f"space_key_not_found:{value}")
        return value
    scope_keys = sorted({str(card.scope_key) for card in cards if card.scope_key})
    if len(scope_keys) == 1:
        return scope_keys[0]
    if strict and len(scope_keys) > 1:
        raise ShadowPreviewError("space_key_required_for_multi_space_v2_db")
    return None


def _retrieval_mode(value: str) -> str:
    mode = str(value or "hybrid").strip().lower()
    if mode not in RETRIEVAL_MODES:
        raise ShadowPreviewError(f"unsupported_retrieval_mode:{value}")
    return mode


def _positive_int(value: int, name: str) -> int:
    number = int(value)
    if number <= 0:
        raise ShadowPreviewError(f"{name}_must_be_positive")
    return number


def _max_chars(value: int | None) -> int | None:
    if value is None:
        return None
    number = int(value)
    if number <= 0:
        raise ShadowPreviewError("max_chars_must_be_positive")
    return number


def _body_excerpt(body: str, *, limit: int = 600) -> str:
    text = " ".join(str(body or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _evidence_payload(evidence: Sequence[EvidenceRef]) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "type": item.evidence_type,
            "ref": item.ref,
            "excerpt": item.excerpt,
            "created_at": item.created_at,
        }
        for item in evidence
    ]


def _item_chars(item: dict[str, Any]) -> int:
    parts = [
        item.get("title"),
        item.get("summary"),
        item.get("body_excerpt"),
        " ".join(str(ev.get("ref") or "") for ev in item.get("evidence", [])),
    ]
    return sum(len(str(part or "")) for part in parts)


def _context_gaps(
    *,
    retrieval: dict[str, Any],
    filtered_cards: Sequence[MemoryCard],
    primary_results: Sequence[dict[str, Any]],
    recent_supplements: Sequence[dict[str, Any]],
    max_chars: int | None,
    omitted_for_budget: int,
    recent_supplement_enabled: bool,
) -> list[str]:
    gaps: list[str] = []
    if not primary_results:
        gaps.append("No primary retrieval matches met the selected retrieval mode and score threshold.")
    if recent_supplement_enabled and not recent_supplements:
        gaps.append("No recent in-scope supplements were added.")
    if not filtered_cards:
        gaps.append("No active v2 cards matched the requested filters.")
    status = retrieval.get("status") if isinstance(retrieval.get("status"), dict) else None
    if status and status.get("degraded"):
        reason = ", ".join(str(item) for item in status.get("reason", []))
        gaps.append(f"Derived index backend is degraded: {reason}")
    if max_chars is not None and omitted_for_budget:
        gaps.append(f"{omitted_for_budget} candidate cards were omitted by max_chars budget.")
    return gaps


def _agent_briefing(
    primary_results: Sequence[dict[str, Any]],
    recent_supplements: Sequence[dict[str, Any]],
    context_gaps: Sequence[str],
) -> dict[str, Any]:
    bullets: list[str] = []
    for item in list(primary_results)[:5]:
        bullets.append(f"Primary match: {item['title']} - {item['summary']}")
    for item in list(recent_supplements)[:5]:
        bullets.append(f"Continuity: {item['title']} - {item['summary']}")
    usable = bool(primary_results or recent_supplements)
    if not usable:
        bullets.append("No usable shadow context was retrieved from the explicit v2 DB.")
    if context_gaps:
        bullets.append("Uncertainty: " + context_gaps[0])
    return {
        "usable": usable,
        "method": "deterministic_card_title_summary_projection",
        "bullets": bullets,
    }


def _card_project_paths(card: MemoryCard) -> set[str]:
    metadata = card.metadata if isinstance(card.metadata, dict) else {}
    values = {
        metadata.get("project_path"),
        metadata.get("project_root_path"),
        metadata.get("root_path"),
    }
    return {_normalize_path(str(value)) for value in values if value}


def _normalize_path(value: str | None) -> str:
    if not value:
        return ""
    return str(Path(value).expanduser())


def _all_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [*report.get("primary_results", []), *report.get("recent_supplements", [])]


def _any_explanations(report: dict[str, Any]) -> bool:
    return any("explanation" in item for item in _all_items(report))


def _markdown_card(item: dict[str, Any], *, include_score: bool) -> list[str]:
    score = f" score=`{item.get('score')}`" if include_score else ""
    lines = [
        f"- `{item['id']}` {item['title']}",
        f"  - stage: `{item['stage']}` kind: `{item['kind']}` updated: `{item.get('updated_at')}`{score}",
        f"  - summary: {item['summary']}",
    ]
    if item.get("body_excerpt"):
        lines.append(f"  - body excerpt: {item['body_excerpt']}")
    evidence = item.get("evidence", [])
    if evidence:
        refs = [f"`{entry.get('ref')}`" for entry in evidence[:5] if entry.get("ref")]
        if refs:
            lines.append("  - evidence: " + "; ".join(refs))
    explanation = item.get("explanation")
    if isinstance(explanation, dict):
        sources = explanation.get("candidate_sources", [])
        tokens = explanation.get("matched_tokens", [])
        lines.append(f"  - explanation: sources={sources} tokens={tokens}")
    return lines

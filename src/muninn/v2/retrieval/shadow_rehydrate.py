from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..core.models import EvidenceRef, MemoryCard, utc_now
from ..indexes import DerivedIndexProvider
from .hybrid_recall import hybrid_recall
from .lexical_recall import lexical_recall
from .scoring import card_search_text, normalize_tokens
from .vector_recall import recall_with_fallback


RETRIEVAL_MODES = {"hybrid", "lexical", "vector"}
REHYDRATE_RESPONSE_SCHEMA_NAME = "RehydrateResponseV1"
REHYDRATE_RESPONSE_CONTRACT_VERSION = "1.0.0"
REHYDRATE_RESPONSE_SCHEMA_VERSION = "muninn.v2.rehydrate_response.v1"
REHYDRATE_RESPONSE_SCHEMA_URI = "docs/contracts/muninn_v2/v1/schemas/rehydrate-response.v1.schema.json"
SUPPLEMENT_RECENT_CAP_OFFSET = 2
SUPPLEMENT_FALLBACK_CAP = 2
SUPPLEMENT_GENERIC_TOKENS = {
    "current",
    "context",
    "project",
    "repo",
    "resume",
    "state",
    "steps",
    "task",
}
SUPPLEMENT_BACKGROUND_MARKERS = (
    "background",
    "background-only",
    "contrast-only",
    "deferred automation",
    "hard-gate",
    "manual_review",
    "optimizer",
    "process artifacts",
    "revisit conditions",
    "trial",
)
SUPPLEMENT_BOUNDARY_MARKERS = (
    "boundary",
    "canonical",
    "contract",
    "entrypoint",
    "entrypoints",
    "runtime memory",
)


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


@dataclass(frozen=True)
class SupplementCandidate:
    card: MemoryCard
    reason: str
    score: float
    matched_tokens: tuple[str, ...]
    candidate_sources: tuple[str, ...]
    penalties: dict[str, float]


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
        supplement_limit = min(recent_limit, limit - len(primary_candidates))
        supplement_candidates = _supplement_entries(
            recent_cards,
            query=query,
            primary_results=primary_candidates,
            limit=supplement_limit,
            strict=options.strict,
            include_evidence=options.include_evidence,
            include_explanations=options.include_explanations,
        )

    budgeted = _apply_budget(
        primary_candidates,
        supplement_candidates,
        max_chars=max_chars,
        limit=limit,
    )
    primary_results = budgeted["primary_results"]
    recent_supplements = budgeted["recent_supplements"]
    selected_cards = [*primary_results, *recent_supplements]
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
    retrieval_provenance = _retrieval_provenance(retrieval, retrieval_mode=mode)
    budget = _budget_payload(
        limit=limit,
        primary_limit=primary_limit,
        recent_limit=recent_limit,
        max_chars=max_chars,
        selected_cards=selected_cards,
        primary_results=primary_results,
        recent_supplements=recent_supplements,
        duplicate_supplements=duplicate_supplements,
        omitted_for_budget=budgeted["omitted_for_budget"],
        omitted_for_limit=budgeted["omitted_for_limit"],
        candidate_cards=len(filtered),
    )
    generated_at = utc_now()
    return {
        "schema": {
            "name": REHYDRATE_RESPONSE_SCHEMA_NAME,
            "version": REHYDRATE_RESPONSE_CONTRACT_VERSION,
            "schema_version": REHYDRATE_RESPONSE_SCHEMA_VERSION,
            "schema_uri": REHYDRATE_RESPONSE_SCHEMA_URI,
        },
        "schema_version": REHYDRATE_RESPONSE_SCHEMA_VERSION,
        "contract_version": REHYDRATE_RESPONSE_CONTRACT_VERSION,
        "record_type": "muninn_v2_rehydrate_response",
        "response_kind": "shadow_rehydrate_preview",
        "response_id": _response_id(
            generated_at=generated_at,
            query=query,
            source_db=str(options.v2_db),
        ),
        "generated_at": generated_at,
        "request": {
            "query": {
                "text": query,
            },
            "source": {
                "v2_db": str(options.v2_db),
                "space_key": inferred_space_key,
                "project_path": options.project_path,
                "active_scope_keys": sorted({str(card.scope_key) for card in active if card.scope_key}),
            },
            "options": {
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
        "selected_memory": {
            "cards": selected_cards,
            "events": [],
            "evidence": _selected_evidence(selected_cards),
        },
        "explanations": _explanations(
            primary_results,
            recent_supplements,
            include_explanations=options.include_explanations,
        ),
        "uncertainty": {
            "usable": bool(briefing["usable"]),
            "context_gaps": context_gaps,
            "warnings": _uncertainty_warnings(
                context_gaps=context_gaps,
                retrieval_provenance=retrieval_provenance,
            ),
        },
        "budget": budget,
        "retrieval_provenance": retrieval_provenance,
        "fallbacks": _fallback_markers(retrieval_provenance),
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
    request = report["request"]
    source = request["source"]
    query = request["query"]["text"]
    composition = report["composition"]
    budget = report["budget"]
    retrieval = report["retrieval_provenance"]
    briefing = report["agent_briefing"]
    primary_results = _cards_by_stage(report, "primary_retrieval")
    recent_supplements = _cards_by_stage(report, "recent_in_scope_supplement")
    lines = [
        "# Muninn v2 Shadow Rehydration Preview",
        "",
        "## Executive Summary",
        "",
        f"- Usable: `{str(briefing['usable']).lower()}`",
        (
            f"- Total cards: {budget['selected_total']} "
            f"({budget['primary_selected']} primary, {budget['supplement_selected']} supplements)"
        ),
        f"- Retrieval backend: `{retrieval.get('backend')}`",
        f"- Fallback used: `{str(retrieval.get('fallback_used')).lower()}`",
        f"- Degraded: `{str(retrieval.get('degraded')).lower()}`",
        "",
        "## Query / Task",
        "",
        f"`{query}`",
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
    if primary_results:
        for item in primary_results:
            lines.extend(_markdown_card(item, include_score=True))
    else:
        lines.append("- none")
    lines.extend(["", "## Recent In-Scope Supplements", ""])
    if recent_supplements:
        for item in recent_supplements:
            lines.extend(_markdown_card(item, include_score=False))
    else:
        lines.append("- none")
    lines.extend(["", "## Evidence / Provenance", ""])
    evidence_count = sum(int(item.get("evidence_count", 0)) for item in _all_items(report))
    included = len(report["selected_memory"].get("evidence", []))
    lines.append(f"- Evidence refs available on preview cards: {evidence_count}")
    lines.append(f"- Evidence refs included in report: {included}")
    lines.append(f"- Retrieval mode: `{retrieval.get('mode')}`")
    lines.append(f"- Degradation reasons: `{retrieval.get('degradation_reasons')}`")
    lines.extend(["", "## Explanation Notes", ""])
    lines.append(f"- Explanations included: `{str(bool(_any_explanations(report))).lower()}`")
    lines.append(f"- Duplicates removed: {budget['duplicates_removed']}")
    lines.append(f"- Omitted for budget: {budget['omitted_for_budget']}")
    lines.append(f"- Omitted for limit: {budget['omitted_for_limit']}")
    lines.extend(["", "## Context Gaps / Uncertainty", ""])
    if report["uncertainty"]["context_gaps"]:
        lines.extend(f"- {gap}" for gap in report["uncertainty"]["context_gaps"])
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


def _supplement_entries(
    recent_cards: Sequence[MemoryCard],
    *,
    query: str,
    primary_results: Sequence[dict[str, Any]],
    limit: int,
    strict: bool,
    include_evidence: bool,
    include_explanations: bool,
) -> list[dict[str, Any]]:
    query_tokens = set(normalize_tokens(query))
    focus_tokens = _supplement_focus_tokens(query_tokens)
    primary_tokens = _primary_domain_tokens(primary_results)
    strong_cap = min(int(limit), max(SUPPLEMENT_FALLBACK_CAP, len(primary_results) + SUPPLEMENT_RECENT_CAP_OFFSET))
    strong: list[SupplementCandidate] = []
    fallback: list[SupplementCandidate] = []
    for card in recent_cards:
        candidate = _score_supplement_candidate(
            card,
            focus_tokens=focus_tokens,
            query_tokens=query_tokens,
            primary_tokens=primary_tokens,
        )
        if candidate.reason == "exclude_background_or_weak_supplement":
            continue
        if candidate.reason == "recent_same_scope_continuity_fallback":
            if not strict:
                fallback.append(candidate)
            continue
        strong.append(candidate)

    _sort_supplement_candidates(strong)
    _sort_supplement_candidates(fallback)
    selected = strong[:strong_cap]
    selected_ids = {candidate.card.id for candidate in selected}
    if not any(candidate.reason == "recent_project_boundary_or_contract" for candidate in selected):
        boundary_candidates = [
            candidate
            for candidate in strong
            if candidate.reason == "recent_project_boundary_or_contract" and candidate.card.id not in selected_ids
        ]
        _sort_boundary_supplement_candidates(boundary_candidates)
        for candidate in boundary_candidates[:1]:
            if len(selected) >= int(limit):
                break
            selected.append(candidate)
            selected_ids.add(candidate.card.id)
    if not strict and len(selected) < int(limit):
        selected.extend(fallback[: min(SUPPLEMENT_FALLBACK_CAP, int(limit) - len(selected))])
    return [
        _supplement_entry(
            candidate,
            include_evidence=include_evidence,
            include_explanations=include_explanations,
        )
        for candidate in selected[: int(limit)]
    ]


def _score_supplement_candidate(
    card: MemoryCard,
    *,
    focus_tokens: set[str],
    query_tokens: set[str],
    primary_tokens: set[str],
) -> SupplementCandidate:
    text = card_search_text(card)
    tokens = set(normalize_tokens(text))
    title_summary_tokens = set(normalize_tokens(" ".join([card.title, card.summary])))
    query_hits = sorted(focus_tokens & tokens)
    title_query_hits = sorted(focus_tokens & title_summary_tokens)
    primary_hits = sorted(primary_tokens & tokens)
    numeric_hits = sorted(_supplement_numeric_tokens(query_tokens) & tokens)
    background_hits = _background_markers(text)
    boundary_hits = _boundary_markers(text)
    score = (
        (4.0 * len(numeric_hits))
        + (3.0 * len(query_hits))
        + (1.25 * min(len(primary_hits), 8))
        + (1.5 * len(title_query_hits))
    )
    penalties: dict[str, float] = {}
    if background_hits:
        penalties["background_or_contrast_only_signal"] = -12.0
        score -= 12.0

    reason = "recent_same_scope_continuity_fallback"
    if numeric_hits:
        reason = "recent_campaign_or_numeric_token_overlap"
    elif len(query_hits) >= 2:
        reason = "recent_query_token_overlap"
    elif len(query_hits) >= 1 and len(primary_hits) >= 2:
        reason = "recent_query_primary_domain_overlap"
    elif len(primary_hits) >= 3:
        reason = "recent_primary_domain_overlap"
    if boundary_hits and (query_hits or len(primary_hits) >= 2):
        reason = "recent_project_boundary_or_contract"
        score += 8.0

    if background_hits and reason != "recent_campaign_or_numeric_token_overlap":
        reason = "exclude_background_or_weak_supplement"
    elif reason == "recent_query_primary_domain_overlap" and score < 10.0:
        reason = "exclude_background_or_weak_supplement"
    elif reason == "recent_same_scope_continuity_fallback" and score < 5.0:
        reason = "recent_same_scope_continuity_fallback"
    elif score < 4.0:
        reason = "exclude_background_or_weak_supplement"

    matched_tokens = tuple(sorted(set(query_hits + primary_hits + numeric_hits)))
    sources: list[str] = []
    if query_hits:
        sources.append("query_tokens")
    if title_query_hits:
        sources.append("title_summary_tokens")
    if primary_hits:
        sources.append("primary_result_domain_tokens")
    if numeric_hits:
        sources.append("numeric_tokens")
    if not sources:
        sources.append("recent_same_scope")
    return SupplementCandidate(
        card=card,
        reason=reason,
        score=round(float(score), 6),
        matched_tokens=matched_tokens,
        candidate_sources=tuple(sources),
        penalties=penalties,
    )


def _supplement_entry(
    candidate: SupplementCandidate,
    *,
    include_evidence: bool,
    include_explanations: bool,
) -> dict[str, Any]:
    card = candidate.card
    explanation = None
    if include_explanations:
        explanation = {
            "retrieval_path": "recent_in_scope_shadow_supplement",
            "reason_code": candidate.reason,
            "score_semantics": "continuity supplement relevance score; primary retrieval remains authoritative",
            "candidate_sources": list(candidate.candidate_sources),
            "matched_tokens": list(candidate.matched_tokens),
            "score_components": {"supplement_relevance": candidate.score},
            "penalties": dict(candidate.penalties),
            "vector_used": False,
        }
    return _card_entry(
        card,
        stage="recent_in_scope_supplement",
        reason=candidate.reason,
        score=candidate.score,
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
        "record_type": "memory_card",
        "kind": card.kind,
        "status": card.status,
        "title": card.title,
        "summary": card.summary,
        "body_excerpt": _body_excerpt(card.body),
        "confidence": float(card.confidence),
        "scope_key": card.scope_key,
        "entity_ids": list(card.entity_ids),
        "tags": list(card.tags),
        "created_at": card.created_at,
        "updated_at": card.updated_at,
        "provenance": dict(card.provenance),
        "metadata": dict(card.metadata),
        "selection": {
            "stage": stage,
            "reason": reason,
            "score": score,
            "retrieval_rank": retrieval_rank,
        },
        "evidence_ids": [item.id for item in card.evidence],
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


def _supplement_focus_tokens(query_tokens: set[str]) -> set[str]:
    return {
        token
        for token in query_tokens
        if len(token) >= 4 and token not in SUPPLEMENT_GENERIC_TOKENS
    }


def _primary_domain_tokens(primary_results: Sequence[dict[str, Any]]) -> set[str]:
    tokens: set[str] = set()
    for item in primary_results:
        text = " ".join(
            [
                str(item.get("title") or ""),
                str(item.get("summary") or ""),
                str(item.get("body_excerpt") or ""),
                " ".join(str(tag) for tag in item.get("tags", [])),
            ]
        )
        tokens.update(normalize_tokens(text))
        explanation = item.get("explanation")
        if isinstance(explanation, dict):
            tokens.update(str(token) for token in explanation.get("matched_tokens", []))
    return {
        token
        for token in tokens
        if len(token) >= 4 and token not in SUPPLEMENT_GENERIC_TOKENS
    }


def _background_markers(text: str) -> tuple[str, ...]:
    normalized = " ".join(str(text or "").lower().split())
    return tuple(marker for marker in SUPPLEMENT_BACKGROUND_MARKERS if marker in normalized)


def _boundary_markers(text: str) -> tuple[str, ...]:
    normalized = " ".join(str(text or "").lower().split())
    return tuple(marker for marker in SUPPLEMENT_BOUNDARY_MARKERS if marker in normalized)


def _supplement_numeric_tokens(query_tokens: set[str]) -> set[str]:
    out: set[str] = set()
    for token in query_tokens:
        if not any(ch.isdigit() for ch in token):
            continue
        if token.startswith(("campaign", "phase")):
            out.add(token)
        elif token.startswith("v") and token[1:].isdigit():
            out.add(token)
        elif token[0].isdigit():
            out.add(token)
    return out


def _sort_supplement_candidates(candidates: list[SupplementCandidate]) -> None:
    candidates.sort(key=lambda candidate: str(candidate.card.id))
    candidates.sort(key=lambda candidate: -candidate.score)
    candidates.sort(key=lambda candidate: str(candidate.card.updated_at or ""), reverse=True)


def _sort_boundary_supplement_candidates(candidates: list[SupplementCandidate]) -> None:
    candidates.sort(key=lambda candidate: str(candidate.card.id))
    candidates.sort(key=lambda candidate: str(candidate.card.updated_at or ""), reverse=True)
    candidates.sort(key=lambda candidate: -candidate.score)


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
            "record_type": "evidence",
            "type": item.evidence_type,
            "ref": item.ref,
            "excerpt": item.excerpt,
            "source_id": item.source_id,
            "metadata": dict(item.metadata),
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


def _response_id(*, generated_at: str, query: str, source_db: str) -> str:
    digest = hashlib.sha256(
        "\n".join(
            [
                REHYDRATE_RESPONSE_SCHEMA_VERSION,
                str(generated_at),
                str(source_db),
                str(query),
            ]
        ).encode("utf-8")
    ).hexdigest()[:16]
    return f"rehydrate_{digest}"


def _budget_payload(
    *,
    limit: int,
    primary_limit: int,
    recent_limit: int,
    max_chars: int | None,
    selected_cards: Sequence[dict[str, Any]],
    primary_results: Sequence[dict[str, Any]],
    recent_supplements: Sequence[dict[str, Any]],
    duplicate_supplements: int,
    omitted_for_budget: int,
    omitted_for_limit: int,
    candidate_cards: int,
) -> dict[str, Any]:
    return {
        "limit": int(limit),
        "primary_limit": int(primary_limit),
        "recent_limit": int(recent_limit),
        "max_chars": max_chars,
        "used_chars": sum(_item_chars(item) for item in selected_cards),
        "candidate_cards": int(candidate_cards),
        "selected_total": len(selected_cards),
        "primary_selected": len(primary_results),
        "supplement_selected": len(recent_supplements),
        "duplicates_removed": int(duplicate_supplements),
        "omitted_for_budget": int(omitted_for_budget),
        "omitted_for_limit": int(omitted_for_limit),
    }


def _selected_evidence(cards: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        for evidence in card.get("evidence", []):
            key = str(evidence.get("id") or f"{card.get('id')}:{evidence.get('ref')}")
            if key in seen:
                continue
            seen.add(key)
            item = dict(evidence)
            item["card_id"] = card.get("id")
            out.append(item)
    out.sort(key=lambda item: (str(item.get("card_id") or ""), str(item.get("id") or "")))
    return out


def _explanations(
    primary_results: Sequence[dict[str, Any]],
    recent_supplements: Sequence[dict[str, Any]],
    *,
    include_explanations: bool,
) -> dict[str, Any]:
    cards = [*primary_results, *recent_supplements]
    return {
        "format": "muninn.v2.retrieval_explanation.v1",
        "included": bool(include_explanations),
        "notes": (
            []
            if include_explanations
            else ["Run with --include-explanations to include score components and matched-field details."]
        ),
        "cards": [
            {
                "card_id": item["id"],
                "stage": item["selection"]["stage"],
                "reason": item["selection"]["reason"],
                "score": item["selection"].get("score"),
                "retrieval_rank": item["selection"].get("retrieval_rank"),
                "details": item.get("explanation") if include_explanations else None,
            }
            for item in cards
        ],
    }


def _retrieval_provenance(retrieval: dict[str, Any], *, retrieval_mode: str) -> dict[str, Any]:
    status = retrieval.get("status") if isinstance(retrieval.get("status"), dict) else None
    reasons = [str(item) for item in (status or {}).get("reason", [])]
    fallback_used = bool(retrieval.get("fallback_used"))
    if fallback_used and "retrieval_fallback_used" not in reasons:
        reasons.append("retrieval_fallback_used")
    degraded = bool(fallback_used or (status and status.get("degraded")))
    return {
        "mode": retrieval_mode,
        "backend": retrieval.get("backend"),
        "fallback_used": fallback_used,
        "degraded": degraded,
        "degradation_reasons": reasons,
        "provider_status": status,
        "query_profile": retrieval.get("query_profile"),
        "result_count": len(retrieval.get("results", [])),
        "candidate_source": "explicit_v2_shadow_db",
        "retrieval_paths": _retrieval_paths(retrieval),
    }


def _retrieval_paths(retrieval: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    for result in retrieval.get("results", []):
        explanation = result.get("explanation") if isinstance(result, dict) else None
        if isinstance(explanation, dict) and explanation.get("retrieval_path"):
            paths.add(str(explanation["retrieval_path"]))
        elif isinstance(result, dict) and result.get("backend"):
            paths.add(str(result["backend"]))
    if not paths and retrieval.get("backend"):
        paths.add(str(retrieval["backend"]))
    return sorted(paths)


def _fallback_markers(retrieval_provenance: dict[str, Any]) -> list[dict[str, Any]]:
    reasons = [str(item) for item in retrieval_provenance.get("degradation_reasons", [])]
    backend = str(retrieval_provenance.get("backend") or "")
    return [
        {
            "name": "derived_vector_backend",
            "active": backend in {"derived_vector_index", "hybrid"},
            "degraded": bool(retrieval_provenance.get("degraded")),
            "reason": "; ".join(reasons) if reasons else None,
        },
        {
            "name": "lexical_fallback",
            "active": bool(retrieval_provenance.get("fallback_used")) or backend == "lexical_fallback",
            "degraded": False,
            "reason": "fallback retrieval path used" if retrieval_provenance.get("fallback_used") else None,
        },
    ]


def _uncertainty_warnings(
    *,
    context_gaps: Sequence[str],
    retrieval_provenance: dict[str, Any],
) -> list[str]:
    warnings = list(context_gaps)
    if retrieval_provenance.get("degraded"):
        reasons = retrieval_provenance.get("degradation_reasons") or []
        warnings.append("Retrieval/index backend degraded: " + ", ".join(str(item) for item in reasons))
    return list(dict.fromkeys(warnings))


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
    return list(report.get("selected_memory", {}).get("cards", []))


def _any_explanations(report: dict[str, Any]) -> bool:
    return bool(report.get("explanations", {}).get("included"))


def _cards_by_stage(report: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    return [
        item
        for item in _all_items(report)
        if item.get("selection", {}).get("stage") == stage
    ]


def _markdown_card(item: dict[str, Any], *, include_score: bool) -> list[str]:
    selection = item.get("selection", {})
    score = f" score=`{selection.get('score')}`" if include_score else ""
    lines = [
        f"- `{item['id']}` {item['title']}",
        (
            f"  - stage: `{selection.get('stage')}` reason: `{selection.get('reason')}` kind: `{item['kind']}` "
            f"updated: `{item.get('updated_at')}`{score}"
        ),
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

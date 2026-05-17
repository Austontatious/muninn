from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..core.models import MemoryCard
from ..indexes import DerivedIndexProvider
from .scoring import (
    card_token_document_frequency,
    evidence_text,
    field_tokens,
    inverse_document_frequency,
    normalized_text,
    query_profile,
)

DEFAULT_MIN_SCORE = 35.0


@dataclass
class HybridScore:
    card: MemoryCard
    score: float
    components: dict[str, float] = field(default_factory=dict)
    matched_fields: dict[str, list[str]] = field(default_factory=dict)
    penalties: dict[str, float] = field(default_factory=dict)
    vector_score: float | None = None
    candidate_sources: set[str] = field(default_factory=set)
    matched_tokens: set[str] = field(default_factory=set)

    def add_component(self, name: str, value: float) -> None:
        if value == 0:
            return
        self.components[name] = round(float(value), 6)
        self.score += float(value)

    def add_penalty(self, name: str, value: float) -> None:
        if value == 0:
            return
        amount = -abs(float(value))
        self.penalties[name] = round(amount, 6)
        self.score += amount


def hybrid_recall(
    records: Sequence[MemoryCard],
    query: str,
    *,
    provider: DerivedIndexProvider | None = None,
    limit: int = 10,
    scope_key: str | None = None,
    min_score: float = DEFAULT_MIN_SCORE,
) -> dict[str, Any]:
    candidates = [
        card
        for card in records
        if str(card.status or "active") == "active" and (not scope_key or card.scope_key == scope_key)
    ]
    profile = query_profile(query)
    if not profile.unique_tokens:
        return {
            "backend": "hybrid",
            "fallback_used": False,
            "status": None,
            "results": [],
            "query_profile": profile.to_dict(),
        }

    status_payload: dict[str, Any] | None = None
    vector_scores: dict[str, float] = {}
    if provider is not None:
        status = provider.status()
        status_payload = status.to_dict()
        if status.indexed_records > 0 and not status.stale_records:
            for row in provider.query(query, limit=max(len(candidates), int(limit) * 4)):
                if scope_key and str(row.get("scope_key") or "") != scope_key:
                    continue
                vector_scores[str(row.get("record_id") or "")] = float(row.get("score") or 0.0)

    document_frequency = card_token_document_frequency(candidates)
    recency_boosts = _recency_boosts(candidates)
    scored: list[HybridScore] = []
    for card in candidates:
        item = _score_card(
            card,
            profile=profile,
            total_records=len(candidates),
            document_frequency=document_frequency,
            vector_score=vector_scores.get(card.id),
            recency_boost=recency_boosts.get(card.id, 0.0),
            scope_matched=bool(scope_key and card.scope_key == scope_key),
        )
        if item.score >= float(min_score):
            scored.append(item)

    scored.sort(key=lambda item: (-round(item.score, 9), str(item.card.updated_at), str(item.card.id)))
    return {
        "backend": "hybrid",
        "fallback_used": False,
        "status": status_payload,
        "query_profile": profile.to_dict(),
        "results": [_result_payload(item, rank=index) for index, item in enumerate(scored[: max(1, int(limit))], start=1)],
    }


def _score_card(
    card: MemoryCard,
    *,
    profile: Any,
    total_records: int,
    document_frequency: Any,
    vector_score: float | None,
    recency_boost: float,
    scope_matched: bool,
) -> HybridScore:
    item = HybridScore(card=card, score=0.0, vector_score=vector_score)
    query_tokens = set(profile.unique_tokens)
    fields = {
        "title": (card.title, 6.0, 80.0, 45.0),
        "summary": (card.summary, 3.5, 70.0, 28.0),
        "body": (card.body, 1.4, 60.0, 22.0),
        "tags": (" ".join(card.tags), 2.0, 30.0, 8.0),
        "evidence": (" ".join(evidence_text(card)), 0.45, 15.0, 8.0),
    }
    field_hit_sets: dict[str, set[str]] = {}
    for field_name, (text, weight, cap, phrase_boost) in fields.items():
        tokens = field_tokens(text)
        hits = sorted(query_tokens & tokens)
        if hits:
            item.candidate_sources.add(field_name)
            item.matched_tokens.update(hits)
            item.matched_fields[field_name] = hits
            field_hit_sets[field_name] = set(hits)
            value = sum(
                inverse_document_frequency(
                    token,
                    total_records=total_records,
                    document_frequency=document_frequency,
                )
                for token in hits
            ) * float(weight)
            item.add_component(f"{field_name}_token_overlap", min(value, float(cap)))
        if profile.phrase and profile.phrase in normalized_text(text):
            item.candidate_sources.add(field_name)
            item.add_component(f"{field_name}_phrase_match", float(phrase_boost))

    title_tokens = field_tokens(card.title)
    body_tokens = field_tokens(" ".join([card.summary, card.body]))
    evidence_tokens = field_tokens(" ".join(evidence_text(card)))
    coverage = len(item.matched_tokens) / max(1, len(query_tokens))
    title_coverage = len(query_tokens & title_tokens) / max(1, len(query_tokens))
    body_coverage = len(query_tokens & body_tokens) / max(1, len(query_tokens))

    if title_coverage >= 0.5:
        item.add_component("title_coverage_boost", 18.0 * title_coverage)
    if body_coverage >= 0.75:
        item.add_component("body_coverage_boost", 10.0 * body_coverage)

    numeric_matches = [
        token
        for token in profile.numeric_tokens
        if token in title_tokens or token in body_tokens or token in evidence_tokens
    ]
    if numeric_matches:
        item.add_component("numeric_token_match", 10.0 * len(numeric_matches))
    campaign_matches = [
        token
        for token in profile.campaign_tokens
        if token in title_tokens or token in body_tokens or token in evidence_tokens
    ]
    if campaign_matches:
        item.add_component("campaign_token_match", 6.0 * len(campaign_matches))

    if scope_matched:
        item.add_component("project_space_match", 3.0)
    if recency_boost > 0:
        item.add_component("recency_boost", recency_boost)
    salience = _salience(card)
    if salience > 0:
        item.add_component("salience_boost", min(2.0, salience * 2.0))
    if vector_score and vector_score > 0:
        item.candidate_sources.add("vector")
        item.add_component("vector_similarity_rescue", min(5.0, vector_score * 5.0))

    broad_hits = [
        token
        for token in item.matched_tokens
        if total_records > 0 and (document_frequency[token] / total_records) > 0.45
    ]
    if coverage < 0.45:
        item.add_penalty("low_specificity_match", 12.0 * (0.45 - coverage))
    if broad_hits and len(item.matched_tokens) <= max(2, len(query_tokens) // 2):
        item.add_penalty("broad_token_match", 2.0 * len(broad_hits))
    if set(field_hit_sets) == {"evidence"}:
        item.add_penalty("evidence_only_weak_match", 8.0)
    if not scope_matched and card.scope_key:
        item.add_penalty("missing_project_space_match", 6.0)
    return item


def _result_payload(item: HybridScore, *, rank: int) -> dict[str, Any]:
    card = item.card
    return {
        "record_id": card.id,
        "rank": rank,
        "score": round(float(item.score), 6),
        "backend": "hybrid",
        "scope_key": card.scope_key,
        "record": card.to_dict(),
        "explanation": {
            "retrieval_path": "v2_hybrid_recall",
            "score_semantics": "higher deterministic hybrid score is better",
            "candidate_sources": sorted(item.candidate_sources),
            "matched_tokens": sorted(item.matched_tokens),
            "matched_fields": {key: list(value) for key, value in sorted(item.matched_fields.items())},
            "score_components": dict(sorted(item.components.items())),
            "penalties": dict(sorted(item.penalties.items())),
            "vector_used": item.vector_score is not None,
            "vector_score": item.vector_score,
        },
    }


def _recency_boosts(cards: Sequence[MemoryCard]) -> dict[str, float]:
    updates = sorted({str(card.updated_at or "") for card in cards})
    if len(updates) <= 1:
        return {card.id: 0.0 for card in cards}
    ranks = {value: index for index, value in enumerate(updates)}
    max_rank = max(1, len(updates) - 1)
    return {card.id: round((ranks[str(card.updated_at or "")] / max_rank) * 2.0, 6) for card in cards}


def _salience(card: MemoryCard) -> float:
    raw = card.metadata.get("v1_salience") if isinstance(card.metadata, dict) else None
    try:
        return max(0.0, float(raw or 0.0))
    except (TypeError, ValueError):
        return 0.0

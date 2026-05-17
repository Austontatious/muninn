from __future__ import annotations

from typing import Any, Sequence

from ..core.models import MemoryCard


def lexical_recall(
    records: Sequence[MemoryCard],
    query: str,
    *,
    limit: int = 10,
    scope_key: str | None = None,
) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    scored: list[tuple[float, MemoryCard, dict[str, Any]]] = []
    for card in records:
        if str(card.status or "active") != "active":
            continue
        if scope_key and card.scope_key != scope_key:
            continue
        score, explanation = _score_card(card, tokens)
        if score <= 0:
            continue
        scored.append((score, card, explanation))
    scored.sort(key=lambda item: (-item[0], str(item[1].updated_at), str(item[1].id)))
    results: list[dict[str, Any]] = []
    for rank, (score, card, explanation) in enumerate(scored[: max(1, int(limit))], start=1):
        results.append(
            {
                "record_id": card.id,
                "rank": rank,
                "score": round(float(score), 6),
                "backend": "lexical_fallback",
                "scope_key": card.scope_key,
                "record": card.to_dict(),
                "explanation": explanation,
            }
        )
    return results


def _score_card(card: MemoryCard, tokens: list[str]) -> tuple[float, dict[str, Any]]:
    title = card.title.lower()
    summary = card.summary.lower()
    body = card.body.lower()
    tags = " ".join(card.tags).lower()
    evidence = " ".join(
        " ".join(str(part or "") for part in (item.ref, item.excerpt))
        for item in card.evidence
    ).lower()
    fields = {
        "title": (title, 5.0),
        "summary": (summary, 3.0),
        "tags": (tags, 2.0),
        "body": (body, 1.0),
        "evidence": (evidence, 1.0),
    }
    score = 0.0
    field_hits: dict[str, list[str]] = {}
    for field_name, (text, weight) in fields.items():
        hits = sorted({token for token in tokens if token in text})
        if hits:
            field_hits[field_name] = hits
            score += weight * len(hits)
    phrase = " ".join(tokens)
    combined = " ".join(value for value, _weight in fields.values())
    phrase_hit = bool(phrase and phrase in combined)
    if phrase_hit:
        score += 10.0
    return score, {
        "retrieval_path": "v2_provisional_lexical_recall",
        "fallback": True,
        "score_semantics": "higher weighted token/phrase score is better",
        "matched_tokens": sorted({token for hits in field_hits.values() for token in hits}),
        "field_hits": field_hits,
        "phrase_hit": phrase_hit,
    }


def _tokens(text: str) -> list[str]:
    out: list[str] = []
    token: list[str] = []
    for ch in str(text or "").lower():
        if ch.isalnum() or ch == "_":
            token.append(ch)
        elif token:
            out.append("".join(token))
            token = []
    if token:
        out.append("".join(token))
    return out

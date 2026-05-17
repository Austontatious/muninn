from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from ..core.models import MemoryCard

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


@dataclass(frozen=True)
class QueryProfile:
    raw: str
    tokens: tuple[str, ...]
    unique_tokens: tuple[str, ...]
    phrase: str
    numeric_tokens: tuple[str, ...]
    campaign_tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "tokens": list(self.tokens),
            "unique_tokens": list(self.unique_tokens),
            "phrase": self.phrase,
            "numeric_tokens": list(self.numeric_tokens),
            "campaign_tokens": list(self.campaign_tokens),
        }


def normalize_tokens(text: str) -> list[str]:
    normalized = str(text or "").replace("_", " ").replace("-", " ")
    return [
        token.lower()
        for token in TOKEN_RE.findall(normalized)
        if token and token.lower() not in STOP_WORDS
    ]


def query_profile(text: str) -> QueryProfile:
    tokens = normalize_tokens(text)
    unique = _dedupe(tokens)
    numeric = [token for token in unique if any(ch.isdigit() for ch in token)]
    campaign = [
        token
        for token in numeric
        if re.fullmatch(r"\d{2,}[a-z]?", token) or re.fullmatch(r"[a-z]+\d+[a-z]?", token)
    ]
    return QueryProfile(
        raw=str(text or ""),
        tokens=tuple(tokens),
        unique_tokens=tuple(unique),
        phrase=" ".join(tokens),
        numeric_tokens=tuple(numeric),
        campaign_tokens=tuple(campaign),
    )


def card_token_document_frequency(records: Sequence[MemoryCard]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for card in records:
        counts.update(set(normalize_tokens(card_search_text(card))))
    return counts


def card_search_text(card: MemoryCard) -> str:
    evidence = " ".join(evidence_text(card))
    return " ".join([card.title, card.summary, card.body, " ".join(card.tags), evidence])


def evidence_text(card: MemoryCard) -> list[str]:
    return [
        " ".join(str(part or "") for part in (item.ref, item.excerpt))
        for item in card.evidence
    ]


def inverse_document_frequency(token: str, *, total_records: int, document_frequency: Counter[str]) -> float:
    return math.log((int(total_records) + 1) / (int(document_frequency[token]) + 1)) + 1.0


def normalized_text(text: str) -> str:
    return " ".join(normalize_tokens(text))


def field_tokens(text: str) -> set[str]:
    return set(normalize_tokens(text))


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out

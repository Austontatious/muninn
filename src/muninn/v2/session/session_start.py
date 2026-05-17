from __future__ import annotations

from typing import Any, Sequence

from ..core.models import MemoryCard, utc_now
from ..indexes import DerivedIndexProvider
from ..retrieval import recall_with_fallback


def build_session_report(
    records: Sequence[MemoryCard],
    query: str,
    *,
    provider: DerivedIndexProvider | None = None,
    limit: int = 10,
    scope_key: str | None = None,
) -> dict[str, Any]:
    recall = recall_with_fallback(
        records,
        query,
        provider=provider,
        limit=limit,
        scope_key=scope_key,
    )
    return {
        "record_type": "muninn_v2_session_retrieval_report",
        "generated_at": utc_now(),
        "query": " ".join(str(query or "").split()),
        "scope_key": scope_key,
        "backend": recall["backend"],
        "fallback_used": bool(recall["fallback_used"]),
        "results": recall["results"],
        "note": "v2 session report is an opt-in helper and is not a live Codex startup default.",
    }

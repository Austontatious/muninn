from __future__ import annotations

from typing import Any, Sequence

from ..core.models import MemoryCard
from ..indexes import DerivedIndexProvider
from .lexical_recall import lexical_recall


def recall_with_fallback(
    records: Sequence[MemoryCard],
    query: str,
    *,
    provider: DerivedIndexProvider | None = None,
    limit: int = 10,
    scope_key: str | None = None,
) -> dict[str, Any]:
    vector_results: list[dict[str, Any]] = []
    status_payload: dict[str, Any] | None = None
    if provider is not None:
        status = provider.status()
        status_payload = status.to_dict()
        if status.indexed_records > 0 and not status.stale_records:
            vector_results = provider.query(query, limit=limit)
            if scope_key:
                vector_results = [
                    row for row in vector_results if str(row.get("scope_key") or "") == scope_key
                ]
    if vector_results:
        return {
            "backend": "derived_vector_index",
            "fallback_used": False,
            "status": status_payload,
            "results": _rank(vector_results, limit=limit),
        }
    lexical_results = lexical_recall(records, query, limit=limit, scope_key=scope_key)
    return {
        "backend": "lexical_fallback",
        "fallback_used": True,
        "status": status_payload,
        "results": lexical_results,
    }


def _rank(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rank, row in enumerate(rows[: max(1, int(limit))], start=1):
        item = dict(row)
        item["rank"] = rank
        out.append(item)
    return out

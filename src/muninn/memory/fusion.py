from __future__ import annotations


def rrf_fuse(fts_ids: list[str], vec_ids: list[str], k0: int) -> list[str]:
    k0 = max(1, int(k0))
    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}

    for rank, item_id in enumerate(fts_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k0 + rank)
        best_rank[item_id] = min(best_rank.get(item_id, rank), rank)

    for rank, item_id in enumerate(vec_ids, start=1):
        scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k0 + rank)
        best_rank[item_id] = min(best_rank.get(item_id, rank), rank)

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], best_rank.get(kv[0], 10**9), kv[0]))
    return [item_id for item_id, _ in ranked]

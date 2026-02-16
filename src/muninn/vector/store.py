from __future__ import annotations

from typing import Literal

from .. import db
from ..models import UpsertEmbeddingsItem, VectorHit
from .vectors import dot, from_f32_blob, l2_normalize, to_f32_blob

VALID_KINDS: set[str] = {"fact", "episode", "preference"}


def upsert_embeddings(
    namespace: str,
    items: list[UpsertEmbeddingsItem],
    now_ts: float | None = None,
) -> tuple[int, int, list[str]]:
    _ = namespace
    conn = db.connect()
    ts = float(now_ts) if now_ts is not None else db.now()

    upserted = 0
    rejected = 0
    reasons: list[str] = []

    for item in items:
        vec = [float(v) for v in item.vector]
        dim = len(vec)
        if dim == 0:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: empty vector")
            continue
        if dim < 8 or dim > 4096:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: dim out of range [{dim}]")
            continue

        try:
            normalized = l2_normalize(vec)
            blob = to_f32_blob(normalized)
            conn.execute(
                """
                INSERT INTO embeddings (item_id, kind, entity_id, model, dim, vector_blob, updated_at)
                VALUES (?,?,?,?,?,?,?)
                ON CONFLICT(item_id) DO UPDATE SET
                    kind = excluded.kind,
                    entity_id = excluded.entity_id,
                    model = excluded.model,
                    dim = excluded.dim,
                    vector_blob = excluded.vector_blob,
                    updated_at = excluded.updated_at
                """,
                (item.item_id, item.kind, item.entity_id, item.model, dim, blob, ts),
            )
            upserted += 1
        except ValueError as exc:
            rejected += 1
            reasons.append(f"Rejected {item.item_id}: {exc}")

    conn.commit()
    return upserted, rejected, reasons


def query_vector(
    namespace: str,
    model: str,
    query_vec: list[float],
    entity_id: str | None,
    kinds: list[Literal["fact", "episode", "preference"]] | None,
    k: int,
    max_scan: int,
) -> list[VectorHit]:
    _ = namespace
    if not query_vec:
        return []

    try:
        query_norm = l2_normalize([float(v) for v in query_vec])
    except ValueError:
        return []
    query_dim = len(query_norm)
    conn = db.connect()

    where = ["model = ?"]
    params: list[object] = [model]

    if entity_id:
        where.append("entity_id = ?")
        params.append(entity_id)

    if kinds:
        kind_list = [kind for kind in kinds if kind in VALID_KINDS]
        if not kind_list:
            return []
        placeholders = ", ".join(["?"] * len(kind_list))
        where.append(f"kind IN ({placeholders})")
        params.extend(kind_list)

    scan_cap = max(1, int(max_scan))
    sql = (
        "SELECT item_id, kind, entity_id, dim, vector_blob FROM embeddings "
        f"WHERE {' AND '.join(where)} LIMIT ?"
    )
    rows = db.fetch_all(conn, sql, tuple(params + [scan_cap]))

    hits: list[VectorHit] = []
    for row in rows:
        dim = int(row["dim"])
        if dim != query_dim:
            continue

        try:
            stored = from_f32_blob(row["vector_blob"])
            if len(stored) != query_dim:
                continue
            score = dot(query_norm, stored)
        except ValueError:
            continue

        hits.append(
            VectorHit(
                item_id=row["item_id"],
                kind=row["kind"],
                entity_id=row["entity_id"],
                score=float(score),
            )
        )

    hits.sort(key=lambda hit: (-hit.score, hit.item_id))
    return hits[: max(1, int(k))]

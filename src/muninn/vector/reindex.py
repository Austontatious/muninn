from __future__ import annotations

from typing import Literal

from .. import db
from ..config import sqlite_vec_enabled
from ..models import ReindexVectorsResponse
from . import sqlite_vec_backend
from .sqlite_vec_loader import is_sqlite_vec_loaded, maybe_load_sqlite_vec, serialize_f32
from .vectors import from_f32_blob


def _scope_filters(namespace: str, model: str | None, dim: int | None) -> tuple[str, list[object]]:
    where = ["namespace = ?"]
    params: list[object] = [namespace]
    if model is not None:
        where.append("model = ?")
        params.append(model)
    if dim is not None:
        where.append("dim = ?")
        params.append(int(dim))
    return " AND ".join(where), params


def _decide_backend(
    conn,
    force_backend: Literal["auto", "sqlite_vec", "bruteforce"],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if force_backend == "bruteforce":
        return "bruteforce", reasons

    if not sqlite_vec_enabled():
        reasons.append("sqlite-vec disabled by MUNINN_SQLITE_VEC_ENABLED; using bruteforce")
        return "bruteforce", reasons

    loaded = maybe_load_sqlite_vec(conn) or is_sqlite_vec_loaded(conn)
    if loaded:
        return "sqlite_vec", reasons

    if force_backend == "sqlite_vec":
        reasons.append("sqlite-vec backend requested but unavailable; using bruteforce")
    else:
        reasons.append("sqlite-vec unavailable; using bruteforce")
    return "bruteforce", reasons


def reindex_vectors(
    namespace: str,
    model: str | None = None,
    dim: int | None = None,
    batch_size: int = 500,
    dry_run: bool = False,
    force_backend: Literal["auto", "sqlite_vec", "bruteforce"] = "auto",
) -> ReindexVectorsResponse:
    conn = db.connect()
    batch = max(1, int(batch_size))
    where_sql, where_params = _scope_filters(namespace, model, dim)

    total_row = db.fetch_one(
        conn,
        f"SELECT count(*) AS n FROM embeddings WHERE {where_sql}",
        tuple(where_params),
    )
    scanned_total = int(total_row["n"] if total_row else 0)

    backend_used, reasons = _decide_backend(conn, force_backend)
    if backend_used == "bruteforce":
        conn.close()
        return ReindexVectorsResponse(
            namespace=namespace,
            backend_used="bruteforce",
            scanned=scanned_total,
            reindexed=0,
            skipped=scanned_total,
            reasons=reasons,
        )

    # sqlite-vec path
    if dry_run:
        conn.close()
        return ReindexVectorsResponse(
            namespace=namespace,
            backend_used="sqlite_vec",
            scanned=scanned_total,
            reindexed=scanned_total,
            skipped=0,
            reasons=reasons,
        )

    pair_rows = db.fetch_all(
        conn,
        f"SELECT DISTINCT model, dim FROM embeddings WHERE {where_sql}",
        tuple(where_params),
    )

    # Recreate vec tables for the selected scope to avoid stale/orphaned rows.
    for pair in pair_rows:
        sqlite_vec_backend.drop_vec_table(conn, model=pair["model"], dim=int(pair["dim"]))

    conn.execute(f"DELETE FROM embeddings_vec_index WHERE {where_sql}", tuple(where_params))
    conn.commit()

    scanned = 0
    reindexed = 0
    skipped = 0

    offset = 0
    while True:
        rows = db.fetch_all(
            conn,
            (
                "SELECT item_id, kind, entity_id, model, dim, vector_blob, updated_at "
                f"FROM embeddings WHERE {where_sql} "
                "ORDER BY updated_at ASC, item_id ASC LIMIT ? OFFSET ?"
            ),
            tuple(where_params + [batch, offset]),
        )
        if not rows:
            break

        for row in rows:
            scanned += 1
            try:
                vec = from_f32_blob(row["vector_blob"])
                vec_blob = serialize_f32(vec)
                sqlite_vec_backend.upsert_vec(
                    conn=conn,
                    namespace=namespace,
                    item_id=row["item_id"],
                    model=row["model"],
                    dim=int(row["dim"]),
                    kind=row["kind"],
                    entity_id=row["entity_id"],
                    embedding_f32_blob=vec_blob,
                    updated_at=float(row["updated_at"]),
                )
                reindexed += 1
            except Exception as exc:  # pragma: no cover - defensive
                skipped += 1
                if len(reasons) < 50:
                    reasons.append(f"Skip {row['item_id']}: {exc}")

        conn.commit()
        offset += batch

    conn.close()
    return ReindexVectorsResponse(
        namespace=namespace,
        backend_used="sqlite_vec",
        scanned=scanned,
        reindexed=reindexed,
        skipped=skipped,
        reasons=reasons,
    )

from __future__ import annotations

import json

from .. import db
from ..models import Provenance, RetrievedItem


def retrieve(namespace: str, query: str, entity_id: str | None, k: int) -> list[RetrievedItem]:
    # v0: naive retrieval = most recent items (optionally filtered by entity).
    # v1: replace with hybrid retrieval.
    _ = namespace, query
    conn = db.connect()
    items: list[RetrievedItem] = []

    ent_filter = ""
    params: list[str] = []
    if entity_id:
        ent_filter = "WHERE entity_id = ?"
        params.append(entity_id)

    # episodes
    rows = db.fetch_all(
        conn,
        f"SELECT id, entity_id, summary, confidence, provenance_json FROM episodes {ent_filter} ORDER BY created_at DESC LIMIT ?",
        tuple(params + [str(k)]),
    )
    for row in rows:
        items.append(
            RetrievedItem(
                kind="episode",
                id=row["id"],
                entity_id=row["entity_id"],
                text=row["summary"],
                confidence=float(row["confidence"]),
                provenance=Provenance(**json.loads(row["provenance_json"])),
            )
        )

    # facts
    rows = db.fetch_all(
        conn,
        "SELECT id, subject_id as entity_id, predicate, object, confidence, provenance_json "
        f"FROM facts {'WHERE subject_id = ?' if entity_id else ''} ORDER BY created_at DESC LIMIT ?",
        tuple(([entity_id] if entity_id else []) + [k]),
    )
    for row in rows:
        items.append(
            RetrievedItem(
                kind="fact",
                id=row["id"],
                entity_id=row["entity_id"],
                text=f"{row['predicate']}: {row['object']}",
                confidence=float(row["confidence"]),
                provenance=Provenance(**json.loads(row["provenance_json"])),
            )
        )

    # preferences
    rows = db.fetch_all(
        conn,
        f"SELECT id, entity_id, key, value, confidence, provenance_json FROM preferences {ent_filter} ORDER BY created_at DESC LIMIT ?",
        tuple(params + [str(k)]),
    )
    for row in rows:
        items.append(
            RetrievedItem(
                kind="preference",
                id=row["id"],
                entity_id=row["entity_id"],
                text=f"{row['key']}={row['value']}",
                confidence=float(row["confidence"]),
                provenance=Provenance(**json.loads(row["provenance_json"])),
            )
        )

    return items[:k]

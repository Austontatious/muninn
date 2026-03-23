from __future__ import annotations

from typing import Any

from .. import db
from ..models import RetrievedCard, RetrievedEvidence


def _upsert_signal(
    conn,
    namespace: str,
    owner_type: str,
    owner_id: str,
    query_hash: str | None,
    now_ts: float,
) -> None:
    conn.execute(
        """
        INSERT INTO signals
            (namespace, owner_type, owner_id, access_count, last_accessed_at, last_query_hash, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(namespace, owner_type, owner_id) DO UPDATE SET
            access_count = signals.access_count + 1,
            last_accessed_at = excluded.last_accessed_at,
            last_query_hash = excluded.last_query_hash,
            updated_at = excluded.updated_at
        """,
        (
            namespace,
            owner_type,
            owner_id,
            1,
            now_ts,
            query_hash,
            now_ts,
            now_ts,
        ),
    )


def _upsert_coaccess_edge(
    conn,
    namespace: str,
    a_type: str,
    a_id: str,
    b_type: str,
    b_id: str,
    now_ts: float,
) -> None:
    conn.execute(
        """
        INSERT INTO coaccess_edges
            (namespace, a_type, a_id, b_type, b_id, weight, updated_at)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(namespace, a_type, a_id, b_type, b_id) DO UPDATE SET
            weight = coaccess_edges.weight + 1.0,
            updated_at = excluded.updated_at
        """,
        (namespace, a_type, a_id, b_type, b_id, 1.0, now_ts),
    )


def record_access(
    namespace: str,
    cards: list[RetrievedCard],
    evidence: list[RetrievedEvidence],
    query_hash: str | None,
    now_ts: float | None = None,
) -> dict[str, Any]:
    timestamp = now_ts if now_ts is not None else db.now()

    card_nodes: set[tuple[str, str]] = {
        ("card", card.card_id.strip())
        for card in cards
        if isinstance(card.card_id, str) and card.card_id.strip()
    }

    evidence_nodes: set[tuple[str, str]] = set()
    for item in evidence:
        ref_type = str(item.ref.type or "").strip()
        ref_id = str(item.ref.id or "").strip()
        if ref_type in {"artifact", "chunk"} and ref_id:
            evidence_nodes.add((ref_type, ref_id))
        if item.source_id:
            source_id = str(item.source_id).strip()
            if source_id:
                evidence_nodes.add(("source", source_id))

    all_nodes = card_nodes | evidence_nodes
    if not all_nodes:
        return {"signals_touched": 0, "coaccess_edges_touched": 0}

    conn = db.connect()
    for owner_type, owner_id in sorted(all_nodes):
        _upsert_signal(
            conn=conn,
            namespace=namespace,
            owner_type=owner_type,
            owner_id=owner_id,
            query_hash=query_hash,
            now_ts=timestamp,
        )

    edge_count = 0
    if card_nodes and evidence_nodes:
        for _, card_id in sorted(card_nodes):
            for evidence_type, evidence_id in sorted(evidence_nodes):
                _upsert_coaccess_edge(
                    conn=conn,
                    namespace=namespace,
                    a_type="card",
                    a_id=card_id,
                    b_type=evidence_type,
                    b_id=evidence_id,
                    now_ts=timestamp,
                )
                edge_count += 1

    conn.commit()
    conn.close()
    return {
        "signals_touched": len(all_nodes),
        "coaccess_edges_touched": edge_count,
    }

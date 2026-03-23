from __future__ import annotations

import sqlite3
from typing import Literal

from .. import db
from ..models import ConfirmCandidatesResponse, MemoryCandidate, PendingCandidate
from .policy import decide_write
from .writeback import write_candidates


def stage_candidates(
    namespace: str,
    candidates: list[MemoryCandidate],
    default_entity_id: str | None = None,
    ttl_seconds: int | None = None,
) -> tuple[list[str], list[str], list[tuple[int, str]], list[str]]:
    conn = db.connect()
    try:
        with db.transaction(conn):
            accepted_candidates: list[MemoryCandidate] = []
            pending_ids: list[str] = []
            pending_reasons: list[str] = []
            rejected: list[tuple[int, str]] = []

            for idx, candidate in enumerate(candidates):
                decision = decide_write(candidate)
                if decision.action == "accept":
                    accepted_candidates.append(candidate)
                    continue

                if decision.action == "confirm_required":
                    now_ts = db.now()
                    expires_at = now_ts + ttl_seconds if ttl_seconds is not None else None
                    pending_id = db.new_id("pend")
                    entity_id = str(candidate.entity.get("id") or default_entity_id or "unknown")
                    db.execute_one(
                        conn,
                        """
                        INSERT INTO pending_candidates
                            (id, namespace, entity_id, candidate_json, reason, status, created_at, expires_at)
                        VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                        """,
                        (
                            pending_id,
                            namespace,
                            entity_id,
                            candidate.model_dump_json(),
                            decision.reason,
                            now_ts,
                            expires_at,
                        ),
                        commit=False,
                    )
                    pending_ids.append(pending_id)
                    pending_reasons.append(decision.reason)
                    continue

                rejected.append((idx, decision.reason))

            accepted_ids: list[str] = []
            if accepted_candidates:
                accepted_ids, _ = write_candidates(
                    namespace,
                    accepted_candidates,
                    enforce_policy=False,
                    conn=conn,
                )
            return accepted_ids, pending_ids, rejected, pending_reasons
    finally:
        conn.close()


def list_pending(
    namespace: str,
    entity_id: str | None = None,
    status: str = "pending",
    limit: int = 50,
) -> list[PendingCandidate]:
    conn = db.connect()

    if status == "pending":
        db.execute_one(
            conn,
            """
            UPDATE pending_candidates
            SET status = 'expired'
            WHERE namespace = ?
              AND status = 'pending'
              AND expires_at IS NOT NULL
              AND expires_at <= ?
            """,
            (namespace, db.now()),
        )

    sql = """
        SELECT id, namespace, entity_id, candidate_json, reason, status, created_at, expires_at
        FROM pending_candidates
        WHERE namespace = ? AND status = ?
    """
    params: list[object] = [namespace, status]

    if entity_id:
        sql += " AND entity_id = ?"
        params.append(entity_id)

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = db.fetch_all(conn, sql, tuple(params))
    items: list[PendingCandidate] = []
    for row in rows:
        candidate = MemoryCandidate.model_validate_json(row["candidate_json"])
        items.append(
            PendingCandidate(
                id=row["id"],
                namespace=row["namespace"],
                entity_id=row["entity_id"],
                candidate=candidate,
                reason=row["reason"],
                status=row["status"],
                created_at=float(row["created_at"]),
                expires_at=float(row["expires_at"]) if row["expires_at"] is not None else None,
            )
        )

    conn.close()
    return items


def _record_decision(
    conn: sqlite3.Connection,
    namespace: str,
    pending_id: str,
    decision: Literal["accept", "reject"],
    decided_by: str,
    note: str | None,
    *,
    commit: bool = True,
) -> None:
    db.execute_one(
        conn,
        """
        INSERT INTO candidate_decisions (id, namespace, pending_id, decision, decided_by, note, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (db.new_id("dec"), namespace, pending_id, decision, decided_by, note, db.now()),
        commit=commit,
    )


def confirm_candidates(
    namespace: str,
    pending_ids: list[str],
    decision: Literal["accept", "reject"],
    decided_by: str,
    note: str | None = None,
) -> ConfirmCandidatesResponse:
    conn = db.connect()
    try:
        with db.transaction(conn):
            accepted_writes = 0
            rejected_count = 0
            missing_count = 0
            expired_count = 0
            accepted_ids: list[str] = []
            reasons: list[str] = []

            for pending_id in pending_ids:
                row = db.fetch_one(
                    conn,
                    """
                    SELECT id, namespace, candidate_json, expires_at
                    FROM pending_candidates
                    WHERE namespace = ? AND id = ? AND status = 'pending'
                    """,
                    (namespace, pending_id),
                )

                if not row:
                    missing_count += 1
                    reasons.append(f"missing_or_not_pending:{pending_id}")
                    continue

                now_ts = db.now()
                expires_at = float(row["expires_at"]) if row["expires_at"] is not None else None
                if expires_at is not None and expires_at <= now_ts:
                    db.execute_one(
                        conn,
                        """
                        UPDATE pending_candidates
                        SET status = 'expired'
                        WHERE namespace = ? AND id = ? AND status = 'pending'
                        """,
                        (namespace, pending_id),
                        commit=False,
                    )
                    expired_count += 1
                    reasons.append(f"expired:{pending_id}")
                    continue

                if decision == "reject":
                    db.execute_one(
                        conn,
                        """
                        UPDATE pending_candidates
                        SET status = 'rejected'
                        WHERE namespace = ? AND id = ? AND status = 'pending'
                        """,
                        (namespace, pending_id),
                        commit=False,
                    )
                    _record_decision(
                        conn,
                        namespace,
                        pending_id,
                        "reject",
                        decided_by,
                        note,
                        commit=False,
                    )
                    rejected_count += 1
                    continue

                # decision == "accept"
                try:
                    candidate = MemoryCandidate.model_validate_json(row["candidate_json"])
                except Exception as exc:  # pragma: no cover - defensive
                    db.execute_one(
                        conn,
                        """
                        UPDATE pending_candidates
                        SET status = 'rejected'
                        WHERE namespace = ? AND id = ? AND status = 'pending'
                        """,
                        (namespace, pending_id),
                        commit=False,
                    )
                    _record_decision(
                        conn,
                        namespace,
                        pending_id,
                        "accept",
                        decided_by,
                        f"{note or ''} malformed_candidate:{exc}".strip(),
                        commit=False,
                    )
                    rejected_count += 1
                    reasons.append(f"malformed_candidate:{pending_id}")
                    continue

                ids, write_reasons = write_candidates(
                    namespace,
                    [candidate],
                    enforce_policy=False,
                    conn=conn,
                )
                if ids:
                    accepted_writes += len(ids)
                    accepted_ids.extend(ids)
                    db.execute_one(
                        conn,
                        """
                        UPDATE pending_candidates
                        SET status = 'accepted'
                        WHERE namespace = ? AND id = ? AND status = 'pending'
                        """,
                        (namespace, pending_id),
                        commit=False,
                    )
                else:
                    rejected_count += 1
                    db.execute_one(
                        conn,
                        """
                        UPDATE pending_candidates
                        SET status = 'rejected'
                        WHERE namespace = ? AND id = ? AND status = 'pending'
                        """,
                        (namespace, pending_id),
                        commit=False,
                    )
                    if write_reasons:
                        reasons.extend([f"{pending_id}:{r}" for r in write_reasons])
                    else:
                        reasons.append(f"write_failed:{pending_id}")

                _record_decision(
                    conn,
                    namespace,
                    pending_id,
                    "accept",
                    decided_by,
                    note,
                    commit=False,
                )

            return ConfirmCandidatesResponse(
                namespace=namespace,
                decision=decision,
                processed=len(pending_ids),
                accepted_writes=accepted_writes,
                rejected=rejected_count,
                missing=missing_count,
                expired=expired_count,
                accepted_ids=accepted_ids,
                reasons=reasons,
            )
    finally:
        conn.close()

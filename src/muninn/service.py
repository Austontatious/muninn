from __future__ import annotations

import hashlib
import sqlite3
from contextvars import ContextVar, Token
from typing import Any

from . import db
from .logging import audit_event, audit_event_json

_AuditRow = tuple[str, str, str, str, float]
_audit_buffer: ContextVar[list[_AuditRow] | None] = ContextVar("muninn_audit_buffer", default=None)


def begin_audit_buffer() -> Token[list[_AuditRow] | None]:
    return _audit_buffer.set([])


def end_audit_buffer(token: Token[list[_AuditRow] | None]) -> None:
    _audit_buffer.reset(token)


def flush_audit_buffer(conn: sqlite3.Connection | None = None) -> int:
    buffered = _audit_buffer.get()
    if not buffered:
        return 0

    rows = list(buffered)
    buffered.clear()

    close_conn = False
    if conn is None:
        conn = db.connect()
        close_conn = True

    try:
        with db.transaction(conn):
            db.execute_many(
                conn,
                "INSERT INTO audit_log (id, namespace, event_type, event_json, created_at) VALUES (?,?,?,?,?)",
                rows,
                commit=False,
            )
    finally:
        if close_conn:
            conn.close()
    return len(rows)


def log_audit(namespace: str, event_type: str, payload: dict[str, Any]) -> str:
    ev = audit_event(event_type, payload)
    ev_json = audit_event_json(ev)
    aid = db.new_id("audit")
    row: _AuditRow = (aid, namespace, event_type, ev_json, db.now())
    buffered = _audit_buffer.get()
    if buffered is not None:
        buffered.append(row)
        return aid

    conn = db.connect()
    try:
        with db.transaction(conn):
            db.execute_one(
                conn,
                "INSERT INTO audit_log (id, namespace, event_type, event_json, created_at) VALUES (?,?,?,?,?)",
                row,
                commit=False,
            )
    finally:
        conn.close()
    return aid


def memory_version(namespace: str, profile: str, embedding_model: str | None = None) -> str:
    conn = db.connect()

    facts_max = db.fetch_one(conn, "SELECT max(created_at) AS v FROM facts WHERE namespace = ?", (namespace,))
    episodes_max = db.fetch_one(
        conn,
        "SELECT max(created_at) AS v FROM episodes WHERE namespace = ?",
        (namespace,),
    )
    prefs_max = db.fetch_one(
        conn,
        "SELECT max(created_at) AS v FROM preferences WHERE namespace = ?",
        (namespace,),
    )

    facts_count = db.fetch_one(conn, "SELECT count(*) AS n FROM facts WHERE namespace = ?", (namespace,))
    episodes_count = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM episodes WHERE namespace = ?",
        (namespace,),
    )
    prefs_count = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM preferences WHERE namespace = ?",
        (namespace,),
    )

    maxes = (
        facts_max["v"] if facts_max else None,
        episodes_max["v"] if episodes_max else None,
        prefs_max["v"] if prefs_max else None,
    )
    counts = (
        facts_count["n"] if facts_count else 0,
        episodes_count["n"] if episodes_count else 0,
        prefs_count["n"] if prefs_count else 0,
    )
    raw = f"{namespace}|{profile}|{maxes}|{counts}"

    if embedding_model:
        emb_max = db.fetch_one(
            conn,
            "SELECT max(updated_at) AS v FROM embeddings WHERE namespace = ? AND model = ?",
            (namespace, embedding_model),
        )
        emb_count = db.fetch_one(
            conn,
            "SELECT count(*) AS n FROM embeddings WHERE namespace = ? AND model = ?",
            (namespace, embedding_model),
        )
        emb_sig = (
            embedding_model,
            emb_max["v"] if emb_max else None,
            emb_count["n"] if emb_count else 0,
        )
        raw = f"{raw}|{emb_sig}"

    conn.close()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

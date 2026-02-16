from __future__ import annotations

import hashlib

from . import db
from .logging import audit_event, audit_event_json


def log_audit(event_type: str, payload: dict) -> None:
    conn = db.connect()
    ev = audit_event(event_type, payload)
    ev_json = audit_event_json(ev)
    aid = db.new_id("audit")
    db.execute_one(
        conn,
        "INSERT INTO audit_log (id, event_type, event_json, created_at) VALUES (?,?,?,?)",
        (aid, event_type, ev_json, db.now()),
    )


def memory_version(namespace: str, profile: str, embedding_model: str | None = None) -> str:
    conn = db.connect()

    facts_max = db.fetch_one(conn, "SELECT max(created_at) AS v FROM facts")
    episodes_max = db.fetch_one(conn, "SELECT max(created_at) AS v FROM episodes")
    prefs_max = db.fetch_one(conn, "SELECT max(created_at) AS v FROM preferences")

    facts_count = db.fetch_one(conn, "SELECT count(*) AS n FROM facts")
    episodes_count = db.fetch_one(conn, "SELECT count(*) AS n FROM episodes")
    prefs_count = db.fetch_one(conn, "SELECT count(*) AS n FROM preferences")

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
            "SELECT max(updated_at) AS v FROM embeddings WHERE model = ?",
            (embedding_model,),
        )
        emb_count = db.fetch_one(
            conn,
            "SELECT count(*) AS n FROM embeddings WHERE model = ?",
            (embedding_model,),
        )
        emb_sig = (
            embedding_model,
            emb_max["v"] if emb_max else None,
            emb_count["n"] if emb_count else 0,
        )
        raw = f"{raw}|{emb_sig}"

    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

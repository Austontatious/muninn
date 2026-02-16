from __future__ import annotations

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

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_admin_cleanup_dry_run_and_delete(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.delenv("MUNINN_READONLY", raising=False)

    conn = db.connect()
    db.init_db(conn)

    now_ts = db.now()
    old_ts = now_ts - (10 * 24 * 60 * 60)

    pending_accepted = db.new_id("pend")
    pending_rejected = db.new_id("pend")
    pending_still_pending = db.new_id("pend")

    for pid, status in [
        (pending_accepted, "accepted"),
        (pending_rejected, "rejected"),
        (pending_still_pending, "pending"),
    ]:
        db.execute_one(
            conn,
            """
            INSERT INTO pending_candidates
              (id, namespace, entity_id, candidate_json, reason, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pid,
                "default",
                "ent_user",
                '{"kind":"preference","entity":{"id":"ent_user"},"payload":{"key":"k","value":"v"},"confidence":0.9,"provenance":{"source_type":"user"}}',
                "test",
                status,
                old_ts,
                None,
            ),
        )

    db.execute_one(
        conn,
        """
        INSERT INTO candidate_decisions (id, namespace, pending_id, decision, decided_by, note, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (db.new_id("dec"), "default", pending_accepted, "accept", "user:test", None, old_ts),
    )
    db.execute_one(
        conn,
        """
        INSERT INTO candidate_decisions (id, namespace, pending_id, decision, decided_by, note, decided_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (db.new_id("dec"), "default", pending_accepted, "accept", "user:test", None, old_ts),
    )
    db.execute_one(
        conn,
        """
        INSERT INTO audit_log (id, namespace, event_type, event_json, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (db.new_id("audit"), "default", "test", "{}", old_ts),
    )

    client = TestClient(app)

    dry_run = client.post(
        "/v0/admin/cleanup",
        json={
            "namespace": "default",
            "targets": ["pending", "decisions", "audit"],
            "older_than_seconds": 3600,
            "limit": 100,
            "dry_run": True,
        },
    )
    assert dry_run.status_code == 200
    dry_body = dry_run.json()
    assert dry_body["deleted_pending"] == 0
    assert dry_body["deleted_decisions"] == 0
    assert dry_body["deleted_audit"] == 0
    assert dry_body["scanned"] >= 1

    live = client.post(
        "/v0/admin/cleanup",
        json={
            "namespace": "default",
            "targets": ["pending", "decisions", "audit"],
            "older_than_seconds": 3600,
            "limit": 100,
            "dry_run": False,
        },
    )
    assert live.status_code == 200
    body = live.json()
    assert body["deleted_pending"] == 2
    assert body["deleted_decisions"] >= 1
    assert body["deleted_audit"] == 0
    assert "audit_append_only" in body["reasons"]

    remaining_pending = db.fetch_one(
        conn,
        "SELECT status FROM pending_candidates WHERE namespace = ? AND id = ?",
        ("default", pending_still_pending),
    )
    assert remaining_pending is not None
    assert remaining_pending["status"] == "pending"

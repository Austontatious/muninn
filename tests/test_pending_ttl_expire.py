from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_pending_ttl_zero_expires_before_confirm(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    stage = client.post(
        "/v0/memory/stage_candidates",
        json={
            "namespace": "default",
            "ttl_seconds": 0,
            "candidates": [
                {
                    "kind": "preference",
                    "entity": {"id": "ent_user", "kind": "user", "name": "Auston"},
                    "payload": {"key": "health.note", "value": "x"},
                    "confidence": 0.9,
                    "provenance": {"source_type": "user", "source_id": "turn_ttl"},
                }
            ],
        },
    )
    pending_id = stage.json()["pending_ids"][0]

    confirm = client.post(
        "/v0/memory/confirm_candidates",
        json={
            "namespace": "default",
            "pending_ids": [pending_id],
            "decision": "accept",
            "decided_by": "user:test",
        },
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["processed"] == 1
    assert body["accepted_writes"] == 0
    assert body["expired"] == 1

    pending = db.fetch_one(
        conn,
        "SELECT status FROM pending_candidates WHERE namespace = ? AND id = ?",
        ("default", pending_id),
    )
    assert pending is not None
    assert pending["status"] == "expired"

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_confirm_reject_does_not_write_candidate(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    stage = client.post(
        "/v0/memory/stage_candidates",
        json={
            "namespace": "default",
            "candidates": [
                {
                    "kind": "preference",
                    "entity": {"id": "ent_user", "kind": "user", "name": "Auston"},
                    "payload": {"key": "health.note", "value": "x"},
                    "confidence": 0.9,
                    "provenance": {"source_type": "user", "source_id": "turn_reject"},
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
            "decision": "reject",
            "decided_by": "user:test",
        },
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["processed"] == 1
    assert body["accepted_writes"] == 0
    assert body["rejected"] == 1

    pref = db.fetch_one(
        conn,
        "SELECT id FROM preferences WHERE namespace = ? AND entity_id = ? AND key = ?",
        ("default", "ent_user", "health.note"),
    )
    assert pref is None

    pending = db.fetch_one(
        conn,
        "SELECT status FROM pending_candidates WHERE namespace = ? AND id = ?",
        ("default", pending_id),
    )
    assert pending is not None
    assert pending["status"] == "rejected"

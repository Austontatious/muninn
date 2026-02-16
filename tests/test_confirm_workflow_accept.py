from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_confirm_accept_writes_pending_candidate(tmp_path, monkeypatch) -> None:
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
                    "provenance": {"source_type": "user", "source_id": "turn_accept"},
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
            "note": "approved",
        },
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["processed"] == 1
    assert body["accepted_writes"] == 1
    assert body["rejected"] == 0
    assert body["missing"] == 0
    assert body["expired"] == 0
    assert len(body["accepted_ids"]) == 1

    row = db.fetch_one(
        conn,
        """
        SELECT id, value
        FROM preferences
        WHERE namespace = ? AND entity_id = ? AND key = ?
        """,
        ("default", "ent_user", "health.note"),
    )
    assert row is not None
    assert row["value"] == "x"

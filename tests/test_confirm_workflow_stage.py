from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_stage_sensitive_candidate_creates_pending(tmp_path, monkeypatch) -> None:
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
                    "provenance": {"source_type": "user", "source_id": "turn_stage"},
                }
            ],
        },
    )
    assert stage.status_code == 200
    body = stage.json()
    assert body["accepted"] == 0
    assert body["pending"] == 1
    assert body["rejected"] == 0
    assert len(body["pending_ids"]) == 1

    pending = client.post(
        "/v0/memory/list_pending",
        json={"namespace": "default", "status": "pending", "limit": 10},
    )
    assert pending.status_code == 200
    items = pending.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == body["pending_ids"][0]
    assert "CONFIRM_REQUIRED" in items[0]["reason"]


def test_stage_benign_candidate_auto_writes(tmp_path, monkeypatch) -> None:
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
                    "payload": {"key": "style.response", "value": "direct"},
                    "confidence": 0.9,
                    "provenance": {"source_type": "user", "source_id": "turn_stage_benign"},
                }
            ],
        },
    )
    assert stage.status_code == 200
    body = stage.json()
    assert body["accepted"] == 1
    assert body["pending"] == 0
    assert len(body["accepted_ids"]) == 1

    row = db.fetch_one(
        conn,
        """
        SELECT id, value
        FROM preferences
        WHERE namespace = ? AND entity_id = ? AND key = ?
        """,
        ("default", "ent_user", "style.response"),
    )
    assert row is not None
    assert row["value"] == "direct"

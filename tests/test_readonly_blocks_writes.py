from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_readonly_blocks_writes_but_keeps_reads(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_READONLY", "1")
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)

    write_resp = client.post(
        "/v0/memory/write_candidates",
        json={
            "namespace": "default",
            "candidates": [
                {
                    "kind": "preference",
                    "entity": {"id": "ent_user", "kind": "user", "name": "Auston"},
                    "payload": {"key": "style.response", "value": "direct"},
                    "confidence": 0.9,
                    "provenance": {"source_type": "user", "source_id": "readonly_write"},
                }
            ],
        },
    )
    assert write_resp.status_code == 503

    stage_resp = client.post(
        "/v0/memory/stage_candidates",
        json={
            "namespace": "default",
            "candidates": [
                {
                    "kind": "preference",
                    "entity": {"id": "ent_user", "kind": "user", "name": "Auston"},
                    "payload": {"key": "health.note", "value": "x"},
                    "confidence": 0.9,
                    "provenance": {"source_type": "user", "source_id": "readonly_stage"},
                }
            ],
        },
    )
    assert stage_resp.status_code == 503

    upsert_resp = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": "fact_fake",
                    "kind": "fact",
                    "entity_id": "ent_user",
                    "model": "test-model",
                    "vector": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                }
            ],
        },
    )
    assert upsert_resp.status_code == 503

    assert client.get("/health").status_code == 200
    assert client.get("/v0/memory/version").status_code == 200
    assert client.get("/v0/debug/vector_backend").status_code == 200

    retrieve_resp = client.post(
        "/v0/memory/retrieve",
        json={
            "namespace": "default",
            "query": "hello",
            "entity_id": "ent_user",
            "k": 5,
        },
    )
    assert retrieve_resp.status_code == 200

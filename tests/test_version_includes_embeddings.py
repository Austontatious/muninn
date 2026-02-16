from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_version_changes_when_embedding_model_state_changes(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "vector-test"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id="turn_1"),
    )
    ids, _ = write_candidates("default", [candidate])

    client = TestClient(app)
    before = client.get(
        "/v0/memory/version",
        params={"namespace": "default", "profile": "generic", "embedding_model": "test-model-v1"},
    )
    assert before.status_code == 200
    v1 = before.json()["version"]

    upsert = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": ids[0],
                    "kind": "fact",
                    "entity_id": "ent_user",
                    "model": "test-model-v1",
                    "vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                }
            ],
        },
    )
    assert upsert.status_code == 200
    assert upsert.json()["upserted"] == 1

    after = client.get(
        "/v0/memory/version",
        params={"namespace": "default", "profile": "generic", "embedding_model": "test-model-v1"},
    )
    assert after.status_code == 200
    v2 = after.json()["version"]

    assert v2 != v1

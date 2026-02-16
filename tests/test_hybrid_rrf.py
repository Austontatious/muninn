from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance, UpsertEmbeddingsItem
from muninn.vector import store as vector_store


def test_hybrid_rrf_includes_fts_and_vector_hits(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_RETRIEVAL_MODE", "hybrid")
    monkeypatch.setenv("MUNINN_RRF_K0", "60")

    conn = db.connect()
    db.init_db(conn)

    item_a = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "alpha"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id="turn_a"),
    )
    item_b = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "bravo"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id="turn_b"),
    )

    id_a, _ = write_candidates("default", [item_a])
    id_b, _ = write_candidates("default", [item_b])

    upserted, rejected, _ = vector_store.upsert_embeddings(
        namespace="default",
        items=[
            UpsertEmbeddingsItem(
                item_id=id_a[0],
                kind="fact",
                entity_id="ent_user",
                model="test-model-v1",
                vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ),
            UpsertEmbeddingsItem(
                item_id=id_b[0],
                kind="fact",
                entity_id="ent_user",
                model="test-model-v1",
                vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ),
        ],
    )
    assert upserted == 2
    assert rejected == 0

    client = TestClient(app)
    response = client.post(
        "/v0/memory/retrieve",
        json={
            "namespace": "default",
            "query": "alpha",
            "entity_id": "ent_user",
            "k": 5,
            "embedding_model": "test-model-v1",
            "query_embedding": [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        },
    )
    assert response.status_code == 200

    ids = [item["id"] for item in response.json()["items"]]
    assert id_a[0] in ids[:2]
    assert id_b[0] in ids[:2]

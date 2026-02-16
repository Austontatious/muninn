import pytest
from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_admin_reindex_vectors_sqlite_vec_path(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_VEC_BACKEND", "sqlite_vec")

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    debug = client.get("/v0/debug/vector_backend")
    assert debug.status_code == 200
    if not debug.json()["sqlite_vec_loaded"]:
        pytest.skip("sqlite-vec not available")

    fact = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "alpha"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="reindex_1"),
    )
    ids, _ = write_candidates("default", [fact])

    upsert = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": ids[0],
                    "kind": "fact",
                    "entity_id": "ent_user",
                    "model": "reindex-model",
                    "vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                }
            ],
        },
    )
    assert upsert.status_code == 200
    assert upsert.json()["upserted"] == 1

    reindex = client.post(
        "/v0/admin/reindex_vectors",
        json={
            "namespace": "default",
            "model": "reindex-model",
            "force_backend": "sqlite_vec",
        },
    )
    assert reindex.status_code == 200
    body = reindex.json()
    assert body["backend_used"] == "sqlite_vec"
    assert body["reindexed"] >= 1

    query = client.post(
        "/v0/memory/query_vector",
        json={
            "namespace": "default",
            "model": "reindex-model",
            "query_vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "entity_id": "ent_user",
            "k": 3,
        },
    )
    assert query.status_code == 200
    hits = query.json()["hits"]
    assert hits
    assert hits[0]["item_id"] == ids[0]

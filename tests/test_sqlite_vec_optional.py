import pytest
from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def _seed_fact() -> str:
    candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "alpha"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="sqlite_vec_test"),
    )
    ids, _ = write_candidates("default", [candidate])
    return ids[0]


def test_sqlite_vec_optional_acceleration_if_available(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_VEC_BACKEND", "auto")
    monkeypatch.delenv("MUNINN_SQLITE_VEC_ENABLED", raising=False)

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    debug = client.get("/v0/debug/vector_backend")
    assert debug.status_code == 200
    info = debug.json()

    if not info["sqlite_vec_loaded"]:
        pytest.skip("sqlite-vec not available")

    monkeypatch.setenv("MUNINN_VEC_BACKEND", "sqlite_vec")
    debug2 = client.get("/v0/debug/vector_backend")
    assert debug2.status_code == 200
    assert debug2.json()["effective_backend"] == "sqlite_vec"

    item_id = _seed_fact()

    upsert = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": item_id,
                    "kind": "fact",
                    "entity_id": "ent_user",
                    "model": "sqlite-vec-test-model",
                    "vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                }
            ],
        },
    )
    assert upsert.status_code == 200
    assert upsert.json()["upserted"] == 1

    query = client.post(
        "/v0/memory/query_vector",
        json={
            "namespace": "default",
            "model": "sqlite-vec-test-model",
            "query_vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "entity_id": "ent_user",
            "k": 3,
        },
    )
    assert query.status_code == 200
    hits = query.json()["hits"]
    assert hits
    assert hits[0]["item_id"] == item_id


def test_sqlite_vec_forced_config_falls_back_to_bruteforce(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_VEC_BACKEND", "sqlite_vec")
    monkeypatch.setenv("MUNINN_SQLITE_VEC_ENABLED", "0")

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    debug = client.get("/v0/debug/vector_backend")
    assert debug.status_code == 200
    info = debug.json()
    assert info["vec_backend_config"] == "sqlite_vec"
    assert info["effective_backend"] == "bruteforce"

    item_id = _seed_fact()

    upsert = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": item_id,
                    "kind": "fact",
                    "entity_id": "ent_user",
                    "model": "fallback-model",
                    "vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                }
            ],
        },
    )
    assert upsert.status_code == 200
    assert upsert.json()["upserted"] == 1

    query = client.post(
        "/v0/memory/query_vector",
        json={
            "namespace": "default",
            "model": "fallback-model",
            "query_vector": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            "entity_id": "ent_user",
            "k": 3,
        },
    )
    assert query.status_code == 200
    hits = query.json()["hits"]
    assert hits
    assert hits[0]["item_id"] == item_id

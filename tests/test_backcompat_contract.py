from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _candidate(value: str, source_id: str, *, key: str = "style.response") -> dict:
    return {
        "kind": "preference",
        "entity": {"id": "ent_user", "kind": "user", "name": "Backcompat User"},
        "payload": {"key": key, "value": value},
        "confidence": 0.9,
        "provenance": {"source_type": "user", "source_id": source_id},
    }


def test_v0_memory_endpoints_return_stable_contract_shapes(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)

    write_resp = client.post(
        "/v0/memory/write_candidates",
        json={
            "namespace": "default",
            "candidates": [_candidate("direct", "backcompat_write")],
        },
    )
    assert write_resp.status_code == 200
    write_body = write_resp.json()
    assert {"accepted", "rejected", "ids", "reasons"}.issubset(write_body.keys())
    assert isinstance(write_body["ids"], list)

    stage_resp = client.post(
        "/v0/memory/stage_candidates",
        json={
            "namespace": "default",
            "candidates": [
                _candidate("private", "backcompat_stage", key="health.note"),
            ],
        },
    )
    assert stage_resp.status_code == 200
    stage_body = stage_resp.json()
    assert {
        "accepted",
        "pending",
        "rejected",
        "accepted_ids",
        "pending_ids",
        "reject_reasons",
        "pending_reasons",
    }.issubset(stage_body.keys())
    assert len(stage_body["pending_ids"]) == 1
    pending_id = stage_body["pending_ids"][0]

    list_resp = client.post(
        "/v0/memory/list_pending",
        json={"namespace": "default", "status": "pending", "limit": 10},
    )
    assert list_resp.status_code == 200
    list_body = list_resp.json()
    assert {"items"}.issubset(list_body.keys())
    assert isinstance(list_body["items"], list)
    assert any(item.get("id") == pending_id for item in list_body["items"])

    confirm_resp = client.post(
        "/v0/memory/confirm_candidates",
        json={
            "namespace": "default",
            "pending_ids": [pending_id],
            "decision": "reject",
            "decided_by": "user:test_backcompat",
        },
    )
    assert confirm_resp.status_code == 200
    confirm_body = confirm_resp.json()
    assert {
        "namespace",
        "decision",
        "processed",
        "accepted_writes",
        "rejected",
        "missing",
        "expired",
        "accepted_ids",
        "reasons",
    }.issubset(confirm_body.keys())

    retrieve_resp = client.post(
        "/v0/memory/retrieve",
        json={"namespace": "default", "query": "direct", "k": 5},
    )
    assert retrieve_resp.status_code == 200
    retrieve_body = retrieve_resp.json()
    assert {"items"}.issubset(retrieve_body.keys())
    assert isinstance(retrieve_body["items"], list)
    assert len(retrieve_body["items"]) >= 1
    first_item = retrieve_body["items"][0]
    assert {"kind", "id", "entity_id", "text", "confidence", "provenance"}.issubset(
        first_item.keys()
    )
    assert {"source_type", "source_id", "note", "ts"}.issubset(first_item["provenance"].keys())

    render_resp = client.post(
        "/v0/memory/render_cards",
        json={"namespace": "default", "items": retrieve_body["items"], "profile": "generic"},
    )
    assert render_resp.status_code == 200
    render_body = render_resp.json()
    assert {"cards"}.issubset(render_body.keys())
    assert isinstance(render_body["cards"], list)

    rehydrate_resp = client.post(
        "/v0/memory/rehydrate",
        json={"namespace": "default", "query": "direct", "k": 5, "profile": "generic"},
    )
    assert rehydrate_resp.status_code == 200
    rehydrate_body = rehydrate_resp.json()
    assert {"cards", "items"}.issubset(rehydrate_body.keys())
    assert isinstance(rehydrate_body["cards"], list)
    assert isinstance(rehydrate_body["items"], list)

    version_resp = client.get("/v0/memory/version", params={"namespace": "default", "profile": "generic"})
    assert version_resp.status_code == 200
    version_body = version_resp.json()
    assert {"namespace", "profile", "embedding_model", "version"}.issubset(version_body.keys())
    assert isinstance(version_body["version"], str)

    upsert_resp = client.post(
        "/v0/memory/upsert_embeddings",
        json={
            "namespace": "default",
            "items": [
                {
                    "item_id": write_body["ids"][0],
                    "kind": "preference",
                    "entity_id": "ent_user",
                    "model": "test-model-v1",
                    "vector": [0.1, 0.2, 0.3],
                }
            ],
        },
    )
    assert upsert_resp.status_code == 200
    upsert_body = upsert_resp.json()
    assert {"upserted", "rejected", "reasons"}.issubset(upsert_body.keys())

    query_resp = client.post(
        "/v0/memory/query_vector",
        json={
            "namespace": "default",
            "model": "test-model-v1",
            "query_vector": [0.1, 0.2, 0.3],
            "k": 3,
        },
    )
    assert query_resp.status_code == 200
    query_body = query_resp.json()
    assert {"hits"}.issubset(query_body.keys())
    assert isinstance(query_body["hits"], list)
    if query_body["hits"]:
        assert {"item_id", "kind", "entity_id", "score"}.issubset(query_body["hits"][0].keys())

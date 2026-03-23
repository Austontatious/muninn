from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _fact_candidate(obj: str) -> dict:
    return {
        "kind": "fact",
        "entity": {"id": "ent_user", "kind": "user", "name": "Auston"},
        "payload": {"predicate": "topic", "object": obj},
        "confidence": 0.9,
        "provenance": {"source_type": "user", "source_id": f"seed_{obj}"},
    }


def _setup_auth_namespaces(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "1")
    monkeypatch.setenv("MUNINN_API_KEYS", "keyA:nsA,keyB:nsB")
    monkeypatch.delenv("MUNINN_API_KEY", raising=False)
    monkeypatch.delenv("MUNINN_NAMESPACE", raising=False)
    monkeypatch.delenv("MUNINN_DEFAULT_NAMESPACE", raising=False)

    conn = db.connect()
    db.init_db(conn)
    conn.close()


def test_namespace_override_is_rejected(tmp_path, monkeypatch) -> None:
    _setup_auth_namespaces(tmp_path, monkeypatch)
    client = TestClient(app)

    response = client.get(
        "/v0/memory/version",
        headers=_auth_headers("keyA"),
        params={"namespace": "nsB"},
    )
    assert response.status_code == 403


def test_same_identifier_isolated_by_server_namespace(tmp_path, monkeypatch) -> None:
    _setup_auth_namespaces(tmp_path, monkeypatch)
    client = TestClient(app)

    write_a = client.post(
        "/v0/memory/write_candidates",
        headers=_auth_headers("keyA"),
        json={"candidates": [_fact_candidate("alpha")]},
    )
    assert write_a.status_code == 200

    write_b = client.post(
        "/v0/memory/write_candidates",
        headers=_auth_headers("keyB"),
        json={"candidates": [_fact_candidate("beta")]},
    )
    assert write_b.status_code == 200

    read_a = client.post(
        "/v0/memory/retrieve",
        headers=_auth_headers("keyA"),
        json={"query": "alpha", "entity_id": "ent_user", "k": 8},
    )
    assert read_a.status_code == 200
    texts_a = [item["text"] for item in read_a.json()["items"]]
    assert any("alpha" in text for text in texts_a)
    assert all("beta" not in text for text in texts_a)

    read_b = client.post(
        "/v0/memory/retrieve",
        headers=_auth_headers("keyB"),
        json={"query": "beta", "entity_id": "ent_user", "k": 8},
    )
    assert read_b.status_code == 200
    texts_b = [item["text"] for item in read_b.json()["items"]]
    assert any("beta" in text for text in texts_b)
    assert all("alpha" not in text for text in texts_b)


def test_index_jobs_are_written_with_resolved_namespace(tmp_path, monkeypatch) -> None:
    _setup_auth_namespaces(tmp_path, monkeypatch)
    client = TestClient(app)

    created = client.post(
        "/cards",
        headers=_auth_headers("keyA"),
        json={
            "type": "fact",
            "title": "Namespace isolated card",
            "summary": "Card belongs to nsA",
            "trusted_mode": True,
        },
    )
    assert created.status_code == 200
    card_id = created.json()["card_id"]

    conn = db.connect()
    job = db.fetch_one(
        conn,
        """
        SELECT namespace, status
        FROM index_jobs
        WHERE owner_type = 'card'
          AND owner_id = ?
          AND modality = 'text'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (card_id,),
    )
    conn.close()
    assert job is not None
    assert str(job["namespace"]) == "nsA"
    assert str(job["status"]) == "pending"

    foreign_read = client.get(f"/cards/{card_id}", headers=_auth_headers("keyB"))
    assert foreign_read.status_code == 404


def test_unauthed_mode_ignores_namespace_override_by_default(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.delenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", raising=False)

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)
    response = client.get("/v0/memory/version", params={"namespace": "nsB"})
    assert response.status_code == 200
    assert response.json()["namespace"] == "default"


def test_unauthed_mode_can_allow_namespace_override_with_flag(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.setenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", "1")

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)
    response = client.get("/v0/memory/version", params={"namespace": "nsB"})
    assert response.status_code == 200
    assert response.json()["namespace"] == "nsB"

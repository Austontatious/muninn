from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.cardex import embeddings, index_jobs


def _init_client(tmp_path, monkeypatch) -> TestClient:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.setenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", "1")
    conn = db.connect()
    db.init_db(conn)
    conn.close()
    return TestClient(app)


def _create_active_card(client: TestClient, namespace: str, title: str, summary: str) -> str:
    response = client.post(
        "/cards",
        json={
            "namespace": namespace,
            "type": "fact",
            "title": title,
            "summary": summary,
            "trusted_mode": True,
        },
    )
    assert response.status_code == 200
    return str(response.json()["card_id"])


def test_index_worker_builds_embeddings_and_vector_search_is_queryable(tmp_path, monkeypatch) -> None:
    client = _init_client(tmp_path, monkeypatch)
    card_a = _create_active_card(
        client,
        namespace="default",
        title="TRT clinic growth plan",
        summary="TRT clinic expansion model patient acquisition velocity",
    )
    _create_active_card(
        client,
        namespace="default",
        title="Groceries",
        summary="grocery list bananas eggs",
    )

    result = index_jobs.process_pending_index_jobs(limit=20, namespace="default")
    assert result["done"] >= 2
    assert result["failed"] == 0

    conn = db.connect()
    rows = db.fetch_all(
        conn,
        """
        SELECT owner_id, embed_status, model
        FROM card_embeddings
        WHERE namespace = ?
          AND owner_type = 'card'
          AND modality = 'text'
        """,
        ("default",),
    )
    conn.close()
    by_owner = {str(row["owner_id"]): (str(row["embed_status"]), str(row["model"])) for row in rows}
    assert card_a in by_owner
    assert by_owner[card_a][0] == "ready"
    assert by_owner[card_a][1] == embeddings.default_card_embedding_model()

    response = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "patient acquisition velocity",
            "scope": ["cards"],
            "k_cards": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cards"][0]["card_id"] == card_a
    assert int(body["notes"]["candidate_counts"]["vec"]) >= 1
    assert str(body["notes"]["model"]) == embeddings.default_card_embedding_model()


def test_cardex_retrieval_is_namespace_clean_for_vector_and_lexical(tmp_path, monkeypatch) -> None:
    client = _init_client(tmp_path, monkeypatch)
    card_a = _create_active_card(
        client,
        namespace="nsA",
        title="Namespace A card",
        summary="TRT clinic expansion model patient acquisition velocity",
    )
    card_b = _create_active_card(
        client,
        namespace="nsB",
        title="Namespace B card",
        summary="TRT clinic expansion model patient acquisition velocity",
    )

    result = index_jobs.process_pending_index_jobs(limit=20)
    assert result["done"] >= 2
    assert result["failed"] == 0

    response = client.post(
        "/retrieve",
        json={
            "namespace": "nsA",
            "query": "patient acquisition velocity",
            "scope": ["cards"],
            "k_cards": 10,
        },
    )
    assert response.status_code == 200
    ids = [str(card["card_id"]) for card in response.json()["cards"]]
    assert card_a in ids
    assert card_b not in ids


def test_hybrid_ranking_can_outrank_lexical_trap(tmp_path, monkeypatch) -> None:
    client = _init_client(tmp_path, monkeypatch)
    card_a = _create_active_card(
        client,
        namespace="default",
        title="Clinic strategy",
        summary="clinic growth strategy playbook for patient care pipeline",
    )
    card_b = _create_active_card(
        client,
        namespace="default",
        title="Warehouse report",
        summary="grocery acquisition velocity model for warehouse logistics",
    )

    result = index_jobs.process_pending_index_jobs(limit=20, namespace="default")
    assert result["done"] >= 2
    assert result["failed"] == 0

    response = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "patient acquisition velocity model",
            "scope": ["cards"],
            "k_cards": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["cards"]) >= 2
    lexical_top = [str(card_id) for card_id in body["notes"]["top_ids"]["lexical"]]
    assert lexical_top[0] == card_b
    assert card_a in lexical_top
    assert body["cards"][0]["card_id"] == card_a

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _seed_card_with_source(client: TestClient, namespace: str, title: str, source_text: str) -> tuple[str, str]:
    source_resp = client.post(
        "/sources",
        json={
            "namespace": namespace,
            "source_type": "note",
            "uri": f"local://{title}",
            "title": f"{title} source",
            "artifacts": [{"artifact_type": "summary", "content_text": source_text}],
        },
    )
    assert source_resp.status_code == 200
    source_id = source_resp.json()["source"]["source_id"]

    card_resp = client.post(
        "/cards",
        json={
            "namespace": namespace,
            "type": "place",
            "title": title,
            "summary": f"Summary for {title}",
            "trusted_mode": True,
        },
    )
    assert card_resp.status_code == 200
    card_id = card_resp.json()["card_id"]

    ref_resp = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": namespace,
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
        },
    )
    assert ref_resp.status_code == 200
    return card_id, source_id


def test_retrieve_returns_cards_and_evidence(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    text = (FIXTURES / "bowie_belize_article.txt").read_text(encoding="utf-8")
    card_id, source_id = _seed_card_with_source(
        client,
        namespace="default",
        title="Bowie Belize restaurant",
        source_text=text,
    )

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "restaurant in Belize David Bowie mentioned",
            "scope": ["cards", "evidence"],
            "k_cards": 10,
            "k_evidence": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["audit_id"].startswith("audit_")
    assert any(card["card_id"] == card_id for card in body["cards"])
    assert any(ev.get("source_id") == source_id for ev in body["evidence"])


def test_retrieve_response_contract_shape_is_stable(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)
    _seed_card_with_source(
        client,
        namespace="default",
        title="Contract shape card",
        source_text="A concise evidence snippet about Belize and Bowie.",
    )

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Belize Bowie",
            "scope": ["cards", "evidence"],
            "k_cards": 10,
            "k_evidence": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert {"cards", "evidence", "audit_id", "redactions", "notes"}.issubset(body.keys())
    assert isinstance(body["cards"], list)
    assert isinstance(body["evidence"], list)
    assert isinstance(body["redactions"], list)
    assert isinstance(body["notes"], dict)
    assert len(body["evidence"]) >= 1

    for evidence in body["evidence"]:
        assert {"ref", "snippet", "blocked", "blocked_reason"}.issubset(evidence.keys())
        assert isinstance(evidence["snippet"], str)
        assert isinstance(evidence["blocked"], bool)
        assert isinstance(evidence["ref"], dict)
        assert {"type", "id"}.issubset(evidence["ref"].keys())



def test_retrieve_prioritizes_card_index(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    for idx in range(30):
        r = client.post(
            "/sources",
            json={
                "namespace": "default",
                "source_type": "note",
                "uri": f"local://noise/{idx}",
                "title": f"Noise {idx}",
                "artifacts": [{"artifact_type": "summary", "content_text": f"irrelevant text {idx}"}],
            },
        )
        assert r.status_code == 200

    card_id, source_id = _seed_card_with_source(
        client,
        namespace="default",
        title="Belize Bowie anchor card",
        source_text="Evidence text about Bowie mentioning a Belize restaurant.",
    )

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Bowie Belize restaurant",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    returned_ids = {card["card_id"] for card in body["cards"]}
    assert card_id in returned_ids
    assert len(body["evidence"]) >= 1
    assert body["evidence"][0].get("source_id") == source_id
    assert "cards" in body["notes"].get("searched", [])



def test_retrieve_fallback_without_cards(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    recipe_text = (FIXTURES / "recipes_belize.md").read_text(encoding="utf-8")

    src = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "document",
            "uri": "local://recipes/belize",
            "title": "Belize recipes",
            "artifacts": [{"artifact_type": "summary", "content_text": recipe_text}],
        },
    )
    assert src.status_code == 200

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Belize Fry Jack ingredients",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 3,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cards"] == []
    assert len(body["evidence"]) >= 1
    assert body["notes"]["fallback"] == "artifact_search"

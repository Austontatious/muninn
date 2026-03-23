from __future__ import annotations

import json

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_ingest_is_deterministic_for_same_text(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    payload = {
        "namespace": "default",
        "source_type": "document",
        "uri": "https://example.test/bowie",
        "title": "Bowie Belize",
        "text": "# Heading\n\nDavid Bowie mentioned Belize restaurants in travel writing.",
        "user_tags": ["bowie", "belize"],
        "chunk_target_tokens": 120,
        "chunk_overlap_tokens": 20,
    }

    first = client.post("/ingest", json=payload)
    second = client.post("/ingest", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    a = first.json()
    b = second.json()

    assert a["source"]["source_id"] == b["source"]["source_id"]
    assert a["doc_id"] == b["doc_id"]
    assert a["chunk_ids"] == b["chunk_ids"]
    assert a["artifact_ids"] == b["artifact_ids"]
    assert "extracted_text" in a["artifact_types"]

    row = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM sources WHERE namespace = ? AND source_id = ?",
        ("default", a["source"]["source_id"]),
    )
    assert row is not None
    assert int(row["n"]) == 1



def test_ingest_web_stub_creates_pending_extracted_text_artifact(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    resp = client.post(
        "/ingest",
        json={
            "namespace": "default",
            "source_type": "web",
            "uri": "https://example.test/future-fetch",
            "title": "Future fetch",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "extracted_text" in body["artifact_types"]

    artifact_row = db.fetch_one(
        conn,
        "SELECT content_json FROM artifacts WHERE namespace = ? AND source_id = ? AND artifact_type = ?",
        ("default", body["source"]["source_id"], "extracted_text"),
    )
    assert artifact_row is not None
    payload = json.loads(str(artifact_row["content_json"]))
    assert payload["status"] == "pending"



def test_ingest_media_stub_creates_pending_modal_artifacts(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    resp = client.post(
        "/ingest",
        json={
            "namespace": "default",
            "source_type": "image",
            "uri": "placeholder://image/1",
            "title": "Belize market photo",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["artifact_types"]) == {"caption", "ocr", "objects"}



def test_ingest_card_mode_trusted_creates_card_and_refs(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    resp = client.post(
        "/ingest",
        json={
            "namespace": "default",
            "source_type": "note",
            "title": "Belize note",
            "text": "Belize restaurant mention with Bowie reference.",
            "card_mode": "trusted",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["card_id"] is not None

    card_row = db.fetch_one(
        conn,
        "SELECT card_id FROM cards WHERE namespace = ? AND card_id = ?",
        ("default", body["card_id"]),
    )
    assert card_row is not None

    ref_rows = db.fetch_all(
        conn,
        "SELECT ref_type FROM card_refs WHERE namespace = ? AND card_id = ?",
        ("default", body["card_id"]),
    )
    ref_types = {str(row["ref_type"]) for row in ref_rows}
    assert "source" in ref_types
    assert "doc" in ref_types



def test_ingest_retrieve_without_card_uses_artifact_search(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    ingest = client.post(
        "/ingest",
        json={
            "namespace": "default",
            "source_type": "document",
            "title": "Belize recipe",
            "text": "Fry Jack ingredients include flour and baking powder.",
        },
    )
    assert ingest.status_code == 200
    source_id = ingest.json()["source"]["source_id"]

    retrieve = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Fry Jack ingredients",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 3,
        },
    )
    assert retrieve.status_code == 200
    body = retrieve.json()
    assert body["cards"] == []
    assert any(ev.get("source_id") == source_id for ev in body["evidence"])
    assert body["notes"]["fallback"] == "artifact_search"

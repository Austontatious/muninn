from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_media_source_and_derived_artifact_retrieval(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "image",
            "uri": "placeholder://image/not-stored-yet",
            "title": "Belize market photo",
            "artifacts": [
                {
                    "artifact_type": "caption",
                    "content_text": "Street-side restaurant signage in Belize market",
                    "generator": "stub",
                }
            ],
        },
    )
    assert source.status_code == 200
    source_id = source.json()["source"]["source_id"]

    card = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "media",
            "title": "Belize market still",
            "summary": "Image source with derived caption",
            "trusted_mode": True,
        },
    )
    assert card.status_code == 200
    card_id = card.json()["card_id"]

    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "caption"}],
        },
    )
    assert link.status_code == 200

    retrieve = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "restaurant signage Belize market photo",
            "scope": ["cards", "evidence"],
            "modalities": ["image", "text"],
            "k_cards": 5,
            "k_evidence": 3,
        },
    )
    assert retrieve.status_code == 200
    body = retrieve.json()
    assert any(c["card_id"] == card_id for c in body["cards"])
    assert any(ev.get("source_id") == source_id for ev in body["evidence"])



def test_embeddings_optional_for_lexical_retrieval(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "audio",
            "uri": "placeholder://audio/not-stored",
            "title": "Bowie audio note",
            "artifacts": [
                {
                    "artifact_type": "transcript",
                    "content_text": "Audio transcript mentions Belize restaurant",
                    "generator": "stub",
                }
            ],
        },
    )
    assert source.status_code == 200
    source_id = source.json()["source"]["source_id"]

    card = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "media",
            "title": "Bowie Belize audio",
            "summary": "Audio-derived transcript card",
            "trusted_mode": True,
        },
    )
    assert card.status_code == 200
    card_id = card.json()["card_id"]

    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "transcript"}],
        },
    )
    assert link.status_code == 200

    emb = client.post(
        "/embeddings",
        json={
            "namespace": "default",
            "owner_type": "source",
            "owner_id": source_id,
            "modality": "audio",
            "model": "audio-embed-v0",
            "dims": 1024,
            "embed_status": "pending",
        },
    )
    assert emb.status_code == 200
    assert emb.json()["embed_status"] == "pending"

    retrieve = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Belize restaurant audio transcript",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 3,
        },
    )
    assert retrieve.status_code == 200
    body = retrieve.json()
    assert any(c["card_id"] == card_id for c in body["cards"])
    assert any(ev.get("source_id") == source_id for ev in body["evidence"])

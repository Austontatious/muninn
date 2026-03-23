from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_cardex_propose_confirm_source_refs_and_retrieve(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)

    source_resp = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "note",
            "uri": "local://note/belize",
            "title": "Belize notes",
            "document_text": "Contact us at owner@example.com or 415-555-1212. Bowie mentioned Belize.",
            "artifacts": [
                {
                    "artifact_type": "summary",
                    "content_text": "Belize note summary with Bowie mention",
                    "generator": "stub",
                }
            ],
        },
    )
    assert source_resp.status_code == 200
    source_body = source_resp.json()
    source_id = source_body["source"]["source_id"]
    assert source_body["doc_id"] is not None
    assert len(source_body["chunk_ids"]) >= 1

    card_resp = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "place",
            "title": "Belize restaurant lead",
            "summary": "Potential lead connecting Belize restaurants and Bowie references",
            "tags_json": ["belize", "restaurant", "bowie"],
        },
    )
    assert card_resp.status_code == 200
    assert card_resp.json()["status"] == "proposed"
    proposal_id = card_resp.json()["proposal_id"]

    confirm_resp = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert confirm_resp.status_code == 200
    confirm_body = confirm_resp.json()
    assert confirm_body["proposal"]["status"] == "confirmed"
    card_id = confirm_body["applied"]["card_id"]

    get_resp = client.get(f"/cards/{card_id}", params={"namespace": "default"})
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Belize restaurant lead"

    link_resp = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [
                {"ref_type": "source", "ref_id": source_id, "role": "evidence"},
                {
                    "ref_type": "chunk",
                    "ref_id": source_body["chunk_ids"][0],
                    "role": "evidence",
                },
            ],
        },
    )
    assert link_resp.status_code == 200
    assert link_resp.json()["linked"] >= 1

    retrieve_resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "restaurant in Belize Bowie contact",
            "purpose": "assistant_answer",
            "scope": ["cards", "evidence"],
            "modalities": ["text", "image", "audio", "video"],
            "sensitivity_ceiling": 3,
            "k_cards": 10,
            "k_evidence": 5,
        },
    )
    assert retrieve_resp.status_code == 200
    body = retrieve_resp.json()
    assert len(body["cards"]) >= 1
    assert len(body["evidence"]) >= 1
    assert body["audit_id"].startswith("audit_")
    assert body["notes"]["policy"] == "tiered_redaction_v1"

    redaction_hits = [ev for ev in body["evidence"] if ev.get("redactions")]
    assert len(redaction_hits) >= 1


def test_cardex_embedding_stub_endpoint(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)

    card_resp = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "fact",
            "title": "Bowie in Belize",
            "summary": "Short fact",
            "trusted_mode": True,
        },
    )
    assert card_resp.status_code == 200
    card_id = card_resp.json()["card_id"]

    emb_resp = client.post(
        "/embeddings",
        json={
            "namespace": "default",
            "owner_type": "card",
            "owner_id": card_id,
            "modality": "text",
            "model": "text-embed-vX",
            "dims": 8,
            "embed_status": "pending",
        },
    )
    assert emb_resp.status_code == 200
    body = emb_resp.json()
    assert body["embedding_id"].startswith("emb_")
    assert body["embed_status"] == "pending"

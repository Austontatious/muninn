from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_promote_endpoint_propose_confirm_promotes_and_enqueues_jobs(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "note",
            "uri": "local://promote/source",
            "title": "Promote source",
            "artifacts": [{"artifact_type": "summary", "content_text": "Promote this evidence"}],
        },
    )
    assert source.status_code == 200
    source_id = source.json()["source"]["source_id"]
    artifact_id = source.json()["artifact_ids"][0]

    promote = client.post(
        "/promote",
        json={
            "namespace": "default",
            "owner_type": "artifact",
            "owner_id": artifact_id,
            "mode": "propose",
            "requested_by": "user:test",
        },
    )
    assert promote.status_code == 200
    promote_body = promote.json()
    assert promote_body["status"] == "proposed"
    assert promote_body["proposal_id"]
    proposal_id = promote_body["proposal_id"]

    confirm = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert confirm.status_code == 200
    applied = confirm.json()["applied"]
    card_id = applied["card_id"]
    assert card_id

    linked_ref = db.fetch_one(
        conn,
        """
        SELECT card_id
        FROM card_refs
        WHERE namespace = ?
          AND card_id = ?
          AND ref_type = 'source'
          AND ref_id = ?
        """,
        ("default", card_id, source_id),
    )
    assert linked_ref is not None

    evidence_state = db.fetch_one(
        conn,
        """
        SELECT status
        FROM evidence_state
        WHERE namespace = ? AND owner_type = 'artifact' AND owner_id = ?
        """,
        ("default", artifact_id),
    )
    assert evidence_state is not None
    assert str(evidence_state["status"]) == "promoted"

    evidence_job = db.fetch_one(
        conn,
        """
        SELECT status
        FROM index_jobs
        WHERE namespace = ?
          AND owner_type = 'artifact'
          AND owner_id = ?
          AND modality = 'text'
        """,
        ("default", artifact_id),
    )
    assert evidence_job is not None
    assert str(evidence_job["status"]) == "pending"

    card_job = db.fetch_one(
        conn,
        """
        SELECT status
        FROM index_jobs
        WHERE namespace = ?
          AND owner_type = 'card'
          AND owner_id = ?
          AND modality = 'text'
        """,
        ("default", card_id),
    )
    assert card_job is not None
    assert str(card_job["status"]) == "pending"

    promote_audit = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM audit_log WHERE event_type = 'cardex_promote'",
    )
    assert promote_audit is not None
    assert int(promote_audit["n"]) >= 1


def test_promote_trusted_mode_downgrades_to_propose_for_sensitive_owner(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "note",
            "uri": "local://promote/sensitive",
            "title": "Sensitive source",
            "sensitivity_tier": 2,
            "artifacts": [{"artifact_type": "summary", "content_text": "Sensitive promoted evidence"}],
        },
    )
    assert source.status_code == 200
    artifact_id = source.json()["artifact_ids"][0]

    promote = client.post(
        "/promote",
        json={
            "namespace": "default",
            "owner_type": "artifact",
            "owner_id": artifact_id,
            "mode": "trusted",
            "requested_by": "user:test",
        },
    )
    assert promote.status_code == 200
    body = promote.json()
    assert body["status"] == "proposed"
    assert body["card_id"] is None
    assert body["proposal_id"] is not None
    assert body["notes"]["effective_mode"] == "propose"

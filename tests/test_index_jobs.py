from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_active_card_creation_enqueues_card_index_job(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    card = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "fact",
            "title": "Index card",
            "summary": "Index me",
            "trusted_mode": True,
        },
    )
    assert card.status_code == 200
    card_id = card.json()["card_id"]

    job = db.fetch_one(
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
    assert job is not None
    assert str(job["status"]) == "pending"


def test_promoted_evidence_enqueues_single_pending_index_job(tmp_path, monkeypatch) -> None:
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
            "uri": "local://index/source",
            "title": "Index evidence source",
            "artifacts": [{"artifact_type": "summary", "content_text": "Index this promoted artifact"}],
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
            "mode": "propose",
            "requested_by": "user:test",
        },
    )
    assert promote.status_code == 200
    proposal_id = promote.json()["proposal_id"]
    assert proposal_id is not None

    confirm = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert confirm.status_code == 200

    second_promote = client.post(
        "/promote",
        json={
            "namespace": "default",
            "owner_type": "artifact",
            "owner_id": artifact_id,
            "mode": "propose",
            "requested_by": "user:test",
        },
    )
    assert second_promote.status_code == 200
    assert second_promote.json()["status"] == "noop"

    jobs = db.fetch_all(
        conn,
        """
        SELECT job_id
        FROM index_jobs
        WHERE namespace = ?
          AND owner_type = 'artifact'
          AND owner_id = ?
          AND modality = 'text'
          AND status IN ('pending', 'running')
        """,
        ("default", artifact_id),
    )
    assert len(jobs) == 1

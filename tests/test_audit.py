from __future__ import annotations

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _audit_count(conn) -> int:
    row = db.fetch_one(conn, "SELECT count(*) AS n FROM audit_log")
    return int(row["n"]) if row else 0


def _latest_http_request(conn) -> dict:
    row = db.fetch_one(
        conn,
        "SELECT event_json FROM audit_log WHERE event_type = 'http_request' ORDER BY created_at DESC LIMIT 1",
    )
    assert row is not None
    return json.loads(str(row["event_json"]))


def test_every_endpoint_call_writes_audit_row_and_failure_is_audited(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    prev = _audit_count(conn)
    health = client.get("/health")
    assert health.status_code == 200
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    card = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "fact",
            "title": "Audit card",
            "summary": "Audit card summary",
            "trusted_mode": True,
            "requested_by": "user:test",
        },
    )
    assert card.status_code == 200
    card_id = card.json()["card_id"]
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    get_card = client.get(f"/cards/{card_id}", params={"namespace": "default"})
    assert get_card.status_code == 200
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "note",
            "uri": "local://audit/source",
            "title": "Audit source",
        },
    )
    assert source.status_code == 200
    source_id = source.json()["source"]["source_id"]
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    add_artifact = client.post(
        f"/sources/{source_id}/artifacts",
        json={
            "namespace": "default",
            "artifacts": [{"artifact_type": "summary", "content_text": "audit artifact"}],
        },
    )
    assert add_artifact.status_code == 200
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
        },
    )
    assert link.status_code == 200
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    retrieve = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "audit",
            "scope": ["cards", "evidence"],
            "purpose": "assistant_answer",
            "modalities": ["text", "image"],
            "k_cards": 5,
            "k_evidence": 5,
        },
    )
    assert retrieve.status_code == 200
    assert _audit_count(conn) > prev

    prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "create_card",
            "payload_json": {"type": "fact", "title": "Prop card", "summary": "x"},
            "requested_by": "user:test",
        },
    )
    assert prop.status_code == 200
    proposal_id = prop.json()["proposal"]["proposal_id"]

    prev = _audit_count(conn)
    confirm = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert confirm.status_code == 200
    assert _audit_count(conn) > prev

    prev = _audit_count(conn)
    second_confirm = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert second_confirm.status_code == 404
    assert _audit_count(conn) > prev

    latest_http = _latest_http_request(conn)
    assert latest_http["payload"]["result_status"] == "error"



def test_audit_log_is_append_only(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    row = db.fetch_one(conn, "SELECT id FROM audit_log LIMIT 1")
    assert row is not None
    audit_id = str(row["id"])

    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE audit_log SET event_type = ? WHERE id = ?", ("tamper", audit_id))
        conn.commit()
    conn.rollback()

    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM audit_log WHERE id = ?", (audit_id,))
        conn.commit()
    conn.rollback()

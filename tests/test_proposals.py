from __future__ import annotations

import json

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _audit_events(conn, event_type: str) -> list[dict]:
    rows = db.fetch_all(
        conn,
        "SELECT event_json FROM audit_log WHERE event_type = ? ORDER BY created_at ASC",
        (event_type,),
    )
    return [json.loads(str(row["event_json"])) for row in rows]


def test_propose_confirm_creates_objects(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    src_prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "add_source",
            "requested_by": "user:test",
            "payload_json": {
                "source_type": "web",
                "uri": "https://example.test/bowie-belize",
                "title": "Bowie Belize Article",
                "artifacts": [
                    {
                        "artifact_type": "summary",
                        "content_text": "Bowie mention tied to Belize restaurant",
                    }
                ],
            },
        },
    )
    assert src_prop.status_code == 200
    src_prop_id = src_prop.json()["proposal"]["proposal_id"]

    src_confirm = client.post(
        f"/confirm/{src_prop_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert src_confirm.status_code == 200
    source_id = src_confirm.json()["applied"]["source_id"]

    card_prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "create_card",
            "requested_by": "user:test",
            "payload_json": {
                "type": "place",
                "title": "Belize Bowie lead",
                "summary": "Potential restaurant mention from Bowie source",
                "tags_json": ["belize", "bowie", "restaurant"],
            },
        },
    )
    assert card_prop.status_code == 200
    card_prop_id = card_prop.json()["proposal"]["proposal_id"]

    card_confirm = client.post(
        f"/confirm/{card_prop_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert card_confirm.status_code == 200
    card_id = card_confirm.json()["applied"]["card_id"]

    refs_prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "link_refs",
            "requested_by": "user:test",
            "payload_json": {
                "card_id": card_id,
                "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
            },
        },
    )
    assert refs_prop.status_code == 200
    refs_prop_id = refs_prop.json()["proposal"]["proposal_id"]

    refs_confirm = client.post(
        f"/confirm/{refs_prop_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert refs_confirm.status_code == 200
    assert refs_confirm.json()["applied"]["linked"] >= 1

    assert db.fetch_one(conn, "SELECT card_id FROM cards WHERE card_id = ?", (card_id,)) is not None
    assert db.fetch_one(conn, "SELECT source_id FROM sources WHERE source_id = ?", (source_id,)) is not None
    assert (
        db.fetch_one(conn, "SELECT card_id FROM card_refs WHERE card_id = ? AND ref_id = ?", (card_id, source_id))
        is not None
    )

    propose_events = _audit_events(conn, "cardex_propose")
    confirm_events = _audit_events(conn, "cardex_confirm")
    assert len(propose_events) >= 3
    assert len(confirm_events) >= 3



def test_propose_reject_does_not_commit(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "create_card",
            "payload_json": {
                "type": "fact",
                "title": "Should not commit",
                "summary": "Reject this",
            },
        },
    )
    assert prop.status_code == 200
    proposal_id = prop.json()["proposal"]["proposal_id"]

    reject = client.post(
        f"/reject/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test", "reason": "not useful"},
    )
    assert reject.status_code == 200
    assert reject.json()["proposal"]["status"] == "rejected"

    row = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM cards WHERE namespace = ? AND title = ?",
        ("default", "Should not commit"),
    )
    assert row is not None
    assert int(row["n"]) == 0

    reject_events = _audit_events(conn, "cardex_reject")
    assert len(reject_events) >= 1



def test_confirm_twice_safe_and_no_duplicates(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    prop = client.post(
        "/propose",
        json={
            "namespace": "default",
            "proposal_type": "create_card",
            "payload_json": {
                "type": "fact",
                "title": "Idempotent confirm",
                "summary": "Confirm once",
            },
        },
    )
    proposal_id = prop.json()["proposal"]["proposal_id"]

    first = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert first.status_code == 200
    card_id = first.json()["applied"]["card_id"]

    second = client.post(
        f"/confirm/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test"},
    )
    assert second.status_code in {200, 404}

    count_row = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM cards WHERE namespace = ? AND card_id = ?",
        ("default", card_id),
    )
    assert count_row is not None
    assert int(count_row["n"]) == 1

    http_events = _audit_events(conn, "http_request")
    actions = [ev.get("payload", {}).get("action") for ev in http_events]
    assert f"POST /confirm/{proposal_id}" in actions

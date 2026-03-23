from __future__ import annotations

import json

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _promotion_proposals_for_owner(conn, owner_type: str, owner_id: str) -> list[dict]:
    rows = db.fetch_all(
        conn,
        """
        SELECT proposal_id, status, reason, payload_json
        FROM proposals
        WHERE namespace = ?
          AND proposal_type = 'create_card'
        ORDER BY created_at ASC
        """,
        ("default",),
    )
    out: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(str(row["payload_json"]))
        except json.JSONDecodeError:
            continue
        promotion = payload.get("promotion")
        if not isinstance(promotion, dict):
            continue
        if str(promotion.get("owner_type")) != owner_type:
            continue
        if str(promotion.get("owner_id")) != owner_id:
            continue
        out.append(
            {
                "proposal_id": str(row["proposal_id"]),
                "status": str(row["status"]),
                "reason": str(row["reason"] or ""),
            }
        )
    return out


def _seed_artifact_source(client: TestClient) -> str:
    source = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "web",
            "uri": "https://example.test/bowie",
            "title": "Bowie Belize article",
            "artifacts": [
                {
                    "artifact_type": "summary",
                    "content_text": "Restaurant in Belize that Bowie mentioned",
                }
            ],
        },
    )
    assert source.status_code == 200
    return source.json()["artifact_ids"][0]


def test_implicit_trigger_creates_candidate_once_without_spam(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    artifact_id = _seed_artifact_source(client)

    q = {
        "namespace": "default",
        "query": "restaurant in Belize David Bowie mentioned",
        "scope": ["cards", "evidence"],
        "k_cards": 5,
        "k_evidence": 5,
    }
    first = client.post("/retrieve", json=q)
    second = client.post("/retrieve", json=q)
    assert first.status_code == 200
    assert second.status_code == 200

    state = db.fetch_one(
        conn,
        """
        SELECT status
        FROM evidence_state
        WHERE namespace = ? AND owner_type = 'artifact' AND owner_id = ?
        """,
        ("default", artifact_id),
    )
    assert state is not None
    assert str(state["status"]) == "candidate"

    proposals = _promotion_proposals_for_owner(conn, "artifact", artifact_id)
    assert len(proposals) == 1
    assert proposals[0]["status"] == "proposed"

    third = client.post("/retrieve", json=q)
    assert third.status_code == 200

    proposals_after = _promotion_proposals_for_owner(conn, "artifact", artifact_id)
    assert len(proposals_after) == 1

    trigger_audit = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM audit_log WHERE event_type = 'cardex_promotion_trigger'",
    )
    assert trigger_audit is not None
    assert int(trigger_audit["n"]) >= 1


def test_reject_enters_cooldown_and_prevents_new_implicit_proposals(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    artifact_id = _seed_artifact_source(client)

    q = {
        "namespace": "default",
        "query": "restaurant in Belize David Bowie mentioned",
        "scope": ["cards", "evidence"],
        "k_cards": 5,
        "k_evidence": 5,
    }
    assert client.post("/retrieve", json=q).status_code == 200
    assert client.post("/retrieve", json=q).status_code == 200

    proposals_before = _promotion_proposals_for_owner(conn, "artifact", artifact_id)
    assert len(proposals_before) == 1
    proposal_id = proposals_before[0]["proposal_id"]

    reject = client.post(
        f"/reject/{proposal_id}",
        json={"namespace": "default", "decided_by": "user:test", "reason": "not now"},
    )
    assert reject.status_code == 200

    assert client.post("/retrieve", json=q).status_code == 200
    assert client.post("/retrieve", json=q).status_code == 200

    proposals_after = _promotion_proposals_for_owner(conn, "artifact", artifact_id)
    assert len(proposals_after) == 1
    assert proposals_after[0]["status"] == "rejected"

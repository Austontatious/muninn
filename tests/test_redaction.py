from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def _create_source(client: TestClient, tier: int, text: str) -> str:
    resp = client.post(
        "/sources",
        json={
            "namespace": "default",
            "source_type": "note",
            "uri": f"local://tier/{tier}",
            "title": f"Tier {tier} source",
            "sensitivity_tier": tier,
            "artifacts": [{"artifact_type": "summary", "content_text": text}],
        },
    )
    assert resp.status_code == 200
    return resp.json()["source"]["source_id"]


def _create_card(client: TestClient, title: str, tier: int = 0) -> str:
    resp = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "fact",
            "title": title,
            "summary": title,
            "sensitivity_tier": tier,
            "trusted_mode": True,
        },
    )
    assert resp.status_code == 200
    return resp.json()["card_id"]


def test_sensitivity_ceiling_blocks_evidence_and_reports_redaction(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    safe_source = _create_source(client, tier=1, text="safe bowie belize snippet")
    sensitive_source = _create_source(client, tier=2, text="sensitive bowie belize details")
    card_id = _create_card(client, title="Bowie Belize sensitive split")

    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [
                {"ref_type": "source", "ref_id": safe_source, "role": "evidence"},
                {"ref_type": "source", "ref_id": sensitive_source, "role": "evidence"},
            ],
        },
    )
    assert link.status_code == 200

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "bowie belize",
            "scope": ["cards", "evidence"],
            "sensitivity_ceiling": 1,
            "k_cards": 5,
            "k_evidence": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert any(ev.get("source_id") == safe_source and not ev.get("blocked") for ev in body["evidence"])
    assert any(
        ev.get("source_id") == sensitive_source
        and ev.get("blocked")
        and ev.get("blocked_reason") == "tier_exceeded"
        for ev in body["evidence"]
    )
    assert any(
        item["type"] == "tier_block" and item["reason"] == "tier_exceeded"
        for item in body["redactions"]
    )



def test_sensitivity_ceiling_blocks_entire_card(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    client = TestClient(app)

    source_id = _create_source(client, tier=2, text="secret bowie belize reference")
    card_id = _create_card(client, title="Secret Bowie Belize card", tier=2)

    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
        },
    )
    assert link.status_code == 200

    resp = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Secret Bowie Belize card",
            "scope": ["cards", "evidence"],
            "sensitivity_ceiling": 1,
            "k_cards": 5,
            "k_evidence": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert body["cards"] == []
    assert not any(ev.get("source_id") == source_id and not ev.get("blocked") for ev in body["evidence"])
    assert any(
        item["target_type"] == "card" and item["reason"] == "tier_exceeded"
        for item in body["redactions"]
    )

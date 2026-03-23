from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_retrieve_updates_signals_and_coaccess_edges(tmp_path, monkeypatch) -> None:
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
            "uri": "local://signals/belize",
            "title": "Signals source",
            "artifacts": [{"artifact_type": "summary", "content_text": "Bowie Belize restaurant lead"}],
        },
    )
    assert source.status_code == 200
    source_id = source.json()["source"]["source_id"]
    artifact_id = source.json()["artifact_ids"][0]

    card = client.post(
        "/cards",
        json={
            "namespace": "default",
            "type": "place",
            "title": "Signals card",
            "summary": "Signals card summary",
            "trusted_mode": True,
        },
    )
    assert card.status_code == 200
    card_id = card.json()["card_id"]

    link = client.post(
        f"/cards/{card_id}/refs",
        json={
            "namespace": "default",
            "refs": [{"ref_type": "source", "ref_id": source_id, "role": "evidence"}],
        },
    )
    assert link.status_code == 200

    r1 = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Signals card Belize restaurant mention",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 5,
        },
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "Signals Bowie restaurant lead",
            "scope": ["cards", "evidence"],
            "k_cards": 5,
            "k_evidence": 5,
        },
    )
    assert r2.status_code == 200

    card_signal = db.fetch_one(
        conn,
        "SELECT access_count FROM signals WHERE namespace = ? AND owner_type = 'card' AND owner_id = ?",
        ("default", card_id),
    )
    artifact_signal = db.fetch_one(
        conn,
        "SELECT access_count FROM signals WHERE namespace = ? AND owner_type = 'artifact' AND owner_id = ?",
        ("default", artifact_id),
    )
    source_signal = db.fetch_one(
        conn,
        "SELECT access_count FROM signals WHERE namespace = ? AND owner_type = 'source' AND owner_id = ?",
        ("default", source_id),
    )
    assert card_signal is not None
    assert artifact_signal is not None
    assert source_signal is not None
    assert int(card_signal["access_count"]) == 2
    assert int(artifact_signal["access_count"]) == 2
    assert int(source_signal["access_count"]) == 2

    edge = db.fetch_one(
        conn,
        """
        SELECT weight
        FROM coaccess_edges
        WHERE namespace = ?
          AND a_type = 'card'
          AND a_id = ?
          AND b_type = 'artifact'
          AND b_id = ?
        """,
        ("default", card_id, artifact_id),
    )
    assert edge is not None
    assert float(edge["weight"]) >= 2.0

    retrieve_audit = db.fetch_one(
        conn,
        "SELECT count(*) AS n FROM audit_log WHERE event_type = 'cardex_retrieve'",
    )
    assert retrieve_audit is not None
    assert int(retrieve_audit["n"]) >= 2

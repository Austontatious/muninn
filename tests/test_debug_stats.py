from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_debug_stats_returns_counts_and_migrations(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.setenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", "1")
    monkeypatch.delenv("MUNINN_READONLY", raising=False)

    conn = db.connect()
    db.init_db(conn)

    candidate = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "direct"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="stats_turn"),
    )
    write_candidates("lexi", [candidate])

    client = TestClient(app)
    global_stats = client.get("/v0/debug/stats")
    assert global_stats.status_code == 200
    global_body = global_stats.json()

    assert "versions" in global_body
    assert "config" in global_body
    assert "migrations" in global_body
    assert "counts" in global_body
    assert "applied_count" in global_body["migrations"]

    scoped_stats = client.get("/v0/debug/stats", params={"namespace": "lexi"})
    assert scoped_stats.status_code == 200
    scoped_body = scoped_stats.json()
    assert scoped_body["counts"]["namespace"] == "lexi"
    assert scoped_body["counts"]["preferences"] is not None
    assert scoped_body["counts"]["preferences"] >= 1

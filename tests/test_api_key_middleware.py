from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_api_key_middleware_enforces_when_enabled(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "1")
    monkeypatch.setenv("MUNINN_API_KEY", "testkey")
    monkeypatch.delenv("MUNINN_READONLY", raising=False)

    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200

    no_key = client.get("/v0/memory/version")
    assert no_key.status_code == 401

    wrong_key = client.get("/v0/memory/version", headers={"X-API-Key": "wrong"})
    assert wrong_key.status_code == 401

    with_key = client.get("/v0/memory/version", headers={"X-API-Key": "testkey"})
    assert with_key.status_code == 200
    assert "version" in with_key.json()

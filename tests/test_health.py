from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_health(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    conn = db.connect()
    db.init_db(conn)

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] in [True, False]

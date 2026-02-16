from fastapi.testclient import TestClient

from muninn.api import app


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] in [True, False]

from __future__ import annotations

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app


def test_procedure_reflect_and_retrieve_endpoints(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    human_db = tmp_path / "human_memory.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_HUMAN_MEMORY_DB_PATH", str(human_db))

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    client = TestClient(app)

    empty = client.post(
        "/v0/memory/procedures/retrieve",
        json={
            "namespace": "default",
            "space_key": "repo:laila",
            "task_label": "debug docker restarts",
            "context_summary": "container exits quickly",
            "task_type": "troubleshooting",
            "tool_names": ["docker"],
            "limit": 3,
        },
    )
    assert empty.status_code == 200
    assert empty.json()["procedures"] == []

    reflect = client.post(
        "/v0/memory/procedures/reflect",
        json={
            "namespace": "default",
            "space_key": "repo:laila",
            "task_label": "debug docker restarts",
            "context_summary": "container exits quickly",
            "actions_taken": ["inspect logs", "check healthcheck"],
            "outcome_status": "success",
            "what_worked": "logs showed missing env variable",
            "what_failed": "",
            "changed_outcome": "service stabilized after env fix",
            "reusable": True,
            "task_type": "troubleshooting",
            "workflow_type": "text_post_draft",
            "tool_requirements": ["docker"],
            "verification_checks": ["container healthy for 5m"],
        },
    )
    assert reflect.status_code == 200
    payload = reflect.json()
    assert payload["action"] in {"created_new_procedure", "updated_existing_procedure"}
    assert payload["procedure_card_id"]

    retrieved = client.post(
        "/v0/memory/procedures/retrieve",
        json={
            "namespace": "default",
            "space_key": "repo:laila",
            "task_label": "debug docker restarts",
            "context_summary": "container exits quickly",
            "task_type": "troubleshooting",
            "tool_names": ["docker"],
            "limit": 3,
        },
    )
    assert retrieved.status_code == 200
    body = retrieved.json()
    assert body["procedures"]
    assert body["compact"]

from __future__ import annotations

import json

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.procedures import ingest_procedure_reflection, procedure_card_upsert, query_procedure_cards
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _init_conn(tmp_path):
    db_path = tmp_path / "human_memory_procedures.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:procedurestest001",
        label="procedures-repo",
        meta_json=json.dumps({"root_path": "/tmp/procedures"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return conn, resolved.key


def test_create_procedure_card_from_structured_payload(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    card_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Investigate container restart loops",
        summary="Use logs + health checks before changing compose.",
        trigger_conditions=["docker service restarts repeatedly"],
        scope={"type": "project"},
        steps=["inspect container logs", "check healthcheck status", "verify env vars"],
        tool_requirements=["docker", "journalctl"],
        pitfalls=["restarting blindly can hide root cause"],
        verification_checks=["container healthy for 5m"],
        confidence=0.78,
        validation_status="validated",
        task_types=["troubleshooting"],
    )

    assert card_id
    payload = query_procedure_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        task_label="docker keeps restarting",
        context_summary="container unhealthy",
        task_type="troubleshooting",
        tool_names=["docker"],
        limit=3,
    )
    assert payload["procedures"]
    top = payload["procedures"][0]
    assert top["title"] == "Investigate container restart loops"
    assert top["validation_status"] == "validated"
    conn.close()


def test_retrieval_ranking_and_filtering_demotes_stale_low_confidence(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    best_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Use rg before grep",
        summary="Prefer ripgrep for code search speed.",
        trigger_conditions=["searching code in repo"],
        scope={"type": "project"},
        steps=["run rg pattern path"],
        confidence=0.85,
        validation_status="validated",
        task_types=["code_navigation"],
    )
    stale_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Old noisy search process",
        summary="Use broad recursive grep everywhere.",
        trigger_conditions=["searching code"],
        scope={"type": "project"},
        steps=["run grep -R"],
        confidence=0.25,
        validation_status="deprecated",
        task_types=["code_navigation"],
    )
    conn.execute("UPDATE cards SET updated_at = datetime('now', '-400 days') WHERE id = ?", (stale_id,))
    conn.commit()

    payload = query_procedure_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        task_label="search this repo",
        context_summary="need fast code search",
        task_type="code_navigation",
        tool_names=["rg"],
        limit=3,
    )
    assert payload["procedures"]
    assert payload["procedures"][0]["id"] == best_id
    assert payload["procedures"][0]["selection_reasons"]
    assert payload["diagnostics"]["filtered_low_confidence"] >= 1
    conn.close()


def test_supersession_replaces_previous_procedure(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    old_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Initial deployment procedure",
        summary="Old steps",
        trigger_conditions=["deploying service"],
        scope={"type": "project"},
        steps=["build image", "deploy"],
        confidence=0.6,
    )
    new_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Deployment procedure v2",
        summary="Updated steps with verification",
        trigger_conditions=["deploying service"],
        scope={"type": "project"},
        steps=["build image", "run smoke test", "deploy"],
        verification_checks=["smoke tests pass"],
        confidence=0.82,
        validation_status="validated",
        supersedes_card_id=old_id,
    )

    assert new_id != old_id
    payload = query_procedure_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        task_label="deploy service",
        task_type="deployment",
        limit=5,
    )
    ids = {item["id"] for item in payload["procedures"]}
    assert new_id in ids
    assert old_id not in ids
    conn.close()


def test_reflection_failure_lowers_confidence_on_existing_procedure(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    procedure_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Port-forward debug workflow",
        summary="Forward then verify endpoint.",
        trigger_conditions=["remote backend unreachable"],
        scope={"type": "project"},
        steps=["start tunnel", "curl health endpoint"],
        confidence=0.8,
        validation_status="validated",
        task_types=["network_debug"],
    )

    result = ingest_procedure_reflection(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        reflection={
            "task_label": "remote backend unreachable",
            "context_summary": "phone cannot reach api",
            "actions_taken": ["start tunnel", "curl health endpoint"],
            "outcome_status": "failure",
            "what_failed": "tunnel endpoint was wrong",
            "reusable": True,
            "candidate_procedure_id": procedure_id,
            "task_type": "network_debug",
            "tool_requirements": ["ssh"],
        },
    )

    assert result["action"] == "updated_existing_procedure"
    assert float(result["confidence"]) < 0.8
    conn.close()


def test_trivial_reflection_is_ignored_for_creation(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    result = ingest_procedure_reflection(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        reflection={
            "task_label": "quick note",
            "context_summary": "ok",
            "actions_taken": [],
            "outcome_status": "success",
            "what_worked": "",
            "what_failed": "",
            "changed_outcome": "",
            "reusable": True,
            "task_type": "misc",
            "tool_requirements": [],
        },
    )
    assert result["action"] == "ignored_low_signal_reflection"

    payload = query_procedure_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        task_label="quick note",
        limit=3,
    )
    assert payload["procedures"] == []
    conn.close()


def test_repeated_failures_invalidate_procedure(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    procedure_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Flaky workflow",
        summary="Needs cautious handling",
        trigger_conditions=["same task"],
        scope={"type": "project"},
        steps=["step a", "step b"],
        confidence=0.7,
        validation_status="validated",
    )

    latest = None
    for _ in range(3):
        latest = ingest_procedure_reflection(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            reflection={
                "task_label": "same task",
                "context_summary": "same task",
                "candidate_procedure_id": procedure_id,
                "actions_taken": ["step a"],
                "outcome_status": "failure",
                "what_failed": "failed",
                "reusable": True,
                "task_type": "ops",
                "tool_requirements": ["shell"],
            },
        )
        procedure_id = latest["procedure_card_id"] or procedure_id

    assert latest is not None
    assert latest["action"] == "invalidated_procedure_after_failures"
    assert latest["validation_status"] == "deprecated"
    conn.close()


def test_material_change_supersedes_existing_procedure(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    old_id = procedure_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        title="Same workflow",
        summary="Original path",
        trigger_conditions=["same workflow"],
        scope={"type": "project"},
        steps=["a", "b"],
        confidence=0.8,
        validation_status="validated",
    )
    result = ingest_procedure_reflection(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        reflection={
            "task_label": "same workflow",
            "context_summary": "same workflow",
            "candidate_procedure_id": old_id,
            "actions_taken": ["a", "b", "c", "d"],
            "outcome_status": "success",
            "what_worked": "new steps required",
            "changed_outcome": "old flow incomplete",
            "reusable": True,
            "task_type": "ops",
            "tool_requirements": ["shell"],
        },
    )

    assert result["action"] == "superseded_existing_procedure"
    assert result["procedure_card_id"] != old_id
    conn.close()


def test_reflection_accepts_valid_structured_evidence_and_links_card(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    result = ingest_procedure_reflection(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        reflection={
            "task_label": "container restart loop",
            "context_summary": "service restarted until env var fixed",
            "actions_taken": ["inspect logs", "fix env var"],
            "outcome_status": "success",
            "what_worked": "logs identified missing configuration",
            "reusable": True,
            "task_type": "ops",
            "tool_requirements": ["docker"],
            "metadata": {
                "structured_evidence": [
                    {
                        "type": "log",
                        "ref": "friday://runtime/procedure_lifecycle",
                        "excerpt": "tool_failures=0 tool_successes=1 retries=0",
                        "meta": {"source": "friday_procedure_reflection_v1"},
                    }
                ]
            },
        },
    )

    assert result["action"] == "created_new_procedure"
    assert int(result.get("evidence_count") or 0) == 1
    assert list(result.get("warning_codes") or []) == []

    row = conn.execute(
        """
        SELECT e.type AS type, e.ref AS ref, e.excerpt AS excerpt
        FROM card_evidence ce
        JOIN evidence e ON e.id = ce.evidence_id
        WHERE ce.card_id = ?
        """,
        (result["procedure_card_id"],),
    ).fetchone()
    assert row is not None
    assert str(row["type"]) == "log"
    assert str(row["ref"]) == "friday://runtime/procedure_lifecycle"
    conn.close()


def test_reflection_warns_on_malformed_structured_evidence(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    result = ingest_procedure_reflection(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        reflection={
            "task_label": "container restart loop",
            "context_summary": "service restarted until env var fixed",
            "actions_taken": ["inspect logs", "fix env var"],
            "outcome_status": "success",
            "what_worked": "logs identified missing configuration",
            "reusable": True,
            "task_type": "ops",
            "tool_requirements": ["docker"],
            "metadata": {
                "structured_evidence": [
                    {
                        "type": "runtime_metrics",
                        "ref": {"not": "a string"},
                        "meta": "not-an-object",
                    }
                ]
            },
        },
    )

    codes = set(result.get("warning_codes") or [])
    assert "invalid_structured_evidence_type_value" in codes
    assert int(result.get("evidence_count") or 0) == 0
    conn.close()

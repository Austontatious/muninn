from __future__ import annotations

import json

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.cards import card_upsert
from muninn.human_memory.policy import learn_policy_signal
from muninn.human_memory.rehydration import rehydrate_bundle
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _init_conn(tmp_path):
    db_path = tmp_path / "human_memory_rehydration.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    repo = ResolvedSpace(
        key="repo:rehydrate000001",
        label="rehydrate-repo",
        meta_json=json.dumps({"root_path": "/tmp/rehydrate-repo"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=repo)
    return conn, repo.key


def test_rehydrate_bundle_prefers_exact_project_match_even_when_old(tmp_path) -> None:
    conn, repo_key = _init_conn(tmp_path)

    exact_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        kind="decision",
        title="Checkpoint C audit batching decision",
        summary="Checkpoint C audit flush batching is the stable path for this repo.",
        body="Checkpoint C audit flush batching remains the implementation decision.",
        created_by_client_name="codex-vscode",
    )
    recent_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        kind="runbook",
        title="Recent but unrelated note",
        summary="This is recent but unrelated to checkpoint batching.",
        body="Unrelated runbook details.",
        created_by_client_name="codex-vscode",
    )
    conn.execute(
        "UPDATE cards SET updated_at = datetime('now', '-15 days') WHERE id = ?",
        (exact_id,),
    )
    conn.execute(
        "UPDATE cards SET updated_at = datetime('now', '-1 day') WHERE id = ?",
        (recent_id,),
    )
    conn.commit()

    payload = rehydrate_bundle(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        query="checkpoint c audit flush batching",
        limit=5,
        include_body=False,
        include_policy=False,
        scope="strict",
    )

    assert payload["project_cards"][0]["id"] == exact_id
    assert payload["stages"][0]["stage"] == "strict_search"
    assert payload["stages"][-1]["skip_reason"] == "soft_scope_disabled"
    conn.close()


def test_rehydrate_bundle_uses_global_and_policy_fallback_when_strict_misses(tmp_path) -> None:
    conn, repo_key = _init_conn(tmp_path)

    global_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key="global",
        kind="runbook",
        title="Docker logs troubleshooting",
        summary="Use exact docker logs commands when debugging service output.",
        body="Run `docker logs <container>` first when debugging service output.",
        created_by_client_name="codex-vscode",
        evidence_refs=[
            {
                "id": "evidence-global-runbook",
                "type": "file",
                "ref": "/tmp/runbook.md",
                "excerpt": "docker logs guidance",
                "created_by_client_name": "codex-vscode",
            }
        ],
    )
    learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        summary="I need exact commands, not a summary.",
        signal_type="directive",
        outcome="corrected",
        scope_type="project",
        tool_name="shell",
        task_type="troubleshooting",
        created_by_client_name="codex-vscode",
    )

    payload = rehydrate_bundle(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_key,
        query="docker logs exact commands",
        limit=6,
        include_body=False,
        include_policy=True,
        scope="soft",
        tool_name="shell",
        task_type="troubleshooting",
    )

    stage_results = {row["stage"]: row["results"] for row in payload["stages"]}
    project_ids = {row["id"] for row in payload["project_cards"]}

    assert stage_results["strict_search"] == 0
    assert stage_results["global_search"] >= 1
    assert global_id in project_ids
    assert payload["policy_cards"]
    assert payload["bundle"]["preferences"] or payload["bundle"]["lessons"]
    alias_stage = next(row for row in payload["stages"] if row["stage"] == "alias_search")
    assert alias_stage["skipped"] is True
    assert alias_stage["skip_reason"] == "no_alias_space_keys"
    conn.close()

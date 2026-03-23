from __future__ import annotations

import json

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.interactions import list_interaction_events
from muninn.human_memory.policy import learn_policy_signal, query_policy_cards
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _init_conn(tmp_path):
    db_path = tmp_path / "human_memory_policy.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    repo_one = ResolvedSpace(
        key="repo:policyrepo000001",
        label="repo-one",
        meta_json=json.dumps({"root_path": "/tmp/repo-one"}, separators=(",", ":")),
    )
    repo_two = ResolvedSpace(
        key="repo:policyrepo000002",
        label="repo-two",
        meta_json=json.dumps({"root_path": "/tmp/repo-two"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=repo_one)
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=repo_two)
    return conn, repo_one.key, repo_two.key


def test_learn_policy_signal_promotes_directive_and_records_event(tmp_path) -> None:
    conn, repo_one, _ = _init_conn(tmp_path)

    result = learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        summary="No, check the repo first before answering implementation questions.",
        signal_type="mixed",
        outcome="corrected",
        scope_type="project",
        created_by_client_name="codex-vscode",
    )

    assert result["promoted"] is True
    assert result["kind"] == "policy.directive"

    policy_payload = query_policy_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        query="implementation repo",
        include_global=False,
        limit=5,
        include_body=True,
    )
    assert len(policy_payload["cards"]) == 1
    policy = policy_payload["cards"][0]["policy"]
    assert "Check repo/files" in policy["preferred_behavior"]

    events = list_interaction_events(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        limit=5,
        event_types=["policy_signal"],
    )
    assert len(events) == 1
    assert events[0]["promoted_card_id"] == result["policy_card_id"]
    conn.close()


def test_repeated_evaluative_signal_promotes_only_after_repetition(tmp_path) -> None:
    conn, repo_one, _ = _init_conn(tmp_path)

    first = learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        summary="A narrower query succeeds after the broad query fails.",
        signal_type="evaluative",
        outcome="failure",
        scope_type="project",
        tool_name="muninn.cards.search",
        task_type="retrieval",
        created_by_client_name="codex-vscode",
    )
    second = learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        summary="A narrower query succeeds after the broad query fails.",
        signal_type="evaluative",
        outcome="failure",
        scope_type="project",
        tool_name="muninn.cards.search",
        task_type="retrieval",
        created_by_client_name="codex-vscode",
    )

    assert first["promoted"] is False
    assert second["promoted"] is True
    assert second["kind"] == "tooling.preference"
    assert second["repetition_count"] >= 2

    policy_payload = query_policy_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        query="narrower query retrieval",
        include_global=False,
        limit=5,
    )
    assert len(policy_payload["cards"]) == 1
    assert policy_payload["cards"][0]["policy"]["repetition_count"] >= 2
    conn.close()


def test_project_scoped_policy_does_not_leak_to_other_repo(tmp_path) -> None:
    conn, repo_one, repo_two = _init_conn(tmp_path)

    learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        summary="I need exact commands, not a summary.",
        signal_type="directive",
        outcome="corrected",
        scope_type="project",
        task_type="troubleshooting",
        created_by_client_name="codex-vscode",
    )

    repo_one_payload = query_policy_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_one,
        query="exact commands",
        include_global=False,
        limit=5,
    )
    repo_two_payload = query_policy_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo_two,
        query="exact commands",
        include_global=False,
        limit=5,
    )

    assert len(repo_one_payload["cards"]) == 1
    assert repo_two_payload["cards"] == []
    conn.close()

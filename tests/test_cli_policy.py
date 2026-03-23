from __future__ import annotations

import argparse
import json

from muninn import cli
from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.policy import learn_policy_signal, query_policy_cards
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _init_policy_db(tmp_path):
    db_path = tmp_path / "human_memory_policy_cli.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    repo = ResolvedSpace(
        key="repo:cli-policy-0001",
        label="cli-policy-repo",
        meta_json=json.dumps({"root_path": "/tmp/cli-policy-repo"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=repo)
    promoted = learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo.key,
        summary="I need exact commands, not a summary.",
        signal_type="directive",
        outcome="corrected",
        scope_type="project",
        task_type="troubleshooting",
        created_by_client_name="codex-vscode",
    )
    learn_policy_signal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=repo.key,
        summary="A narrower query succeeds after the broad query fails.",
        signal_type="evaluative",
        outcome="failure",
        scope_type="project",
        tool_name="muninn.cards.search",
        task_type="retrieval",
        created_by_client_name="codex-vscode",
    )
    conn.close()
    return db_path, repo.key, str(promoted["policy_card_id"])


def test_cmd_policy_list_json(tmp_path, capsys) -> None:
    db_path, repo_key, _ = _init_policy_db(tmp_path)
    args = argparse.Namespace(
        db_path=str(db_path),
        space_key=repo_key,
        cwd=None,
        query="exact commands",
        scope_types=None,
        scope_key=None,
        tool_name=None,
        task_type=None,
        include_global=False,
        limit=10,
        include_body=False,
        as_json=True,
    )

    code = cli._cmd_policy_list(args)
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["counts"]["total"] == 1
    assert payload["counts"]["by_kind"]["policy.directive"] == 1



def test_cmd_policy_show_json(tmp_path, capsys) -> None:
    db_path, _, card_id = _init_policy_db(tmp_path)
    args = argparse.Namespace(
        db_path=str(db_path),
        card_id=card_id,
        as_json=True,
    )

    code = cli._cmd_policy_show(args)
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["id"] == card_id
    assert payload["kind"] == "policy.directive"



def test_cmd_policy_events_can_filter_unpromoted(tmp_path, capsys) -> None:
    db_path, repo_key, _ = _init_policy_db(tmp_path)
    args = argparse.Namespace(
        db_path=str(db_path),
        space_key=repo_key,
        cwd=None,
        session_id=None,
        event_types=["policy_signal"],
        promoted="unpromoted",
        limit=10,
        as_json=True,
    )

    code = cli._cmd_policy_events(args)
    captured = capsys.readouterr()

    assert code == 0
    payload = json.loads(captured.out)
    assert payload["counts"]["unpromoted"] >= 1
    assert all(event["promoted_card_id"] is None for event in payload["events"])

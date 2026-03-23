from __future__ import annotations

import json
import subprocess

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.cards import card_upsert, cards_recent
from muninn.human_memory.spaces import (
    ResolvedSpace,
    canonicalize_space_key,
    get_or_create_space,
    resolve_space_from_cwd,
    resolve_space_lookup_keys,
)


def _git(cwd: str, *args: str) -> None:
    subprocess.check_call(["git", *args], cwd=cwd)


def test_resolve_space_from_git_remote_is_stable(tmp_path) -> None:
    repo = tmp_path / "repo_a"
    repo.mkdir()
    _git(str(repo), "init")
    _git(str(repo), "remote", "add", "origin", "git@github.com:Org/Repo.git")

    resolved_1 = resolve_space_from_cwd(str(repo))
    resolved_2 = resolve_space_from_cwd(str(repo))

    assert resolved_1.key.startswith("repo:")
    assert resolved_1.key == resolved_2.key
    assert resolved_1.label == "repo_a"

    meta = json.loads(resolved_1.meta_json)
    assert meta["git_remote"] == "git@github.com:Org/Repo.git"
    assert meta["git_remote_norm"] == "https://github.com/org/repo"


def test_resolve_space_from_non_git_uses_cwd_fallback(tmp_path) -> None:
    cwd = tmp_path / "scratch"
    cwd.mkdir()
    resolved = resolve_space_from_cwd(str(cwd))
    assert resolved.key.startswith("path:")
    assert resolved.label == "scratch"
    assert len(resolved.alias_keys) == 1
    assert resolved.alias_keys[0].startswith("cwd:")


def test_get_or_create_space_registers_aliases_and_migrates_legacy_rows(tmp_path) -> None:
    db_path = tmp_path / "spaces_aliases.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    legacy = ResolvedSpace(
        key="path:legacy1234567890",
        label="legacy",
        meta_json=json.dumps({"root_path": "/tmp/project"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=legacy)
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=legacy.key,
        kind="decision",
        title="Legacy path card",
        summary="Legacy summary",
        body="Legacy body",
    )

    canonical = ResolvedSpace(
        key="repo:canonical123456",
        label="project",
        meta_json=json.dumps(
            {"root_path": "/tmp/project", "git_remote": "git@github.com:Org/Repo.git"},
            separators=(",", ":"),
        ),
        alias_keys=(legacy.key,),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=canonical)

    assert canonicalize_space_key(conn, user_id=DEFAULT_USER_ID, space_key=legacy.key) == canonical.key
    assert resolve_space_lookup_keys(conn, user_id=DEFAULT_USER_ID, space_key=canonical.key) == [
        canonical.key,
        legacy.key,
    ]

    rows = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=canonical.key,
        limit=10,
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "Legacy path card"
    conn.close()

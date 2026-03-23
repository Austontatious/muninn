from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import uuid
from dataclasses import dataclass, field
from typing import Any


def _sha16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _run_git(cwd: str, args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return None
    decoded = out.decode("utf-8", "replace").strip()
    return decoded or None


def _normalize_remote(remote: str) -> str:
    value = remote.strip()
    value = value.replace("git@github.com:", "https://github.com/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


@dataclass(frozen=True)
class ResolvedSpace:
    key: str
    label: str
    meta_json: str
    alias_keys: tuple[str, ...] = field(default_factory=tuple)


def resolve_space_from_cwd(cwd: str) -> ResolvedSpace:
    abs_cwd = os.path.abspath(cwd)

    repo_root = _run_git(abs_cwd, ["rev-parse", "--show-toplevel"])
    if repo_root:
        repo_root = os.path.abspath(repo_root)
        path_key = f"path:{_sha16(repo_root)}"
        remote = _run_git(abs_cwd, ["config", "--get", "remote.origin.url"])
        if remote:
            remote_norm = _normalize_remote(remote)
            key = f"repo:{_sha16(remote_norm)}"
            meta = {
                "root_path": repo_root,
                "git_remote": remote,
                "git_remote_norm": remote_norm,
                "identity": "repo_remote",
            }
            alias_keys = (path_key,)
        else:
            key = path_key
            meta = {
                "root_path": repo_root,
                "git_remote": None,
                "identity": "repo_path",
            }
            alias_keys = ()
        label = os.path.basename(repo_root.rstrip(os.sep)) or repo_root
        return ResolvedSpace(
            key=key,
            label=label,
            meta_json=json.dumps(meta, separators=(",", ":")),
            alias_keys=alias_keys,
        )

    key = f"path:{_sha16(abs_cwd)}"
    legacy_cwd_key = f"cwd:{_sha16(abs_cwd)}"
    label = os.path.basename(abs_cwd.rstrip(os.sep)) or abs_cwd
    return ResolvedSpace(
        key=key,
        label=label,
        meta_json=json.dumps(
            {"root_path": abs_cwd, "cwd": abs_cwd, "identity": "path"},
            separators=(",", ":"),
        ),
        alias_keys=(legacy_cwd_key,),
    )


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1;",
        (table_name,),
    ).fetchone()
    return row is not None


def _load_space_row(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    key: str,
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, key, label, meta_json FROM spaces WHERE user_id = ? AND key = ?;",
        (user_id, key),
    ).fetchone()


def canonicalize_space_key(conn: sqlite3.Connection, *, user_id: str, space_key: str) -> str:
    normalized = str(space_key or "").strip()
    if not normalized:
        return normalized
    if _table_exists(conn, "space_aliases"):
        row = conn.execute(
            """
            SELECT canonical_key
            FROM space_aliases
            WHERE user_id = ? AND alias_key = ?
            LIMIT 1
            """,
            (user_id, normalized),
        ).fetchone()
        if row is not None:
            return str(row["canonical_key"])
    return normalized


def resolve_space_lookup_keys(conn: sqlite3.Connection, *, user_id: str, space_key: str) -> list[str]:
    canonical_key = canonicalize_space_key(conn, user_id=user_id, space_key=space_key)
    keys = [canonical_key]
    if not _table_exists(conn, "space_aliases"):
        return keys
    rows = conn.execute(
        """
        SELECT alias_key
        FROM space_aliases
        WHERE user_id = ? AND canonical_key = ?
        ORDER BY alias_key ASC
        """,
        (user_id, canonical_key),
    ).fetchall()
    for row in rows:
        alias_key = str(row["alias_key"])
        if alias_key and alias_key not in keys:
            keys.append(alias_key)
    return keys


def _register_space_alias(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    alias_key: str,
    canonical_key: str,
    reason: str,
) -> None:
    if not alias_key or alias_key == canonical_key or not _table_exists(conn, "space_aliases"):
        return
    conn.execute(
        """
        INSERT INTO space_aliases (user_id, alias_key, canonical_key, reason)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, alias_key)
        DO UPDATE SET canonical_key = excluded.canonical_key, reason = excluded.reason
        """,
        (user_id, alias_key, canonical_key, reason),
    )


def _migrate_space_references(
    conn: sqlite3.Connection,
    *,
    from_space_id: str,
    to_space_id: str,
) -> None:
    if from_space_id == to_space_id:
        return
    for table_name in ("cards", "evidence", "interaction_events"):
        if not _table_exists(conn, table_name):
            continue
        conn.execute(
            f"UPDATE {table_name} SET space_id = ? WHERE space_id = ?",
            (to_space_id, from_space_id),
        )


def _meta_dict(meta_json: str) -> dict[str, Any]:
    try:
        loaded = json.loads(meta_json)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def get_or_create_space(conn: sqlite3.Connection, user_id: str, resolved: ResolvedSpace) -> str:
    canonical_key = canonicalize_space_key(conn, user_id=user_id, space_key=resolved.key) or resolved.key
    resolved_meta = _meta_dict(resolved.meta_json)
    if resolved.alias_keys:
        resolved_meta["alias_keys"] = list(dict.fromkeys([*resolved_meta.get("alias_keys", []), *resolved.alias_keys]))
    canonical_meta_json = json.dumps(resolved_meta, separators=(",", ":"))

    row = _load_space_row(conn, user_id=user_id, key=canonical_key)
    if row:
        space_id = str(row["id"])
        conn.execute(
            "UPDATE spaces SET label = ?, meta_json = ? WHERE id = ?;",
            (resolved.label, canonical_meta_json, space_id),
        )
    else:
        space_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-space:{user_id}:{canonical_key}"))
        conn.execute(
            """
            INSERT INTO spaces (id, user_id, key, label, meta_json)
            VALUES (?, ?, ?, ?, ?);
            """,
            (space_id, user_id, canonical_key, resolved.label, canonical_meta_json),
        )

    alias_keys = []
    for raw_alias in resolved.alias_keys:
        alias_key = str(raw_alias or "").strip()
        if not alias_key or alias_key == canonical_key:
            continue
        alias_keys.append(alias_key)
        _register_space_alias(
            conn,
            user_id=user_id,
            alias_key=alias_key,
            canonical_key=canonical_key,
            reason="resolved_space_alias",
        )
        alias_row = _load_space_row(conn, user_id=user_id, key=alias_key)
        if alias_row is not None:
            _migrate_space_references(
                conn,
                from_space_id=str(alias_row["id"]),
                to_space_id=space_id,
            )

    conn.commit()
    return space_id


def get_space_summary(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    space_key: str,
) -> dict[str, Any]:
    canonical_key = canonicalize_space_key(conn, user_id=user_id, space_key=space_key)
    row = _load_space_row(conn, user_id=user_id, key=canonical_key)
    if row is None:
        raise ValueError(f"space_not_found:{space_key}")
    lookup_keys = resolve_space_lookup_keys(conn, user_id=user_id, space_key=canonical_key)
    return {
        "id": str(row["id"]),
        "key": canonical_key,
        "label": str(row["label"] or canonical_key),
        "meta": _meta_dict(str(row["meta_json"] or "{}")),
        "lookup_keys": lookup_keys,
    }

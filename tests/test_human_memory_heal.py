from __future__ import annotations

import json

from muninn.human_memory.bootstrap import (
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from muninn.human_memory.cards import card_upsert
from muninn.human_memory.heal import run_heal
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _seed_space(conn, key: str, label: str) -> ResolvedSpace:
    resolved = ResolvedSpace(
        key=key,
        label=label,
        meta_json=json.dumps({"root_path": f"/tmp/{label}"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return resolved


def test_run_heal_reports_duplicates_without_applying(tmp_path) -> None:
    db_path = tmp_path / "human_memory_heal_report.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = _seed_space(conn, "repo:healreport123456", "heal-report")

    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        title="Prefer strict scope first",
        summary="Use strict retrieval before falling back to global scope.",
        body="First body.",
        dedupe_by_fingerprint=False,
    )
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        title="Prefer strict scope first",
        summary="Use strict retrieval before falling back to global scope.",
        body="Second body.",
        dedupe_by_fingerprint=False,
    )

    report = run_heal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        apply=False,
        window_days=30,
    )
    assert report["actions_applied"] == 0
    assert len(report["duplicates_by_fingerprint"]) >= 1
    conn.close()


def test_run_heal_apply_merges_duplicates(tmp_path) -> None:
    db_path = tmp_path / "human_memory_heal_apply.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = _seed_space(conn, "repo:healapply1234567", "heal-apply")

    first = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="runbook",
        title="Check Muninn health endpoints",
        summary="Call /health and /v0/memory/version to validate service reachability.",
        body="Use curl.",
        dedupe_by_fingerprint=False,
    )
    second = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="runbook",
        title="Check Muninn health endpoints",
        summary="Call /health and /v0/memory/version to validate service reachability.",
        body="Use curl with timers.",
        dedupe_by_fingerprint=False,
    )
    assert first != second

    report = run_heal(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        apply=True,
        window_days=30,
        max_actions=5,
    )
    assert report["actions_applied"] >= 1
    assert report["applied"]

    active_count_row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND s.key = ?
          AND c.status = 'active'
        """,
        (DEFAULT_USER_ID, resolved.key),
    ).fetchone()
    assert active_count_row is not None
    assert int(active_count_row["n"]) == 1
    conn.close()

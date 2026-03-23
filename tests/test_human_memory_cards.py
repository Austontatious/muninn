from __future__ import annotations

import json

from muninn.human_memory.bootstrap import (
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from muninn.human_memory.cards import (
    card_supersede,
    card_upsert,
    cards_merge,
    cards_recent,
    cards_search,
)
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def test_cards_upsert_recent_search_with_evidence(tmp_path) -> None:
    db_path = tmp_path / "human_memory_cards.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    resolved = ResolvedSpace(
        key="repo:abc123def4567890",
        label="muninn",
        meta_json=json.dumps({"root_path": "/mnt/data/Muninn"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)

    card_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        tags=["Schema", "invariants"],
        title="Use global space as real row",
        summary="Global space is explicit and never NULL.",
        body="All cards and evidence require space_id; global is a real space row.",
        created_by_client_name="codex-vscode",
        evidence_refs=[
            {
                "type": "commit",
                "ref": "abc1234",
                "excerpt": "Add global space bootstrapping",
            }
        ],
    )

    recent = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kinds=["decision"],
        limit=10,
        include_body=False,
    )
    assert len(recent) == 1
    assert recent[0]["id"] == card_id
    assert "body" not in recent[0]
    assert recent[0]["tags"] == ["invariants", "schema"]

    hits = cards_search(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        query="global row",
        kinds=["decision"],
        limit=10,
        include_body=True,
    )
    assert len(hits) == 1
    assert hits[0]["id"] == card_id
    assert "body" in hits[0]
    assert hits[0]["tags"] == ["invariants", "schema"]

    tagged = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        tags=["schema"],
    )
    assert len(tagged) == 1

    not_tagged = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        tags=["missing-tag"],
    )
    assert len(not_tagged) == 0

    join_row = conn.execute("SELECT count(*) AS n FROM card_evidence WHERE card_id = ?", (card_id,)).fetchone()
    assert join_row is not None
    assert int(join_row["n"]) == 1

    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        card_id=card_id,
        kind="decision",
        status="archived",
        tags=["schema"],
        title="Use global space as real row",
        summary="Global space is explicit and never NULL.",
        body="All cards and evidence require space_id; global is a real space row.",
        created_by_client_name="codex-vscode",
    )
    active_after_archive = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        status="active",
    )
    assert len(active_after_archive) == 0

    archived = cards_recent(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        status="archived",
    )
    assert len(archived) == 1
    assert archived[0]["id"] == card_id
    conn.close()


def test_card_upsert_dedupes_by_fingerprint(tmp_path) -> None:
    db_path = tmp_path / "human_memory_cards_dedupe.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    resolved = ResolvedSpace(
        key="repo:dedupe1234567890",
        label="dedupe",
        meta_json=json.dumps({"root_path": "/tmp/dedupe"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)

    first_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        title="Use memory discipline",
        summary="Read recent cards before coding and write at stable boundaries.",
        body="Original body",
    )
    second_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        title="Use memory discipline",
        summary="Read recent cards before coding and write at stable boundaries.",
        body="Updated body",
    )
    assert first_id == second_id

    count_row = conn.execute("SELECT COUNT(*) AS n FROM cards").fetchone()
    assert count_row is not None
    assert int(count_row["n"]) == 1
    conn.close()


def test_card_supersede_creates_lineage(tmp_path) -> None:
    db_path = tmp_path / "human_memory_cards_supersede.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    resolved = ResolvedSpace(
        key="repo:supersede12345678",
        label="supersede",
        meta_json=json.dumps({"root_path": "/tmp/supersede"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)

    old_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="constraint",
        title="MUNINN_BASE_URL must be reachable",
        summary="Service URL must resolve from runtime environment.",
        body="Initial constraint body.",
    )
    out = card_supersede(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        old_card_id=old_id,
        kind="constraint",
        title="MUNINN_BASE_URL must be reachable from the caller runtime",
        summary="The base URL differs between host and container runtimes.",
        body="Use 127.0.0.1 on host and muninn DNS in compose.",
        relation_type="supersedes",
    )
    assert out["old_card_id"] == old_id
    assert out["new_card_id"] != old_id

    old_row = conn.execute("SELECT status FROM cards WHERE id = ?", (old_id,)).fetchone()
    assert old_row is not None
    assert str(old_row["status"]) == "superseded"

    rel_row = conn.execute(
        """
        SELECT relation_type
        FROM card_relations
        WHERE from_card_id = ? AND to_card_id = ?
        """,
        (old_id, out["new_card_id"]),
    ).fetchone()
    assert rel_row is not None
    assert str(rel_row["relation_type"]) == "supersedes"
    conn.close()


def test_cards_merge_supersedes_inputs_and_links_duplicates(tmp_path) -> None:
    db_path = tmp_path / "human_memory_cards_merge.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    resolved = ResolvedSpace(
        key="repo:merge123456789012",
        label="merge",
        meta_json=json.dumps({"root_path": "/tmp/merge"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)

    first = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="runbook",
        title="Run muninn status first",
        summary="Run status checks before deeper debugging.",
        body="Run status.",
        tags=["ops"],
    )
    second = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="runbook",
        title="Run muninn status first",
        summary="Run status checks before deeper debugging.",
        body="Run status with timeout detail.",
        tags=["ops", "debug"],
        dedupe_by_fingerprint=False,
    )
    assert first != second

    merged = cards_merge(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        card_ids=[first, second],
        kind="runbook",
        title="Run Muninn diagnostics before API changes",
        summary="Merge duplicated operational guidance into one canonical runbook.",
        body="1) status 2) audit 3) doctor",
        relation_type="duplicates",
    )
    merged_id = str(merged["merged_card_id"])
    assert merged_id not in {first, second}
    assert set(merged["superseded_card_ids"]) == {first, second}

    status_rows = conn.execute(
        "SELECT id, status FROM cards WHERE id IN (?, ?)",
        (first, second),
    ).fetchall()
    assert {str(row["status"]) for row in status_rows} == {"superseded"}

    relation_count_row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM card_relations
        WHERE to_card_id = ? AND relation_type = 'duplicates'
        """,
        (merged_id,),
    ).fetchone()
    assert relation_count_row is not None
    assert int(relation_count_row["n"]) == 2
    conn.close()

from __future__ import annotations

import uuid

from muninn.human_memory.bootstrap import (
    DEFAULT_CLIENT_NAME,
    DEFAULT_USER_ID,
    GLOBAL_SPACE_KEY,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)


def test_bootstrap_defaults_is_idempotent_and_deterministic(tmp_path) -> None:
    db_path = tmp_path / "human_memory.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    bootstrap_defaults(conn)

    user = conn.execute("SELECT id FROM users WHERE id = ?", (DEFAULT_USER_ID,)).fetchone()
    assert user is not None

    client = conn.execute("SELECT id, name FROM clients WHERE name = ?", (DEFAULT_CLIENT_NAME,)).fetchone()
    assert client is not None
    assert str(client["id"]) == str(uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-client:{DEFAULT_CLIENT_NAME}"))

    space = conn.execute(
        "SELECT id, key, user_id FROM spaces WHERE user_id = ? AND key = ?",
        (DEFAULT_USER_ID, GLOBAL_SPACE_KEY),
    ).fetchone()
    assert space is not None
    assert str(space["id"]) == str(
        uuid.uuid5(uuid.NAMESPACE_DNS, f"muninn-space:{DEFAULT_USER_ID}:{GLOBAL_SPACE_KEY}")
    )

    cards_cols = {
        str(row["name"]) for row in conn.execute("PRAGMA table_info(cards)").fetchall()
    }
    assert "fingerprint" in cards_cols
    assert "is_unstable" in cards_cols
    assert "quarantine_reason" in cards_cols

    relation_table = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'card_relations'"
    ).fetchone()
    assert relation_table is not None
    conn.close()

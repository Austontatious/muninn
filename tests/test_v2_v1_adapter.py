from __future__ import annotations

import json
import os
import sqlite3

from muninn.human_memory.bootstrap import (
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from muninn.human_memory.cards import card_supersede, card_upsert
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.v2 import SQLiteMemoryStore
from muninn.v2.adapters import V1ImportAdapter, V1ReadAdapter


def _seed_v1_db(db_path) -> tuple[str, str, str]:
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:v2adapter0000001",
        label="v2-adapter",
        meta_json=json.dumps({"root_path": "/tmp/v2-adapter"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    old_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind="decision",
        title="Keep v1 live",
        summary="v2 must be adjacent",
        body="Do not mutate v1 during v2 reads.",
        tags=["compat"],
        evidence_refs=[{"type": "file", "ref": "/tmp/source.py:7", "excerpt": "evidence"}],
    )
    out = card_supersede(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        old_card_id=old_id,
        kind="decision",
        title="Keep v1 live with v2 adjacent",
        summary="v2 reads and imports without changing v1",
        body="Adapter maps v1 cards into v2 primitives.",
    )
    conn.close()
    return resolved.key, old_id, str(out["new_card_id"])


def _v1_counts(db_path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            "cards": int(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]),
            "evidence": int(conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]),
            "relations": int(conn.execute("SELECT COUNT(*) FROM card_relations").fetchone()[0]),
        }
    finally:
        conn.close()


def test_v1_read_adapter_maps_cards_evidence_and_relations_without_mutation(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    space_key, old_id, new_id = _seed_v1_db(db_path)
    before = _v1_counts(db_path)

    reader = V1ReadAdapter(db_path)
    cards = reader.list_cards(space_key=space_key)
    associations = reader.list_associations()
    profiles = reader.list_ontology_profiles()

    after = _v1_counts(db_path)
    assert after == before
    assert {card.id for card in cards} == {old_id, new_id}
    old_card = next(card for card in cards if card.id == old_id)
    assert old_card.scope_key == space_key
    assert old_card.evidence[0].evidence_type == "file"
    assert old_card.metadata["source_system"] == "muninn_v1"
    assert associations[0].source_id == old_id
    assert associations[0].target_id == new_id
    assert associations[0].association_type == "supersedes"
    assert any(profile.metadata["space_key"] == space_key for profile in profiles)


def test_v1_import_adapter_writes_only_to_v2_store(tmp_path) -> None:
    v1_path = tmp_path / "human_memory_v1.db"
    space_key, old_id, _new_id = _seed_v1_db(v1_path)
    before = _v1_counts(v1_path)

    v2_store = SQLiteMemoryStore(tmp_path / "muninn_v2.db")
    importer = V1ImportAdapter(V1ReadAdapter(v1_path), v2_store)
    counts = importer.import_all(space_key=space_key)

    assert _v1_counts(v1_path) == before
    assert counts["cards"] == 2
    assert counts["associations"] == 1
    assert v2_store.get_card(old_id).metadata["source_system"] == "muninn_v1"  # type: ignore[union-attr]


def test_v1_read_adapter_uses_read_only_sqlite_connection(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    _seed_v1_db(db_path)
    reader = V1ReadAdapter(db_path)

    conn = reader._connect()
    try:
        try:
            conn.execute("INSERT INTO tags (id, name) VALUES ('bad', 'bad')")
        except sqlite3.OperationalError as exc:
            assert "readonly" in str(exc).lower() or "read-only" in str(exc).lower()
        else:
            raise AssertionError("read-only adapter allowed a write")
    finally:
        conn.close()


def test_importing_v2_modules_does_not_create_v1_or_v2_databases(tmp_path, monkeypatch) -> None:
    v1_db = tmp_path / "v1.db"
    human_db = tmp_path / "human_memory.db"
    v2_db = tmp_path / "v2.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(v1_db))
    monkeypatch.setenv("MUNINN_HUMAN_MEMORY_DB_PATH", str(human_db))
    monkeypatch.setenv("MUNINN_V2_DB_PATH", str(v2_db))

    __import__("muninn.v2")
    __import__("muninn.v2.core.models")
    __import__("muninn.v2.storage.sqlite_store")
    __import__("muninn.v2.adapters.v1_read_adapter")

    assert not os.path.exists(v1_db)
    assert not os.path.exists(human_db)
    assert not os.path.exists(v2_db)

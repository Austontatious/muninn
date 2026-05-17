from __future__ import annotations

import sqlite3

from muninn.v2 import MemoryCard, SQLiteMemoryStore
from muninn.v2.indexes import SQLiteDerivedIndexProvider
from muninn.v2.retrieval import recall_with_fallback


def _seed_v2(tmp_path):
    db_path = tmp_path / "v2_indexes.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    cards = [
        store.create_card(
            MemoryCard(
                id="card-alpha",
                kind="decision",
                title="Derived indexes are optional",
                summary="Vectors are rebuildable diagnostics, not canonical memory.",
                body="The v2 index can be rebuilt from canonical cards.",
                scope_key="repo:test",
                updated_at="2026-05-13T00:00:00Z",
            )
        ),
        store.create_card(
            MemoryCard(
                id="card-beta",
                kind="runbook",
                title="Lexical fallback handles missing vector backends",
                summary="When no derived index exists, lexical recall still reports provisional results.",
                body="sqlite_vec absence must not block core operation.",
                scope_key="repo:test",
                updated_at="2026-05-13T00:01:00Z",
            )
        ),
    ]
    return db_path, cards


def test_index_status_degrades_without_sqlite_vec_or_index_table(tmp_path) -> None:
    db_path, cards = _seed_v2(tmp_path)
    provider = SQLiteDerivedIndexProvider(db_path, records=cards)

    status = provider.status()

    assert status.backend_available is True
    assert status.eligible_records == 2
    assert status.indexed_records == 0
    assert status.missing_records == 2
    assert status.degraded is True
    assert "index_table_missing" in status.reason


def test_rebuild_dry_run_does_not_create_index_table(tmp_path) -> None:
    db_path, cards = _seed_v2(tmp_path)
    provider = SQLiteDerivedIndexProvider(db_path, records=cards)

    report = provider.rebuild(cards, dry_run=True)

    assert report["dry_run"] is True
    assert report["planned_upserts"] == 2
    assert report["written_upserts"] == 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_vector_indexes'"
        ).fetchone()
    assert row is None


def test_explicit_rebuild_write_indexes_and_detects_stale_records(tmp_path) -> None:
    db_path, cards = _seed_v2(tmp_path)
    provider = SQLiteDerivedIndexProvider(db_path, records=cards)

    report = provider.rebuild(cards, dry_run=False)
    status = provider.status()

    assert report["written_upserts"] == 2
    assert status.indexed_records == 2
    assert status.missing_records == 0
    mutated = [
        cards[0],
        MemoryCard(
            id="card-beta",
            kind="runbook",
            title="Lexical fallback changed",
            summary="A changed canonical card makes the derived index stale.",
            scope_key="repo:test",
            updated_at="2026-05-13T00:02:00Z",
        ),
    ]
    stale_status = SQLiteDerivedIndexProvider(db_path, records=mutated).status()
    assert stale_status.stale_records == 1


def test_query_falls_back_to_lexical_when_vector_index_missing(tmp_path) -> None:
    db_path, cards = _seed_v2(tmp_path)
    provider = SQLiteDerivedIndexProvider(db_path, records=cards)

    payload = recall_with_fallback(cards, "sqlite vec fallback", provider=provider, limit=5)

    assert payload["backend"] == "lexical_fallback"
    assert payload["fallback_used"] is True
    assert payload["results"][0]["record_id"] == "card-beta"

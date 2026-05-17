from __future__ import annotations

import json
import sqlite3

from muninn.v2 import MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main


def _seed_v2_db(tmp_path):
    db_path = tmp_path / "cli_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    store.create_card(
        MemoryCard(
            id="card-cli-index",
            kind="decision",
            title="Explicit v2 index command",
            summary="Derived index commands require explicit v2 DB paths.",
            body="No production defaults are used by v2 index commands.",
            scope_key="repo:cli",
        )
    )
    return db_path


def test_index_health_requires_explicit_v2_db(tmp_path) -> None:
    assert main(["index-health", "--out-dir", str(tmp_path / "out")]) == 2


def test_index_health_writes_reports(tmp_path, capsys) -> None:
    db_path = _seed_v2_db(tmp_path)
    out_dir = tmp_path / "health"

    code = main(["index-health", "--v2-db", str(db_path), "--out-dir", str(out_dir)])

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["mode"] == "index_health"
    assert payload["index_status"]["eligible_records"] == 1
    assert (out_dir / "index_health_report.json").exists()
    assert (out_dir / "index_health_report.md").exists()


def test_index_rebuild_is_dry_run_until_write_index_is_explicit(tmp_path, capsys) -> None:
    db_path = _seed_v2_db(tmp_path)
    out_dir = tmp_path / "rebuild"

    code = main(["index-rebuild", "--v2-db", str(db_path), "--out-dir", str(out_dir)])

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["dry_run"] is True
    assert payload["written_upserts"] == 0
    with sqlite3.connect(db_path) as conn:
        assert (
            conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_vector_indexes'"
            ).fetchone()
            is None
        )

    code = main(["index-rebuild", "--v2-db", str(db_path), "--out-dir", str(out_dir), "--write-index"])
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["dry_run"] is False
    assert payload["written_upserts"] == 1
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM v2_vector_indexes").fetchone()[0]
    assert count == 1

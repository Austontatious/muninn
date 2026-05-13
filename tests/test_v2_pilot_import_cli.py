from __future__ import annotations

import json
import sqlite3

from muninn.human_memory.bootstrap import (
    DEFAULT_USER_ID,
    apply_init_schema,
    bootstrap_defaults,
    open_db,
)
from muninn.human_memory.cards import card_supersede, card_upsert
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import _connect_v1_readonly, _connect_v2_readonly, main, run_pilot_import


def _seed_v1_db(db_path, *, space_key: str = "repo:nullsignalfixture") -> tuple[str, str, str]:
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key=space_key,
        label="Null_Signal",
        meta_json=json.dumps(
            {
                "root_path": str(db_path.parent / "Null_Signal"),
                "git_remote": "https://github.com/example/Null_Signal.git",
                "git_remote_norm": "https://github.com/example/null_signal",
            },
            separators=(",", ":"),
        ),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    old_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        kind="decision",
        title="Pilot import remains dry-run",
        summary="The pilot maps v1 cards without mutating v1",
        body="Null_Signal-like fixture cards should project into v2 primitives.",
        tags=["pilot"],
        evidence_refs=[{"type": "file", "ref": "/tmp/Null_Signal/README.md:1", "excerpt": "pilot"}],
    )
    out = card_supersede(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        old_card_id=old_id,
        kind="decision",
        title="Pilot import has relation coverage",
        summary="The fixture includes a supersedes relation",
        body="Relations should map to v2 MemoryAssociation records.",
    )
    conn.close()
    return space_key, old_id, str(out["new_card_id"])


def _v1_row_counts(db_path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        return {
            row[0]: int(conn.execute(f'SELECT COUNT(*) FROM "{row[0]}"').fetchone()[0])
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
    finally:
        conn.close()


def _run_args(tmp_path, *, write_v2: bool = False) -> list[str]:
    project_path = tmp_path / "Null_Signal"
    project_path.mkdir(exist_ok=True)
    args = [
        "pilot-import",
        "--v1-db",
        str(tmp_path / "human_memory_v1.db"),
        "--v2-db",
        str(tmp_path / "requested_v2.db"),
        "--space-key",
        "repo:nullsignalfixture",
        "--project-path",
        str(project_path),
        "--out-dir",
        str(tmp_path / "pilot_out"),
    ]
    if write_v2:
        args.append("--write-v2")
    return args


def _seed_v1_recall_db(db_path, *, space_key: str = "repo:recallfixture") -> tuple[str, str]:
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key=space_key,
        label="RecallFixture",
        meta_json=json.dumps({"root_path": str(db_path.parent / "RecallFixture")}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    alpha_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        kind="decision",
        title="Alpha sonar contact",
        summary="Alpha sonar recall parity card",
        body="Alpha sonar evidence should overlap with v2.",
        evidence_refs=[{"type": "file", "ref": "/tmp/alpha.md:1", "excerpt": "alpha sonar"}],
    )
    beta_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        kind="decision",
        title="Beta sonar contact",
        summary="Beta sonar is expected to be missing from v2",
        body="Beta sonar exists in v1 only for missing-record reporting.",
        evidence_refs=[{"type": "file", "ref": "/tmp/beta.md:1", "excerpt": "beta sonar"}],
    )
    conn.close()
    return alpha_id, beta_id


def _seed_v2_recall_db(db_path, *, space_key: str = "repo:recallfixture", alpha_id: str) -> None:
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    store.create_card(
        MemoryCard(
            id=alpha_id,
            kind="decision",
            title="Alpha sonar contact",
            summary="Alpha sonar recall parity card",
            body="Alpha sonar evidence should overlap with v2.",
            scope_key=space_key,
            evidence=[EvidenceRef(id="alpha-evidence", evidence_type="file", ref="/tmp/alpha.md:1")],
        )
    )
    store.create_card(
        MemoryCard(
            id="extra-v2-card",
            kind="decision",
            title="Extra sonar contact",
            summary="Extra sonar card exists only in v2",
            body="Extra sonar card should be reported as extra_from_v2.",
            scope_key=space_key,
        )
    )


def _recall_args(tmp_path, *, queries: list[str] | None = None, query_file: str | None = None, v2_db: str | None = None) -> list[str]:
    project_path = tmp_path / "RecallFixture"
    project_path.mkdir(exist_ok=True)
    args = [
        "recall-parity",
        "--v1-db",
        str(tmp_path / "human_memory_v1.db"),
        "--v2-db",
        v2_db or str(tmp_path / "recall_v2.db"),
        "--space-key",
        "repo:recallfixture",
        "--project-path",
        str(project_path),
        "--out-dir",
        str(tmp_path / "recall_out"),
        "--limit",
        "10",
        "--include-evidence",
        "--include-ranking",
        "--include-explanations",
    ]
    for query in queries or []:
        args.extend(["--query", query])
    if query_file:
        args.extend(["--query-file", query_file])
    return args


def test_pilot_import_cli_requires_explicit_safety_arguments(tmp_path) -> None:
    required = {
        "--v1-db": str(tmp_path / "human_memory_v1.db"),
        "--v2-db": str(tmp_path / "requested_v2.db"),
        "--space-key": "repo:nullsignalfixture",
        "--project-path": str(tmp_path / "Null_Signal"),
        "--out-dir": str(tmp_path / "pilot_out"),
    }
    for missing in ("--v1-db", "--v2-db", "--space-key", "--project-path", "--out-dir"):
        args = ["pilot-import"]
        for option, value in required.items():
            if option == missing:
                continue
            args.extend([option, value])
        assert main(args) == 2


def test_pilot_import_uses_read_only_v1_connection(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    _seed_v1_db(db_path)
    conn = _connect_v1_readonly(db_path)
    try:
        try:
            conn.execute("INSERT INTO tags (id, name) VALUES ('bad', 'bad')")
        except sqlite3.OperationalError as exc:
            assert "readonly" in str(exc).lower() or "read-only" in str(exc).lower()
        else:
            raise AssertionError("pilot v1 connection allowed a write")
    finally:
        conn.close()


def test_dry_run_writes_only_scratch_v2_db_and_reports(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    space_key, _old_id, _new_id = _seed_v1_db(db_path)
    before = _v1_row_counts(db_path)
    namespace = main(_run_args(tmp_path))

    assert namespace == 0
    assert _v1_row_counts(db_path) == before
    assert not (tmp_path / "requested_v2.db").exists()
    assert (tmp_path / "pilot_out" / "scratch_v2.db").exists()

    report = json.loads((tmp_path / "pilot_out" / "pilot_import_report.json").read_text())
    assert report["dry_run"] is True
    assert report["space_key_canonical"] == space_key
    assert report["v1_row_counts_changed"] is False
    assert report["counts"]["migrated_cards"] == 2
    assert report["counts"]["ledger_entries"] == 6
    assert report["counts"]["fidelity_failures"] == 0


def test_pilot_import_reports_row_count_verification(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    _seed_v1_db(db_path)

    assert main(_run_args(tmp_path)) == 0
    rows = json.loads((tmp_path / "pilot_out" / "v1_row_count_before_after.json").read_text())
    assert rows
    assert all(row["changed"] is False for row in rows)
    assert any(row["table"] == "cards" and row["before"] == row["after"] == 2 for row in rows)


def test_pilot_import_reports_unsupported_records(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    space_key, _old_id, _new_id = _seed_v1_db(db_path)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        space_id = conn.execute("SELECT id FROM spaces WHERE key = ?", (space_key,)).fetchone()["id"]
        conn.execute(
            """
            INSERT INTO interaction_events (id, user_id, space_id, event_type, actor, summary)
            VALUES ('event-1', ?, ?, 'feedback', 'codex', 'unsupported event')
            """,
            (DEFAULT_USER_ID, space_id),
        )
        conn.commit()
    finally:
        conn.close()

    assert main(_run_args(tmp_path)) == 0
    unsupported = json.loads((tmp_path / "pilot_out" / "unsupported_records.json").read_text())
    assert unsupported["total_unsupported_records"] >= 1
    assert any(
        item["record_type"] == "interaction_events" and item["count"] == 1
        for item in unsupported["unsupported_record_types"]
    )


def test_null_signal_like_fixture_maps_cards_evidence_and_relations(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    space_key, old_id, new_id = _seed_v1_db(db_path)
    project_path = tmp_path / "Null_Signal"
    project_path.mkdir(exist_ok=True)
    report = run_pilot_import(
        type(
            "Args",
            (),
            {
                "v1_db": str(db_path),
                "v2_db": str(tmp_path / "requested_v2.db"),
                "space_key": space_key,
                "project_path": str(project_path),
                "out_dir": str(tmp_path / "pilot_out"),
                "dry_run": False,
                "write_v2": False,
                "allow_existing_v2": False,
                "limit": None,
                "include_relations": True,
                "include_evidence": True,
                "strict": False,
                "json_report": None,
            },
        )()
    )

    assert report["counts"]["migrated_cards"] == 2
    assert report["counts"]["migrated_evidence_refs"] == 1
    assert report["counts"]["migrated_associations"] == 1
    assert report["counts"]["created_entities"] == 1
    cards = [
        json.loads(line)
        for line in (tmp_path / "pilot_out" / "migrated_cards.jsonl").read_text().splitlines()
    ]
    assert {card["id"] for card in cards} == {old_id, new_id}
    assert all(card["entity_ids"] == [f"v1-project:{space_key}"] for card in cards)
    associations = [
        json.loads(line)
        for line in (tmp_path / "pilot_out" / "migrated_associations.jsonl").read_text().splitlines()
    ]
    assert associations[0]["source_id"] == old_id
    assert associations[0]["target_id"] == new_id

    ledger = [
        json.loads(line)
        for line in (tmp_path / "pilot_out" / "migration_ledger.jsonl").read_text().splitlines()
    ]
    assert len(ledger) == 6
    assert {entry["source_table"] for entry in ledger} == {
        "spaces",
        "cards",
        "evidence",
        "card_relations",
    }
    assert all(entry["fidelity_status"] == "ok" for entry in ledger)

    checksums = json.loads((tmp_path / "pilot_out" / "migration_checksums.json").read_text())
    assert checksums["algorithm"] == "sha256"
    assert checksums["ledger"]["entries"] == len(ledger)
    assert len(checksums["source"]["aggregate"]) == 64
    assert len(checksums["target"]["aggregate"]) == 64

    fidelity = json.loads((tmp_path / "pilot_out" / "record_fidelity_report.json").read_text())
    assert fidelity["summary"]["fidelity_passed"] is True
    assert fidelity["summary"]["cards_checked"] == 2
    assert fidelity["summary"]["evidence_refs_checked"] == 1
    assert fidelity["summary"]["associations_checked"] == 1
    assert fidelity["summary"]["failures"] == 0


def test_write_v2_requires_explicit_flag(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    _seed_v1_db(db_path)

    assert main(_run_args(tmp_path)) == 0
    assert not (tmp_path / "requested_v2.db").exists()

    assert main(_run_args(tmp_path, write_v2=True)) == 0
    assert (tmp_path / "requested_v2.db").exists()


def test_recall_parity_requires_explicit_safety_arguments(tmp_path) -> None:
    required = {
        "--v1-db": str(tmp_path / "human_memory_v1.db"),
        "--v2-db": str(tmp_path / "recall_v2.db"),
        "--space-key": "repo:recallfixture",
        "--project-path": str(tmp_path / "RecallFixture"),
        "--out-dir": str(tmp_path / "recall_out"),
    }
    for missing in ("--v1-db", "--v2-db", "--space-key", "--project-path", "--out-dir"):
        args = ["recall-parity", "--query", "sonar"]
        for option, value in required.items():
            if option == missing:
                continue
            args.extend([option, value])
        assert main(args) == 2


def test_recall_parity_fails_when_query_set_empty(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    alpha_id, _beta_id = _seed_v1_recall_db(db_path)
    _seed_v2_recall_db(tmp_path / "recall_v2.db", alpha_id=alpha_id)

    assert main(_recall_args(tmp_path)) == 2


def test_recall_parity_fails_when_v2_db_missing(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    _seed_v1_recall_db(db_path)

    assert main(_recall_args(tmp_path, queries=["sonar"], v2_db=str(tmp_path / "missing_v2.db"))) == 2


def test_recall_parity_opens_v2_read_only(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    alpha_id, _beta_id = _seed_v1_recall_db(db_path)
    v2_db = tmp_path / "recall_v2.db"
    _seed_v2_recall_db(v2_db, alpha_id=alpha_id)

    conn = _connect_v2_readonly(v2_db)
    try:
        try:
            conn.execute("INSERT INTO v2_schema_info (key, value) VALUES ('bad', 'bad')")
        except sqlite3.OperationalError as exc:
            assert "readonly" in str(exc).lower() or "read-only" in str(exc).lower()
        else:
            raise AssertionError("recall parity v2 connection allowed a write")
    finally:
        conn.close()


def test_recall_parity_loads_query_file_and_repeatable_queries(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    alpha_id, _beta_id = _seed_v1_recall_db(db_path)
    _seed_v2_recall_db(tmp_path / "recall_v2.db", alpha_id=alpha_id)
    query_file = tmp_path / "queries.json"
    query_file.write_text(json.dumps({"queries": ["sonar"]}), encoding="utf-8")

    assert main(_recall_args(tmp_path, queries=["alpha"], query_file=str(query_file))) == 0
    report = json.loads((tmp_path / "recall_out" / "recall_parity_report.json").read_text())
    assert report["queries"] == ["alpha", "sonar"]
    copied = json.loads((tmp_path / "recall_out" / "readyplayer1_recall_queries.json").read_text())
    assert copied["queries"] == ["alpha", "sonar"]


def test_recall_parity_reports_missing_extra_ranking_and_evidence_without_mutation(tmp_path) -> None:
    db_path = tmp_path / "human_memory_v1.db"
    alpha_id, beta_id = _seed_v1_recall_db(db_path)
    v2_db = tmp_path / "recall_v2.db"
    _seed_v2_recall_db(v2_db, alpha_id=alpha_id)
    before_v1 = _v1_row_counts(db_path)
    before_v2 = _v1_row_counts(v2_db)

    assert main(_recall_args(tmp_path, queries=["sonar"])) == 0

    assert _v1_row_counts(db_path) == before_v1
    assert _v1_row_counts(v2_db) == before_v2
    report = json.loads((tmp_path / "recall_out" / "recall_parity_report.json").read_text())
    assert report["v1_row_counts_changed"] is False
    assert report["v2_row_counts_changed"] is False
    assert report["aggregate"]["total_queries"] == 1
    assert report["aggregate"]["total_missing_from_v2"] >= 1
    assert report["aggregate"]["total_extra_from_v2"] >= 1

    missing = json.loads((tmp_path / "recall_out" / "missing_from_v2.json").read_text())
    assert any(record["id"] == beta_id for group in missing["records"] for record in group["records"])
    extra = json.loads((tmp_path / "recall_out" / "extra_from_v2.json").read_text())
    assert any(record["id"] == "extra-v2-card" for group in extra["records"] for record in group["records"])
    deltas = json.loads((tmp_path / "recall_out" / "ranking_deltas.json").read_text())
    assert any(delta["card_id"] == alpha_id for delta in deltas["records"])
    evidence = json.loads((tmp_path / "recall_out" / "evidence_parity_report.json").read_text())
    assert evidence["summary"]["checks"] >= 1
    assert (tmp_path / "recall_out" / "recall_parity_results.jsonl").exists()
    assert (tmp_path / "recall_out" / "recall_parity_report.md").exists()

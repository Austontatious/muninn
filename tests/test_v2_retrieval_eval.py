from __future__ import annotations

import json

from muninn.v2 import MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main
from muninn.v2.eval import load_retrieval_fixture, run_retrieval_eval
from muninn.v2.indexes import SQLiteDerivedIndexProvider


def _seed_v2(tmp_path):
    db_path = tmp_path / "eval_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    cards = [
        store.create_card(
            MemoryCard(
                id="card-present-hit",
                kind="decision",
                title="Derived index diagnostic recall",
                summary="Retrieval eval should find this diagnostic card.",
                scope_key="repo:eval",
            )
        ),
        store.create_card(
            MemoryCard(
                id="card-present-miss",
                kind="decision",
                title="Unrelated archive",
                summary="This canonical card exists but does not match the query.",
                scope_key="repo:eval",
            )
        ),
    ]
    return db_path, cards


def _fixture(tmp_path):
    path = tmp_path / "fixture.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "v2 retrieval eval fixture",
                "defaults": {"limit": 5},
                "cases": [
                    {
                        "id": "hit",
                        "query": "diagnostic recall",
                        "space_key": "repo:eval",
                        "expected_card_ids": ["card-present-hit"],
                    },
                    {
                        "id": "retrieval-mismatch",
                        "query": "missing semantic wording",
                        "space_key": "repo:eval",
                        "expected_card_ids": ["card-present-miss"],
                    },
                    {
                        "id": "record-absent",
                        "query": "absent card",
                        "space_key": "repo:eval",
                        "expected_card_ids": ["card-absent"],
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_retrieval_eval_classifies_absent_vs_mismatch(tmp_path) -> None:
    db_path, cards = _seed_v2(tmp_path)
    fixture = load_retrieval_fixture(_fixture(tmp_path))
    provider = SQLiteDerivedIndexProvider(db_path, records=cards)

    report = run_retrieval_eval(records=cards, fixture=fixture, provider=provider)

    assert report["summary"]["cases"] == 3
    assert report["summary"]["record_absent_count"] == 1
    assert report["summary"]["retrieval_mismatch_count"] == 1
    mismatch = next(case for case in report["cases"] if case["id"] == "retrieval-mismatch")
    assert mismatch["missing_expected"] == [
        {"record_id": "card-present-miss", "classification": "retrieval_mismatch"}
    ]
    absent = next(case for case in report["cases"] if case["id"] == "record-absent")
    assert absent["missing_expected"] == [
        {"record_id": "card-absent", "classification": "record_absent"}
    ]


def test_retrieval_eval_cli_writes_reports(tmp_path, capsys) -> None:
    db_path, _cards = _seed_v2(tmp_path)
    out_dir = tmp_path / "eval"

    code = main(
        [
            "retrieval-eval",
            "--v2-db",
            str(db_path),
            "--fixture",
            str(_fixture(tmp_path)),
            "--out-dir",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["mode"] == "retrieval_eval"
    assert payload["summary"]["record_absent_count"] == 1
    assert (out_dir / "retrieval_eval_report.json").exists()
    assert (out_dir / "retrieval_eval_report.md").exists()

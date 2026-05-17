from __future__ import annotations

import json

from muninn.v2 import EvidenceRef, MemoryCard, RecallEvent, SQLiteMemoryStore
from muninn.v2.cli import main
from muninn.v2.retrieval import hybrid_recall
from muninn.v2.retrieval.reinforcement import (
    REINFORCEMENT_SCHEMA_VERSION,
    ReinforcementWeights,
    apply_reinforcement_state_to_score,
    replay_reinforcement,
)


def _seed_store(tmp_path):
    db_path = tmp_path / "phase_d_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    durable = store.create_card(
        MemoryCard(
            id="durable",
            kind="decision",
            title="Durable project state",
            summary="Important implementation checkpoint.",
            body="This durable memory should survive quiet periods.",
            scope_key="repo:test",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/ARCHITECTURE.md:10")],
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
    )
    useful = store.create_card(
        MemoryCard(
            id="useful",
            kind="runbook",
            title="Useful resume procedure",
            summary="Accepted procedure for resuming work.",
            scope_key="repo:test",
            created_at="2026-05-01T00:00:00Z",
            updated_at="2026-05-01T00:00:00Z",
        )
    )
    noisy = store.create_card(
        MemoryCard(
            id="noisy",
            kind="note",
            title="Noisy background note",
            summary="Confusing background material.",
            tags=["background"],
            scope_key="repo:test",
            created_at="2026-05-01T00:00:00Z",
            updated_at="2026-05-01T00:00:00Z",
        )
    )
    return db_path, store, durable, useful, noisy


def test_recall_event_record_dry_run_does_not_write(tmp_path, capsys) -> None:
    db_path, store, _durable, useful, noisy = _seed_store(tmp_path)

    code = main(
        [
            "recall-event-record",
            "--v2-db",
            str(db_path),
            "--query",
            "resume project",
            "--out-dir",
            str(tmp_path / "event"),
            "--scope-key",
            "repo:test",
            "--accepted-id",
            useful.id,
            "--suppressed-id",
            noisy.id,
            "--created-at",
            "2026-05-17T00:00:00Z",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["schema_version"] == REINFORCEMENT_SCHEMA_VERSION
    assert payload["write_event"] is False
    assert payload["counts"]["recall_events_before"] == 0
    assert payload["counts"]["recall_events_after"] == 0
    assert store.list_recalls() == []
    assert (tmp_path / "event" / "recall_event_record_report.json").exists()
    assert (tmp_path / "event" / "recall_event_record_report.md").exists()


def test_recall_event_record_write_requires_explicit_flag(tmp_path, capsys) -> None:
    db_path, store, _durable, useful, noisy = _seed_store(tmp_path)

    code = main(
        [
            "recall-event-record",
            "--v2-db",
            str(db_path),
            "--query",
            "resume project",
            "--out-dir",
            str(tmp_path / "event"),
            "--scope-key",
            "repo:test",
            "--recalled-id",
            useful.id,
            "--accepted-id",
            useful.id,
            "--suppressed-id",
            noisy.id,
            "--created-at",
            "2026-05-17T00:00:00Z",
            "--write-event",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["write_event"] is True
    recalls = store.list_recalls(scope_key="repo:test")
    assert len(recalls) == 1
    assert recalls[0].accepted_ids == [useful.id]
    assert recalls[0].suppressed_ids == [noisy.id]


def test_reinforcement_replay_is_deterministic_and_explainable() -> None:
    cards = [
        MemoryCard(
            id="durable",
            kind="decision",
            title="Durable project state",
            summary="Important implementation checkpoint.",
            scope_key="repo:test",
            evidence=[EvidenceRef(evidence_type="file", ref="/repo/ARCHITECTURE.md:10")],
            updated_at="2026-01-01T00:00:00Z",
        ),
        MemoryCard(
            id="useful",
            kind="runbook",
            title="Useful resume procedure",
            summary="Accepted procedure for resuming work.",
            scope_key="repo:test",
            updated_at="2026-05-01T00:00:00Z",
        ),
        MemoryCard(
            id="noisy",
            kind="note",
            title="Noisy background note",
            summary="Confusing background material.",
            scope_key="repo:test",
            updated_at="2026-05-01T00:00:00Z",
        ),
    ]
    events = [
        RecallEvent(
            id="event1",
            query="resume project",
            actor="offline",
            scope_key="repo:test",
            recalled_ids=["useful", "noisy"],
            accepted_ids=["useful"],
            suppressed_ids=["noisy"],
            created_at="2026-05-10T00:00:00Z",
        )
    ]

    first = replay_reinforcement(
        cards=cards,
        recall_events=events,
        as_of="2026-05-17T00:00:00Z",
        scope_key="repo:test",
        weights=ReinforcementWeights(half_life_days=30.0),
    )
    second = replay_reinforcement(
        cards=list(reversed(cards)),
        recall_events=list(reversed(events)),
        as_of="2026-05-17T00:00:00Z",
        scope_key="repo:test",
        weights=ReinforcementWeights(half_life_days=30.0),
    )

    assert first == second
    by_id = {item["record_id"]: item for item in first["states"]}
    assert by_id["useful"]["status"] == "boosted"
    assert by_id["noisy"]["status"] == "suppressed"
    assert by_id["durable"]["status"] == "preserved"
    assert by_id["durable"]["components"]["preservation_floor_applied"] is True
    assert by_id["useful"]["explanation"]
    assert first["counts"]["boosted"] == 1
    assert first["counts"]["suppressed"] == 1
    assert first["counts"]["preserved"] == 1


def test_reinforcement_replay_write_state_does_not_mutate_canonical_cards(tmp_path, capsys) -> None:
    db_path, store, durable, useful, noisy = _seed_store(tmp_path)
    store.log_recall(
        RecallEvent(
            id="event1",
            query="resume project",
            actor="offline",
            scope_key="repo:test",
            recalled_ids=[useful.id, noisy.id],
            accepted_ids=[useful.id],
            suppressed_ids=[noisy.id],
            created_at="2026-05-10T00:00:00Z",
        )
    )
    before = store.get_card(durable.id).to_dict()  # type: ignore[union-attr]

    code = main(
        [
            "recall-reinforcement-replay",
            "--v2-db",
            str(db_path),
            "--out-dir",
            str(tmp_path / "replay"),
            "--scope-key",
            "repo:test",
            "--as-of",
            "2026-05-17T00:00:00Z",
            "--write-state",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    after = store.get_card(durable.id).to_dict()  # type: ignore[union-attr]
    states = store.list_reinforcement_state(scope_key="repo:test")
    assert code == 0
    assert payload["write_state"] is True
    assert payload["state_counts"]["written"] == 3
    assert before == after
    assert {item["record_id"] for item in states} == {durable.id, useful.id, noisy.id}
    assert (tmp_path / "replay" / "recall_reinforcement_replay_report.json").exists()
    assert (tmp_path / "replay" / "recall_reinforcement_replay_report.md").exists()


def test_reinforcement_replay_dry_run_does_not_write_state(tmp_path, capsys) -> None:
    db_path, store, _durable, useful, _noisy = _seed_store(tmp_path)
    store.log_recall(
        RecallEvent(
            id="event1",
            query="resume project",
            actor="offline",
            scope_key="repo:test",
            recalled_ids=[useful.id],
            accepted_ids=[useful.id],
            created_at="2026-05-10T00:00:00Z",
        )
    )

    code = main(
        [
            "recall-reinforcement-replay",
            "--v2-db",
            str(db_path),
            "--out-dir",
            str(tmp_path / "replay"),
            "--scope-key",
            "repo:test",
            "--as-of",
            "2026-05-17T00:00:00Z",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["dry_run"] is True
    assert payload["state_counts"]["written"] == 0
    assert store.list_reinforcement_state(scope_key="repo:test") == []


def test_hybrid_retrieval_can_apply_reinforcement_state_without_default_change() -> None:
    useful = MemoryCard(
        id="useful",
        kind="decision",
        title="Project resume procedure",
        summary="Same lexical query match.",
        scope_key="repo:test",
        updated_at="2026-05-17T00:00:00Z",
    )
    noisy = MemoryCard(
        id="noisy",
        kind="decision",
        title="Project resume procedure",
        summary="Same lexical query match.",
        scope_key="repo:test",
        updated_at="2026-05-17T00:00:00Z",
    )

    baseline = hybrid_recall([noisy, useful], "project resume procedure", scope_key="repo:test")
    adjusted = hybrid_recall(
        [noisy, useful],
        "project resume procedure",
        scope_key="repo:test",
        reinforcement_state={
            "useful": {"record_id": "useful", "status": "boosted", "effective_score": 2.0},
            "noisy": {"record_id": "noisy", "status": "suppressed", "effective_score": -2.0},
        },
    )

    assert [item["record_id"] for item in baseline["results"]] == ["noisy", "useful"]
    assert [item["record_id"] for item in adjusted["results"]] == ["useful"]
    useful_explanation = adjusted["results"][0]["explanation"]
    assert "reinforcement_effective_boost" in useful_explanation["score_components"]


def test_reinforcement_suppression_can_remove_high_lexical_match() -> None:
    adjusted, _components, penalties, state = apply_reinforcement_state_to_score(
        "noisy",
        120.0,
        {"noisy": {"record_id": "noisy", "status": "suppressed", "effective_score": -1.0}},
    )

    assert state is not None
    assert adjusted < 35.0
    assert penalties["reinforcement_suppressed_memory"] <= -140.0


def test_phase_d_cli_does_not_use_v1_connector(tmp_path, monkeypatch, capsys) -> None:
    db_path, _store, _durable, useful, _noisy = _seed_store(tmp_path)

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("v1 connector should not be used by Phase D commands")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)

    code = main(
        [
            "recall-event-record",
            "--v2-db",
            str(db_path),
            "--query",
            "resume",
            "--out-dir",
            str(tmp_path / "event"),
            "--accepted-id",
            useful.id,
            "--write-event",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["mode"] == "offline_recall_event_record"

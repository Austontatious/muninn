from __future__ import annotations

import json

from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main
from muninn.v2.retrieval import ShadowPreviewOptions, build_shadow_rehydrate_preview


def _seed_shadow_db(tmp_path):
    db_path = tmp_path / "shadow_v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    cards = [
        store.create_card(
            MemoryCard(
                id="primary",
                kind="decision",
                title="Friday coder auto route",
                summary="Direct chat routes code prompts to coder with repo file context.",
                body="Primary implementation checkpoint with detailed Friday coder routing behavior.",
                scope_key="repo:test",
                updated_at="2026-05-17T10:00:00Z",
                evidence=[EvidenceRef(evidence_type="file", ref="/repo/backend/core/chat_engine.py:10")],
            )
        ),
        store.create_card(
            MemoryCard(
                id="recent-a",
                kind="runbook",
                title="Friday stack start stop",
                summary="Use docker compose up and down for explicit stack lifecycle.",
                scope_key="repo:test",
                updated_at="2026-05-17T12:00:00Z",
                evidence=[EvidenceRef(evidence_type="file", ref="/repo/RUNBOOK.md:4")],
            )
        ),
        store.create_card(
            MemoryCard(
                id="recent-b",
                kind="interface",
                title="Friday Althing bridge",
                summary="Althing and Direct Friday modes use explicit UI routes.",
                scope_key="repo:test",
                updated_at="2026-05-17T12:00:00Z",
            )
        ),
    ]
    return db_path, cards


def test_shadow_preview_requires_explicit_args(tmp_path) -> None:
    assert main(["shadow-rehydrate-preview", "--query", "resume", "--out-dir", str(tmp_path)]) == 2
    assert main(["shadow-rehydrate-preview", "--v2-db", str(tmp_path / "missing.db"), "--out-dir", str(tmp_path)]) == 2
    assert main(["shadow-rehydrate-preview", "--v2-db", str(tmp_path / "missing.db"), "--query", "resume"]) == 2


def test_shadow_preview_cli_writes_json_and_markdown_with_evidence_and_explanations(tmp_path, capsys) -> None:
    db_path, _cards = _seed_shadow_db(tmp_path)
    out_dir = tmp_path / "preview"

    code = main(
        [
            "shadow-rehydrate-preview",
            "--v2-db",
            str(db_path),
            "--query",
            "Friday coder auto route repo file context",
            "--out-dir",
            str(out_dir),
            "--limit",
            "3",
            "--primary-limit",
            "1",
            "--recent-limit",
            "2",
            "--space-key",
            "repo:test",
            "--include-evidence",
            "--include-explanations",
            "--strict",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    report = json.loads((out_dir / "shadow_rehydrate_preview.json").read_text(encoding="utf-8"))
    markdown = (out_dir / "shadow_rehydrate_preview.md").read_text(encoding="utf-8")
    assert code == 0
    assert payload["mode"] == "shadow_rehydrate_preview"
    assert payload["counts"]["primary"] == 1
    assert payload["counts"]["supplements"] == 2
    assert report["primary_results"][0]["id"] == "primary"
    assert report["primary_results"][0]["evidence"]
    assert "explanation" in report["primary_results"][0]
    assert "Recent In-Scope Supplements" in markdown


def test_shadow_preview_no_recent_supplement_disables_supplements(tmp_path, capsys) -> None:
    db_path, _cards = _seed_shadow_db(tmp_path)

    code = main(
        [
            "shadow-rehydrate-preview",
            "--v2-db",
            str(db_path),
            "--query",
            "Friday coder auto route",
            "--out-dir",
            str(tmp_path / "preview"),
            "--space-key",
            "repo:test",
            "--no-recent-supplement",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["counts"]["primary"] >= 1
    assert payload["counts"]["supplements"] == 0


def test_shadow_preview_prefers_primary_under_max_chars() -> None:
    _db_path = "/tmp/nonexistent-shadow-test.db"
    primary = MemoryCard(
        id="primary",
        kind="decision",
        title="Friday coder auto route",
        summary="Direct coder route.",
        scope_key="repo:test",
        updated_at="2026-05-17T10:00:00Z",
    )
    supplement = MemoryCard(
        id="supplement",
        kind="runbook",
        title="Very long continuity supplement",
        summary="x" * 500,
        scope_key="repo:test",
        updated_at="2026-05-17T12:00:00Z",
    )

    report = build_shadow_rehydrate_preview(
        [supplement, primary],
        provider=None,
        options=ShadowPreviewOptions(
            v2_db=_db_path,
            query="Friday coder auto route",
            space_key="repo:test",
            limit=2,
            primary_limit=1,
            recent_limit=1,
            max_chars=120,
        ),
    )

    assert [item["id"] for item in report["primary_results"]] == ["primary"]
    assert report["recent_supplements"] == []
    assert report["counts"]["omitted_for_budget"] == 1


def test_shadow_preview_recent_order_is_deterministic_for_ties() -> None:
    primary = MemoryCard(
        id="primary",
        kind="decision",
        title="Unique primary match",
        summary="Primary match summary.",
        scope_key="repo:test",
        updated_at="2026-05-17T10:00:00Z",
    )
    cards = [
        MemoryCard(
            id="b-supplement",
            kind="runbook",
            title="Supplement b",
            summary="Recent supplement.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
        ),
        primary,
        MemoryCard(
            id="a-supplement",
            kind="runbook",
            title="Supplement a",
            summary="Recent supplement.",
            scope_key="repo:test",
            updated_at="2026-05-17T12:00:00Z",
        ),
    ]

    first = build_shadow_rehydrate_preview(
        cards,
        options=ShadowPreviewOptions(
            v2_db="/tmp/test.db",
            query="Unique primary match",
            space_key="repo:test",
            limit=3,
            primary_limit=1,
            recent_limit=2,
        ),
    )
    second = build_shadow_rehydrate_preview(
        list(reversed(cards)),
        options=ShadowPreviewOptions(
            v2_db="/tmp/test.db",
            query="Unique primary match",
            space_key="repo:test",
            limit=3,
            primary_limit=1,
            recent_limit=2,
        ),
    )

    assert [item["id"] for item in first["recent_supplements"]] == ["a-supplement", "b-supplement"]
    assert [item["id"] for item in second["recent_supplements"]] == ["a-supplement", "b-supplement"]


def test_shadow_preview_empty_db_fails_clearly(tmp_path, capsys) -> None:
    db_path = tmp_path / "empty.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()

    code = main(
        [
            "shadow-rehydrate-preview",
            "--v2-db",
            str(db_path),
            "--query",
            "resume",
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )

    captured = capsys.readouterr()
    assert code == 2
    assert "shadow_preview_no_active_v2_cards" in captured.err


def test_shadow_preview_does_not_call_v1_read_connector(tmp_path, monkeypatch, capsys) -> None:
    db_path, _cards = _seed_shadow_db(tmp_path)

    def fail_v1(*_args, **_kwargs):
        raise AssertionError("v1 connector should not be used")

    monkeypatch.setattr("muninn.v2.cli._connect_v1_readonly", fail_v1)

    code = main(
        [
            "shadow-rehydrate-preview",
            "--v2-db",
            str(db_path),
            "--query",
            "Friday coder auto route",
            "--out-dir",
            str(tmp_path / "out"),
            "--space-key",
            "repo:test",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["usable"] is True

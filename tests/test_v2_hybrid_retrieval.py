from __future__ import annotations

import json

from muninn.v2 import EvidenceRef, MemoryCard, SQLiteMemoryStore
from muninn.v2.cli import main
from muninn.v2.eval import load_retrieval_fixture, run_retrieval_eval
from muninn.v2.retrieval import hybrid_recall, normalize_tokens


def test_query_normalization_preserves_campaign_and_numeric_tokens() -> None:
    tokens = normalize_tokens("Campaign 004A duplicate torpedo_wasted_shot_rate count 2")

    assert "004a" in tokens
    assert "2" in tokens
    assert {"torpedo", "wasted", "shot", "rate"}.issubset(tokens)


def test_hybrid_title_phrase_beats_weak_body_match() -> None:
    precise = MemoryCard(
        id="precise",
        kind="decision",
        title="Campaign 004A duplicate torpedo suppression",
        summary="Bounded campaign result.",
        scope_key="repo:test",
    )
    weak = MemoryCard(
        id="weak",
        kind="decision",
        title="General torpedo archive",
        summary="Weak broad body match.",
        body="Campaign notes mention duplicate telemetry and suppression in a broad appendix.",
        scope_key="repo:test",
    )

    payload = hybrid_recall([weak, precise], "Campaign 004A duplicate torpedo suppression", scope_key="repo:test")

    assert payload["results"][0]["record_id"] == "precise"
    explanation = payload["results"][0]["explanation"]
    assert "title_phrase_match" in explanation["score_components"]
    assert "004a" in explanation["matched_tokens"]


def test_hybrid_evidence_contributes_without_flooding() -> None:
    evidence_only = MemoryCard(
        id="evidence-only",
        kind="decision",
        title="Unrelated report",
        summary="No direct title match.",
        evidence=[EvidenceRef(evidence_type="file", ref="/tmp/sonar_clutter_wrong_binding_rate.json")],
        scope_key="repo:test",
    )
    body_match = MemoryCard(
        id="body-match",
        kind="decision",
        title="Sonar clutter campaign",
        summary="Metric body match.",
        body="The sonar_clutter_wrong_binding_rate metric stayed at zero.",
        scope_key="repo:test",
    )

    payload = hybrid_recall(
        [evidence_only, body_match],
        "sonar clutter wrong binding rate",
        scope_key="repo:test",
        min_score=0,
    )

    assert payload["results"][0]["record_id"] == "body-match"
    evidence_result = next(item for item in payload["results"] if item["record_id"] == "evidence-only")
    assert "evidence_only_weak_match" in evidence_result["explanation"]["penalties"]


def test_hybrid_penalizes_broad_low_specificity_matches() -> None:
    broad = MemoryCard(
        id="broad",
        kind="decision",
        title="Campaign archive",
        summary="Broad low specificity match.",
        body="Campaign campaign campaign archive notes.",
        scope_key="repo:test",
    )
    precise = MemoryCard(
        id="precise",
        kind="decision",
        title="Campaign 007A post reacquisition stabilization",
        summary="Precise title match.",
        scope_key="repo:test",
    )

    payload = hybrid_recall([broad, precise], "Campaign 007A post reacquisition stabilization", scope_key="repo:test")

    assert payload["results"][0]["record_id"] == "precise"
    assert all(item["record_id"] != "broad" for item in payload["results"])


def test_hybrid_works_without_vector_backend_and_returns_explanations() -> None:
    card = MemoryCard(
        id="card",
        kind="decision",
        title="Derived vector fallback absent",
        summary="Hybrid retrieval still works without vector indexes.",
        scope_key="repo:test",
    )

    payload = hybrid_recall([card], "derived vector fallback absent", provider=None, scope_key="repo:test")

    assert payload["backend"] == "hybrid"
    assert payload["results"][0]["record_id"] == "card"
    assert payload["results"][0]["explanation"]["vector_used"] is False
    assert payload["results"][0]["explanation"]["score_components"]


def test_hybrid_ranking_is_deterministic() -> None:
    cards = [
        MemoryCard(
                id="b",
                kind="decision",
                title="Campaign 005A fire control state",
                summary="Same deterministic content.",
                scope_key="repo:test",
            updated_at="2026-05-17T00:00:00Z",
        ),
        MemoryCard(
                id="a",
                kind="decision",
                title="Campaign 005A fire control state",
                summary="Same deterministic content.",
                scope_key="repo:test",
            updated_at="2026-05-17T00:00:00Z",
        ),
    ]

    first = hybrid_recall(cards, "Campaign 005A fire control state", scope_key="repo:test")
    second = hybrid_recall(list(reversed(cards)), "Campaign 005A fire control state", scope_key="repo:test")

    assert [item["record_id"] for item in first["results"]] == ["a", "b"]
    assert [item["record_id"] for item in second["results"]] == ["a", "b"]


def test_retrieval_eval_supports_hybrid_mode_and_score_components(tmp_path) -> None:
    db_path = tmp_path / "v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    card = store.create_card(
        MemoryCard(
                id="campaign-007a",
                kind="decision",
                title="Campaign 007A post reacquisition stabilization",
                summary="Campaign post reacquisition stabilization.",
                body="The sonar_clutter_wrong_binding_rate metric stayed stable.",
                scope_key="repo:test",
        )
    )
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "hybrid",
                "cases": [
                    {
                        "id": "case",
                        "query": "Campaign 007A post reacquisition stabilization",
                        "space_key": "repo:test",
                        "expected_card_ids": [card.id],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = run_retrieval_eval(
        records=[card],
        fixture=load_retrieval_fixture(fixture_path),
        retrieval_mode="hybrid",
    )

    assert report["retrieval_mode"] == "hybrid"
    assert report["summary"]["hit_records"] == 1
    explanation = report["cases"][0]["top_results"][0]["explanation"]
    assert "score_components" in explanation
    assert "title_phrase_match" in explanation["score_components"]


def test_retrieval_eval_cli_accepts_hybrid_mode_without_v1_db(tmp_path, capsys) -> None:
    db_path = tmp_path / "v2.db"
    store = SQLiteMemoryStore(db_path)
    store.initialize()
    store.create_card(
        MemoryCard(
            id="card",
            kind="decision",
            title="Hybrid retrieval CLI",
            summary="No v1 database is required for retrieval eval.",
            scope_key="repo:test",
        )
    )
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "version": 1,
                "cases": [
                    {
                        "id": "cli",
                        "query": "Hybrid retrieval CLI",
                        "space_key": "repo:test",
                        "expected_card_ids": ["card"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "retrieval-eval",
            "--v2-db",
            str(db_path),
            "--fixture",
            str(fixture),
            "--out-dir",
            str(tmp_path / "out"),
            "--retrieval-mode",
            "hybrid",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["retrieval_mode"] == "hybrid"
    assert payload["summary"]["hit_records"] == 1

from __future__ import annotations

import json

import pytest

from muninn.human_memory.adaptation import adaptation_card_upsert, query_adaptation_cards
from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.cards import card_upsert, cards_search
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space


def _init_conn(tmp_path):
    db_path = tmp_path / "human_memory_adaptation.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)
    resolved = ResolvedSpace(
        key="repo:lailaadapt123456",
        label="laila",
        meta_json=json.dumps({"root_path": "/tmp/laila"}, separators=(",", ":")),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)
    return conn, resolved.key


def test_adaptation_card_upsert_and_durable_preference_query(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)

    card_id = adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="preference.direct",
        subject_id="client_acme",
        category="voice",
        scope={"type": "campaign", "id": "spring_2026"},
        persistence="durable",
        source_type="direct_feedback",
        confidence=0.91,
        tags=["Humor", "Polish"],
        workflow_tags=["business_goal"],
        title="Client asked for less polished voice",
        summary="Use less polished and more conversational voice for this client.",
        body="Direct feedback: 'less polished'. Keep copy more natural and less formal.",
        session_id="sess-a",
    )
    assert card_id

    out = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id="client_acme",
        view="durable_preferences",
        categories=["voice"],
        limit=5,
    )
    assert out["counts"]["total"] == 1
    card = out["cards"][0]
    assert card["adaptation"]["memory_type"] == "preference.direct"
    assert card["adaptation"]["persistence"] == "durable"
    assert card["adaptation"]["scope"]["type"] == "campaign"
    assert card["adaptation"]["scope"]["id"] == "spring_2026"
    assert "adaptation" in card["tags"]
    assert "preference.direct" in card["tags"]
    assert "durable_candidate" in card["tags"]
    assert "voice" in card["tags"]
    conn.close()


def test_adaptation_query_separates_durable_vs_one_off_and_scope(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)
    subject_id = "client_scope_test"

    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="preference.inferred",
        subject_id=subject_id,
        category="tone",
        scope={"type": "global"},
        persistence="durable",
        source_type="inference",
        title="Client consistently approves humor-heavy posts",
        summary="Inferred durable preference for humor-forward tone.",
        body="Repeated approvals for humor-heavy social captions over 4 cycles.",
    )
    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="override.scoped",
        subject_id=subject_id,
        category="cta_tolerance",
        scope={"type": "thread", "id": "thread-9"},
        persistence="one_off",
        source_type="operator_edit",
        title="Thread override: reduce CTA force",
        summary="For this thread only, avoid aggressive CTA framing.",
        body="Operator lowered CTA intensity for this thread.",
    )
    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="override.scoped",
        subject_id=subject_id,
        category="topic",
        scope={"type": "session", "id": "session-42"},
        persistence="session_only",
        source_type="direct_feedback",
        session_id="session-42",
        title="Session override: avoid knives topic",
        summary="Session-only request to avoid knives topic unless user introduces it.",
        body="Direct session feedback to avoid knives topic by default.",
    )

    durable = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="durable_preferences",
        limit=10,
    )
    assert durable["counts"]["total"] == 1
    assert durable["cards"][0]["adaptation"]["memory_type"] == "preference.inferred"

    overrides = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="recent_overrides",
        limit=10,
    )
    assert overrides["counts"]["total"] == 2
    assert {card["adaptation"]["persistence"] for card in overrides["cards"]} == {
        "one_off",
        "session_only",
    }

    thread_only = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="recent_overrides",
        scope_types=["thread"],
        limit=10,
    )
    assert thread_only["counts"]["total"] == 1
    assert thread_only["cards"][0]["adaptation"]["scope"]["type"] == "thread"

    conn.close()


def test_adaptation_prompt_state_groups_corrections_and_outcomes(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)
    subject_id = "client_prompt_state"

    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="correction",
        subject_id=subject_id,
        category="cta_tolerance",
        scope={"type": "social"},
        persistence="durable",
        source_type="operator_edit",
        tags=["social"],
        title="Operator revised CTA down",
        summary="CTA language should remain soft for social posts.",
        body="Operator repeatedly reduced hard-sell CTA phrasing.",
    )
    adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="outcome",
        subject_id=subject_id,
        category="cta_tolerance",
        scope={"type": "social"},
        persistence="durable",
        source_type="analytics",
        tags=["social"],
        title="Soft CTA posts perform better",
        summary="Soft CTA language correlated with higher engagement.",
        body="Engagement rate improved on social posts with softer CTA framing.",
    )

    prompt_state = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="prompt_state",
        limit=20,
    )
    categories = {group["category"]: group for group in prompt_state["prompt_state"]}
    assert "cta_tolerance" in categories
    assert len(categories["cta_tolerance"]["corrections"]) == 1
    assert len(categories["cta_tolerance"]["outcomes"]) == 1

    outcomes_social = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="outcomes",
        tags=["social"],
        limit=10,
    )
    assert outcomes_social["counts"]["total"] == 1
    assert outcomes_social["cards"][0]["adaptation"]["memory_type"] == "outcome"
    conn.close()


def test_adaptation_query_recency_and_session_scoping(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)
    subject_id = "client_session_scope"

    old_card_id = adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="correction",
        subject_id=subject_id,
        category="tone",
        scope={"type": "session", "id": "session-old"},
        persistence="session_only",
        source_type="operator_edit",
        session_id="session-old",
        title="Old session correction",
        summary="Old session correction summary.",
        body="Old session correction details.",
    )
    recent_card_id = adaptation_card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        memory_type="correction",
        subject_id=subject_id,
        category="tone",
        scope={"type": "session", "id": "session-new"},
        persistence="session_only",
        source_type="operator_edit",
        session_id="session-new",
        title="Current session correction",
        summary="Current session correction summary.",
        body="Current session correction details.",
    )

    conn.execute(
        "UPDATE cards SET created_at = datetime('now', '-20 days') WHERE id = ?",
        (old_card_id,),
    )
    conn.commit()

    current_session = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="corrections",
        session_id="session-new",
        limit=10,
    )
    assert current_session["counts"]["total"] == 1
    assert current_session["cards"][0]["id"] == recent_card_id

    recent_only = query_adaptation_cards(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        subject_id=subject_id,
        view="corrections",
        max_age_days=7,
        limit=10,
    )
    assert recent_only["counts"]["total"] == 1
    assert recent_only["cards"][0]["id"] == recent_card_id
    conn.close()


def test_query_validation_and_fts_query_normalization(tmp_path) -> None:
    conn, space_key = _init_conn(tmp_path)
    card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        kind="decision",
        title="Use global space as real row",
        summary="Global space is explicit and never NULL.",
        body="All cards and evidence require space_id; global is a real space row.",
    )

    hits = cards_search(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=space_key,
        query="global.space??? row",
        limit=10,
    )
    assert len(hits) == 1

    with pytest.raises(ValueError):
        cards_search(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            query="...!!!",
            limit=10,
        )
    with pytest.raises(ValueError):
        query_adaptation_cards(
            conn,
            user_id=DEFAULT_USER_ID,
            space_key=space_key,
            subject_id="client_validation",
            view="not-a-view",
        )
    conn.close()

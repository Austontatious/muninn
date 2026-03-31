from __future__ import annotations

import json

import pytest

pytest.importorskip("mcp")

from muninn.human_memory.bootstrap import DEFAULT_USER_ID, apply_init_schema, bootstrap_defaults, open_db
from muninn.human_memory.cards import card_upsert
from muninn.human_memory.spaces import ResolvedSpace, get_or_create_space
from muninn.mcp_server import (
    ATLAS_KIND_PREFIX,
    AtlasQueryInput,
    CardInput,
    LensInput,
    _atlas_card_matches,
    _normalize_atlas_result_row,
)


def test_card_input_allows_atlas_kind_with_structured_refs() -> None:
    card = CardInput.model_validate(
        {
            "kind": "atlas.project",
            "title": "Friday",
            "summary": "Friday ownership",
            "body": "Owns orchestration",
            "atlas": {
                "entity_type": "project",
                "entity_id": "friday",
                "project": "friday",
            },
        }
    )

    assert card.atlas is not None
    assert card.atlas.entity_type == "project"


def test_card_input_rejects_mismatched_atlas_kind() -> None:
    with pytest.raises(ValueError):
        CardInput.model_validate(
            {
                "kind": "atlas.project",
                "title": "Bad",
                "summary": "bad",
                "body": "bad",
                "atlas": {
                    "entity_type": "capability",
                    "entity_id": "durable-memory",
                },
            }
        )


def test_atlas_query_input_normalizes_entity_types() -> None:
    query = AtlasQueryInput.model_validate({"entity_types": "project, capability", "limit": 3})
    assert query.entity_types == ["project", "capability"]
    assert query.limit == 3


def test_normalize_and_filter_atlas_row(tmp_path) -> None:
    db_path = tmp_path / "atlas_query.db"
    conn = open_db(str(db_path))
    apply_init_schema(conn)
    bootstrap_defaults(conn)

    resolved = ResolvedSpace(
        key="repo:atlasrepo0001",
        label="atlas-repo",
        meta_json=json.dumps({"root_path": "/tmp/atlas-repo"}, separators=(",", ":")),
        alias_keys=("path:atlasrepo0001",),
    )
    get_or_create_space(conn, user_id=DEFAULT_USER_ID, resolved=resolved)

    card_id = card_upsert(
        conn,
        user_id=DEFAULT_USER_ID,
        space_key=resolved.key,
        kind=f"{ATLAS_KIND_PREFIX}relationship",
        title="Friday depends on Muninn",
        summary="Dependency edge",
        body="Friday depends on Muninn for durable memory context.",
        context_json={
            "atlas": {
                "entity_type": "relationship",
                "entity_id": "rel-friday-muninn",
                "source": "friday",
                "target": "muninn",
            }
        },
        tags=["atlas"],
    )

    row = conn.execute(
        """
        SELECT c.id, s.key AS space_key, c.kind, c.title, c.summary, c.updated_at, c.context_json
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.id = ?
        """,
        (card_id,),
    ).fetchone()

    normalized = _normalize_atlas_result_row(dict(row), include_body=False)
    assert normalized["atlas"]["source"] == "friday"
    assert _atlas_card_matches(normalized, AtlasQueryInput.model_validate({"source": "friday"}))
    assert not _atlas_card_matches(normalized, AtlasQueryInput.model_validate({"source": "lex"}))
    assert normalized["score"] is None
    conn.close()


def test_lens_accepts_atlas_kind_filter() -> None:
    lens = LensInput.model_validate("space:global kinds:atlas.project,atlas.capability limit:5")
    assert lens.kinds == ["atlas.project", "atlas.capability"]

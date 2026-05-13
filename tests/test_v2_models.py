from __future__ import annotations

import json

from muninn.v2 import (
    EvidenceRef,
    MemoryAssociation,
    MemoryCard,
    MemoryEntity,
    MemoryEvent,
    OntologyProfile,
    RecallEvent,
)


def test_v2_primitives_round_trip_as_json() -> None:
    evidence = EvidenceRef(
        id="ev1",
        evidence_type="file",
        ref="/tmp/example.py:1",
        metadata={"source": "unit-test"},
        created_at="2026-05-13T00:00:00Z",
    )
    card = MemoryCard(
        id="card1",
        kind="decision",
        title="Keep v1 stable",
        summary="v2 is adjacent",
        evidence=[evidence],
        entity_ids=["entity1"],
        tags=["v2"],
        metadata={"source_system": "test"},
        created_at="2026-05-13T00:00:00Z",
        updated_at="2026-05-13T00:00:00Z",
    )
    entity = MemoryEntity(
        id="entity1",
        entity_type="repository",
        name="Muninn",
        aliases=["muninn"],
        created_at="2026-05-13T00:00:00Z",
        updated_at="2026-05-13T00:00:00Z",
    )
    association = MemoryAssociation(
        id="assoc1",
        source_id="card1",
        target_id="entity1",
        association_type="about",
        created_at="2026-05-13T00:00:00Z",
        updated_at="2026-05-13T00:00:00Z",
    )
    event = MemoryEvent(
        id="event1",
        event_type="write",
        actor="codex",
        summary="Wrote adjacent v2 card",
        evidence=[evidence],
        created_at="2026-05-13T00:00:00Z",
    )
    recall = RecallEvent(
        id="recall1",
        query="adjacent v2",
        actor="codex",
        recalled_ids=["card1"],
        created_at="2026-05-13T00:00:00Z",
    )
    ontology = OntologyProfile(
        id="ontology1",
        name="foundation",
        version="0.1",
        entity_types=["repository"],
        card_kinds=["decision"],
        association_types=["about"],
        created_at="2026-05-13T00:00:00Z",
        updated_at="2026-05-13T00:00:00Z",
    )

    for model in [evidence, card, entity, association, event, recall, ontology]:
        payload = json.loads(json.dumps(model.to_dict()))
        restored = type(model).from_dict(payload)
        assert restored.to_dict() == model.to_dict()


def test_v2_card_accepts_legacy_evidence_type_key() -> None:
    card = MemoryCard.from_dict(
        {
            "kind": "decision",
            "title": "Mapped card",
            "summary": "Evidence shape accepts v1 keys",
            "evidence": [{"id": "ev1", "type": "file", "ref": "/tmp/a.py"}],
        }
    )

    assert card.evidence[0].evidence_type == "file"
    assert card.evidence[0].ref == "/tmp/a.py"

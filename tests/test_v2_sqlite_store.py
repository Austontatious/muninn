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
    SQLiteMemoryStore,
)


def test_v2_sqlite_store_round_trips_records_and_exports(tmp_path) -> None:
    store = SQLiteMemoryStore(tmp_path / "muninn_v2.db")
    store.initialize()

    evidence = EvidenceRef(id="ev1", evidence_type="file", ref="/tmp/example.py:1")
    entity = store.create_entity(MemoryEntity(id="ent1", entity_type="repository", name="Muninn"))
    card = store.create_card(
        MemoryCard(
            id="card1",
            kind="decision",
            title="Adjacent v2",
            summary="v2 store is separate",
            scope_key="repo:test",
            entity_ids=[entity.id],
            evidence=[evidence],
        )
    )
    association = store.create_association(
        MemoryAssociation(
            id="assoc1",
            source_id=card.id,
            source_type="memory_card",
            target_id=entity.id,
            target_type="memory_entity",
            association_type="about",
        )
    )
    event = store.create_event(
        MemoryEvent(id="event1", event_type="write", actor="codex", summary="created card")
    )
    recall = store.log_recall(
        RecallEvent(id="recall1", query="adjacent", actor="codex", recalled_ids=[card.id])
    )
    ontology = store.create_ontology_profile(
        OntologyProfile(
            id="ontology1",
            name="foundation",
            version="0.1",
            card_kinds=["decision"],
            entity_types=["repository"],
            association_types=["about"],
        )
    )

    assert store.get_card(card.id).summary == "v2 store is separate"  # type: ignore[union-attr]
    assert store.get_entity(entity.id).name == "Muninn"  # type: ignore[union-attr]
    assert store.get_association(association.id).target_id == entity.id  # type: ignore[union-attr]
    assert store.get_event(event.id).actor == "codex"  # type: ignore[union-attr]
    assert store.get_recall(recall.id).recalled_ids == [card.id]  # type: ignore[union-attr]
    assert store.get_ontology_profile(ontology.id).name == "foundation"  # type: ignore[union-attr]

    bundle = store.export_bundle()
    assert bundle["counts"] == {
        "ontology_profiles": 1,
        "entities": 1,
        "cards": 1,
        "associations": 1,
        "events": 1,
        "recall_events": 1,
    }
    jsonl = store.export_jsonl()
    assert '"record_type":"export_header"' in jsonl
    assert '"record_type":"memory_card"' in jsonl

    imported = SQLiteMemoryStore(tmp_path / "imported_v2.db")
    counts = imported.import_bundle(json.loads(json.dumps(bundle)))
    assert counts["cards"] == 1
    assert imported.get_card("card1").title == "Adjacent v2"  # type: ignore[union-attr]

from muninn import db
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance, UpsertEmbeddingsItem
from muninn.vector import store as vector_store


def test_vector_query_top_hit_matches_expected_item(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    fact_candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "alpha"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="turn_1"),
    )
    pref_candidate = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "quiet"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="turn_2"),
    )

    fact_id, _ = write_candidates("default", [fact_candidate])
    pref_id, _ = write_candidates("default", [pref_candidate])

    upserted, rejected, reasons = vector_store.upsert_embeddings(
        namespace="default",
        items=[
            UpsertEmbeddingsItem(
                item_id=fact_id[0],
                kind="fact",
                entity_id="ent_user",
                model="test-model-v1",
                vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ),
            UpsertEmbeddingsItem(
                item_id=pref_id[0],
                kind="preference",
                entity_id="ent_user",
                model="test-model-v1",
                vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ),
        ],
    )
    assert upserted == 2
    assert rejected == 0
    assert reasons == []

    hits = vector_store.query_vector(
        namespace="default",
        model="test-model-v1",
        query_vec=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        entity_id="ent_user",
        kinds=None,
        k=2,
        max_scan=5000,
    )
    assert len(hits) == 2
    assert hits[0].item_id == fact_id[0]
    assert hits[0].kind == "fact"

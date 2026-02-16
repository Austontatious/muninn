from muninn import db
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance, UpsertEmbeddingsItem
from muninn.vector import store as vector_store


def test_vector_query_is_namespace_scoped(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    fact_a = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "alpha"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="a1"),
    )
    fact_b = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "topic", "object": "beta"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="b1"),
    )

    id_a, _ = write_candidates("lexi", [fact_a])
    id_b, _ = write_candidates("friday", [fact_b])

    vector_store.upsert_embeddings(
        namespace="lexi",
        items=[
            UpsertEmbeddingsItem(
                item_id=id_a[0],
                kind="fact",
                entity_id="ent_user",
                model="ns-model",
                vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            )
        ],
    )
    vector_store.upsert_embeddings(
        namespace="friday",
        items=[
            UpsertEmbeddingsItem(
                item_id=id_b[0],
                kind="fact",
                entity_id="ent_user",
                model="ns-model",
                vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            )
        ],
    )

    hits_lexi = vector_store.query_vector(
        namespace="lexi",
        model="ns-model",
        query_vec=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        entity_id="ent_user",
        kinds=None,
        k=5,
        max_scan=5000,
    )
    assert hits_lexi
    assert all(hit.item_id == id_a[0] for hit in hits_lexi)

    hits_friday = vector_store.query_vector(
        namespace="friday",
        model="ns-model",
        query_vec=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        entity_id="ent_user",
        kinds=None,
        k=5,
        max_scan=5000,
    )
    assert hits_friday
    assert all(hit.item_id == id_b[0] for hit in hits_friday)

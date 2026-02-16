from muninn import db
from muninn.memory.retrieval import retrieve
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_fts_retrieval_fact_hit(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "style.response", "object": "direct"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="turn_1"),
    )
    ids, reasons = write_candidates("default", [candidate])
    assert len(ids) == 1
    assert any(reason.startswith("Accepted") for reason in reasons)

    items = retrieve(namespace="default", query="direct", entity_id="ent_user", k=8)
    assert any(item.kind == "fact" and "direct" in item.text for item in items)

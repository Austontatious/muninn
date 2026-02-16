from muninn import db
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_write_and_retrieve_fact(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "prefers", "object": "direct answers"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="test"),
    )
    ids, _ = write_candidates("default", [candidate])
    assert len(ids) == 1

from muninn import db
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance
from muninn.service import memory_version


def test_memory_version_changes_after_write(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    v1 = memory_version("default", "generic")
    v1_repeat = memory_version("default", "generic")
    assert v1 == v1_repeat

    candidate = MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"predicate": "style.response", "object": "direct"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id="turn_1"),
    )
    write_candidates("default", [candidate])

    v2 = memory_version("default", "generic")
    assert v2 != v1

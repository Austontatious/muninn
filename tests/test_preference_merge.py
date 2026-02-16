from muninn import db
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_preference_merge_keeps_single_key(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    cand1 = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "direct"},
        confidence=0.7,
        provenance=Provenance(source_type="user", source_id="turn_1"),
    )
    cand2 = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "quiet"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="turn_2"),
    )

    write_candidates("default", [cand1])
    write_candidates("default", [cand2])

    rows = db.fetch_all(
        conn,
        "SELECT value, confidence FROM preferences WHERE entity_id = ? AND key = ?",
        ("ent_user", "style.response"),
    )
    assert len(rows) == 1
    assert rows[0]["value"] == "quiet"
    assert float(rows[0]["confidence"]) == 0.9

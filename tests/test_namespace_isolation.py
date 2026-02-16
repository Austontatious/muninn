from muninn import db
from muninn.memory.retrieval import retrieve
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def test_namespace_preference_isolation_and_merge_boundaries(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    lexi_pref = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "direct"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id="lexi_1"),
    )
    friday_pref = MemoryCandidate(
        kind="preference",
        entity={"id": "ent_user", "kind": "user", "name": "Auston"},
        payload={"key": "style.response", "value": "quiet"},
        confidence=0.9,
        provenance=Provenance(source_type="user", source_id="friday_1"),
    )

    write_candidates("lexi", [lexi_pref])
    write_candidates("friday", [friday_pref])

    rows = db.fetch_all(
        conn,
        """
        SELECT namespace, value
        FROM preferences
        WHERE entity_id = ? AND key = ?
        ORDER BY namespace ASC
        """,
        ("ent_user", "style.response"),
    )
    assert len(rows) == 2
    assert rows[0]["namespace"] == "friday"
    assert rows[0]["value"] == "quiet"
    assert rows[1]["namespace"] == "lexi"
    assert rows[1]["value"] == "direct"

    lexi_items = retrieve(namespace="lexi", query="direct", entity_id="ent_user", k=8)
    friday_items = retrieve(namespace="friday", query="quiet", entity_id="ent_user", k=8)

    assert any(item.kind == "preference" and "style.response=direct" == item.text for item in lexi_items)
    assert all("quiet" not in item.text for item in lexi_items)

    assert any(
        item.kind == "preference" and "style.response=quiet" == item.text for item in friday_items
    )
    assert all("direct" not in item.text for item in friday_items)

from __future__ import annotations

import sqlite3
import threading
import time

from fastapi.testclient import TestClient

from muninn import db
from muninn.api import app
from muninn.memory.retrieval import retrieve
from muninn.memory.writeback import write_candidates
from muninn.models import MemoryCandidate, Provenance


def _fact_candidate(i: int) -> MemoryCandidate:
    return MemoryCandidate(
        kind="fact",
        entity={"id": "ent_user", "kind": "user", "name": "Batch User"},
        payload={"predicate": "topic", "object": f"value_{i}"},
        confidence=0.8,
        provenance=Provenance(source_type="user", source_id=f"turn_{i}"),
    )


def test_writeback_batch_commits_once(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)

    trace: list[str] = []
    conn.set_trace_callback(lambda sql: trace.append(str(sql).strip().upper()))
    candidates = [_fact_candidate(i) for i in range(32)]
    ids, _ = write_candidates("default", candidates, conn=conn)
    conn.close()

    assert len(ids) == 32
    commits = [sql for sql in trace if sql.startswith("COMMIT")]
    assert len(commits) == 1


def test_audit_flush_is_batched_and_records_events(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))
    monkeypatch.setenv("MUNINN_REQUIRE_API_KEY", "0")
    monkeypatch.setenv("MUNINN_ALLOW_UNAUTH_NAMESPACE_OVERRIDE", "1")

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    execute_one_calls = 0
    execute_many_calls = 0

    original_execute_one = db.execute_one
    original_execute_many = db.execute_many

    def _counting_execute_one(conn, sql, params, *, commit=True):
        nonlocal execute_one_calls
        if "INSERT INTO audit_log" in sql:
            execute_one_calls += 1
        return original_execute_one(conn, sql, params, commit=commit)

    def _counting_execute_many(conn, sql, rows, *, commit=True):
        nonlocal execute_many_calls
        if "INSERT INTO audit_log" in sql:
            execute_many_calls += 1
        return original_execute_many(conn, sql, rows, commit=commit)

    monkeypatch.setattr(db, "execute_one", _counting_execute_one)
    monkeypatch.setattr(db, "execute_many", _counting_execute_many)

    client = TestClient(app)
    response = client.post(
        "/retrieve",
        json={
            "namespace": "default",
            "query": "batched audit request",
            "scope": ["cards"],
            "k_cards": 5,
        },
    )
    assert response.status_code == 200
    assert execute_one_calls == 0
    assert execute_many_calls == 1

    check_conn = db.connect()
    row = db.fetch_one(
        check_conn,
        """
        SELECT count(*) AS n
        FROM audit_log
        WHERE namespace = ?
          AND event_type IN ('cardex_retrieve', 'http_request')
        """,
        ("default",),
    )
    check_conn.close()
    assert row is not None
    assert int(row["n"]) >= 2


def test_concurrent_read_write_smoke_has_no_lock_errors(tmp_path, monkeypatch) -> None:
    test_db = tmp_path / "muninn.db"
    monkeypatch.setenv("MUNINN_DB_PATH", str(test_db))

    conn = db.connect()
    db.init_db(conn)
    conn.close()

    errors: list[Exception] = []
    writer_done = threading.Event()
    read_count = 0

    def _writer() -> None:
        try:
            writer_conn = db.connect()
            with db.transaction(writer_conn):
                db.execute_one(
                    writer_conn,
                    "INSERT OR IGNORE INTO entities (id, namespace, kind, name, created_at) VALUES (?,?,?,?,?)",
                    ("ent_user", "default", "user", "Concurrent User", db.now()),
                    commit=False,
                )
                for idx in range(180):
                    db.execute_one(
                        writer_conn,
                        """
                        INSERT INTO facts (id, namespace, subject_id, predicate, object, confidence, provenance_json, created_at)
                        VALUES (?,?,?,?,?,?,?,?)
                        """,
                        (
                            f"fact_{idx}",
                            "default",
                            "ent_user",
                            "topic",
                            f"value_{idx}",
                            0.8,
                            '{"source_type":"user","source_id":"concurrency"}',
                            db.now(),
                        ),
                        commit=False,
                    )
                    if idx % 30 == 0:
                        time.sleep(0.002)
            writer_conn.close()
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)
        finally:
            writer_done.set()

    def _reader() -> None:
        nonlocal read_count
        while not writer_done.is_set():
            try:
                retrieve(namespace="default", query="topic", entity_id="ent_user", k=8)
                read_count += 1
            except Exception as exc:  # pragma: no cover - defensive
                errors.append(exc)
            time.sleep(0.001)

    writer = threading.Thread(target=_writer)
    reader = threading.Thread(target=_reader)
    writer.start()
    reader.start()
    writer.join(timeout=10)
    reader.join(timeout=10)

    assert writer_done.is_set()
    assert read_count > 0
    lock_errors = [
        exc
        for exc in errors
        if isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower()
    ]
    assert not lock_errors

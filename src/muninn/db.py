import os
import sqlite3
import time
import uuid
from collections.abc import Iterable
from contextlib import contextmanager
from pathlib import Path

from .config import settings
from .vector.sqlite_vec_loader import maybe_load_sqlite_vec


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _db_path() -> str:
    return os.getenv("MUNINN_DB_PATH", settings.db_path)


def connect() -> sqlite3.Connection:
    db_path = _db_path()
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA temp_store=MEMORY")
    maybe_load_sqlite_vec(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@contextmanager
def transaction(conn: sqlite3.Connection | None = None):
    created_here = False
    if conn is None:
        conn = connect()
        created_here = True

    started_here = not conn.in_transaction
    if started_here:
        conn.execute("BEGIN")

    try:
        yield conn
    except Exception:
        if started_here and conn.in_transaction:
            conn.rollback()
        raise
    else:
        if started_here and conn.in_transaction:
            conn.commit()
    finally:
        if created_here:
            conn.close()


def execute_many(
    conn: sqlite3.Connection,
    sql: str,
    rows: Iterable[tuple],
    *,
    commit: bool = True,
) -> None:
    buffered = list(rows)
    if not buffered:
        return
    was_in_transaction = conn.in_transaction
    conn.executemany(sql, buffered)
    if commit and not was_in_transaction:
        conn.commit()


def execute_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple,
    *,
    commit: bool = True,
) -> None:
    was_in_transaction = conn.in_transaction
    conn.execute(sql, params)
    if commit and not was_in_transaction:
        conn.commit()


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    cur = conn.execute(sql, params)
    return list(cur.fetchall())


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Row | None:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return row

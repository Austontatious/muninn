import os
import sqlite3
import time
import uuid
from collections.abc import Iterable
from pathlib import Path

from .config import settings


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
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def now() -> float:
    return time.time()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def execute_many(conn: sqlite3.Connection, sql: str, rows: Iterable[tuple]) -> None:
    conn.executemany(sql, list(rows))
    conn.commit()


def execute_one(conn: sqlite3.Connection, sql: str, params: tuple) -> None:
    conn.execute(sql, params)
    conn.commit()


def fetch_all(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    cur = conn.execute(sql, params)
    return list(cur.fetchall())


def fetch_one(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> sqlite3.Row | None:
    cur = conn.execute(sql, params)
    row = cur.fetchone()
    return row

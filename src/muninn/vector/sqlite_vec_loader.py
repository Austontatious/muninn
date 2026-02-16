from __future__ import annotations

import sqlite3

from ..config import sqlite_vec_enabled, sqlite_vec_path
from .vectors import to_f32_blob

try:
    import sqlite_vec as _sqlite_vec_module
except Exception:  # pragma: no cover - optional dependency
    _sqlite_vec_module = None


_CONN_SQLITE_VEC_STATE: dict[int, bool] = {}


def _set_cached_state(conn: sqlite3.Connection, loaded: bool) -> None:
    _CONN_SQLITE_VEC_STATE[id(conn)] = bool(loaded)


def get_cached_state(conn: sqlite3.Connection) -> bool | None:
    return _CONN_SQLITE_VEC_STATE.get(id(conn))


def is_sqlite_vec_loaded(conn: sqlite3.Connection) -> bool:
    try:
        row = conn.execute("SELECT vec_version() AS version").fetchone()
    except Exception:
        return False
    return bool(row and row[0])


def maybe_load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    cached = get_cached_state(conn)
    if cached is not None:
        return cached

    if not sqlite_vec_enabled():
        _set_cached_state(conn, False)
        return False

    if is_sqlite_vec_loaded(conn):
        _set_cached_state(conn, True)
        return True

    loaded = False
    ext_enabled = False
    try:
        conn.enable_load_extension(True)
        ext_enabled = True

        # Preferred path: python sqlite_vec package helper.
        if _sqlite_vec_module is not None:
            try:
                _sqlite_vec_module.load(conn)
                loaded = is_sqlite_vec_loaded(conn)
            except Exception:
                loaded = False

        # Fallback: explicit extension path, if provided.
        if not loaded:
            ext_path = sqlite_vec_path()
            if ext_path:
                try:
                    conn.load_extension(ext_path)
                    loaded = is_sqlite_vec_loaded(conn)
                except Exception:
                    loaded = False
    except Exception:
        loaded = False
    finally:
        if ext_enabled:
            try:
                conn.enable_load_extension(False)
            except Exception:
                pass

    _set_cached_state(conn, loaded)
    return loaded


def serialize_f32(vec: list[float]) -> bytes:
    if _sqlite_vec_module is not None:
        try:
            return _sqlite_vec_module.serialize_float32(vec)
        except Exception:
            pass
    return to_f32_blob([float(v) for v in vec])


def sqlite_vec_python_available() -> bool:
    return _sqlite_vec_module is not None

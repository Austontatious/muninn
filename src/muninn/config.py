import os
from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    db_path: str = os.getenv("MUNINN_DB_PATH", "./data/muninn.db")
    host: str = os.getenv("MUNINN_HOST", "127.0.0.1")
    port: int = int(os.getenv("MUNINN_PORT", "8000"))
    retrieval_mode: Literal["fts", "hybrid", "vector"] = os.getenv(
        "MUNINN_RETRIEVAL_MODE", "fts"
    )
    rrf_k0: int = int(os.getenv("MUNINN_RRF_K0", "60"))
    max_vec_scan: int = int(os.getenv("MUNINN_MAX_VEC_SCAN", "5000"))
    vec_backend: str = os.getenv("MUNINN_VEC_BACKEND", "auto")
    sqlite_vec_path: str | None = os.getenv("MUNINN_SQLITE_VEC_PATH") or None
    sqlite_vec_enabled: bool = os.getenv("MUNINN_SQLITE_VEC_ENABLED", "1") != "0"
    vec_table_prefix: str = os.getenv("MUNINN_VEC_TABLE_PREFIX", "muninn_vec")


settings = Settings()


def retrieval_mode() -> Literal["fts", "hybrid", "vector"]:
    mode = os.getenv("MUNINN_RETRIEVAL_MODE", settings.retrieval_mode)
    if mode in {"fts", "hybrid", "vector"}:
        return mode
    return "fts"


def rrf_k0() -> int:
    raw = os.getenv("MUNINN_RRF_K0", str(settings.rrf_k0))
    try:
        value = int(raw)
    except ValueError:
        return settings.rrf_k0
    return max(1, value)


def max_vec_scan() -> int:
    raw = os.getenv("MUNINN_MAX_VEC_SCAN", str(settings.max_vec_scan))
    try:
        value = int(raw)
    except ValueError:
        return settings.max_vec_scan
    return max(1, value)


def vec_backend() -> Literal["auto", "bruteforce", "sqlite_vec"]:
    raw = os.getenv("MUNINN_VEC_BACKEND", settings.vec_backend).strip().lower()
    if raw in {"auto", "bruteforce", "sqlite_vec"}:
        return raw
    return "auto"


def sqlite_vec_path() -> str | None:
    value = os.getenv("MUNINN_SQLITE_VEC_PATH")
    if value is not None:
        value = value.strip()
        return value or None
    return settings.sqlite_vec_path


def sqlite_vec_enabled() -> bool:
    value = os.getenv("MUNINN_SQLITE_VEC_ENABLED")
    if value is None:
        return settings.sqlite_vec_enabled
    return value.strip() != "0"


def vec_table_prefix() -> str:
    value = os.getenv("MUNINN_VEC_TABLE_PREFIX", settings.vec_table_prefix).strip()
    return value or "muninn_vec"

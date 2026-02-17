import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


def _default_config_dir() -> str:
    raw = os.getenv("MUNINN_CONFIG_DIR")
    if raw:
        return str(Path(raw).expanduser())
    return str(Path.home() / ".config" / "muninn")


def _default_data_dir() -> str:
    raw = os.getenv("MUNINN_DATA_DIR")
    if raw:
        return str(Path(raw).expanduser())
    return str(Path.home() / ".local" / "share" / "muninn")


def _default_db_path() -> str:
    raw = os.getenv("MUNINN_DB_PATH")
    if raw:
        return str(Path(raw).expanduser())
    return str(Path(_default_data_dir()) / "muninn.db")


class Settings(BaseModel):
    config_dir: str = _default_config_dir()
    data_dir: str = _default_data_dir()
    db_path: str = _default_db_path()
    host: str = os.getenv("MUNINN_HOST", "127.0.0.1")
    port: int = int(os.getenv("MUNINN_PORT", "8000"))
    readonly: bool = os.getenv("MUNINN_READONLY", "0") == "1"
    api_key: str | None = os.getenv("MUNINN_API_KEY") or None
    require_api_key: bool = os.getenv("MUNINN_REQUIRE_API_KEY", "0") == "1"
    api_key_header: str = os.getenv("MUNINN_API_KEY_HEADER", "X-API-Key")
    pending_retention_days: int = int(os.getenv("MUNINN_PENDING_RETENTION_DAYS", "14"))
    audit_retention_days: int = int(os.getenv("MUNINN_AUDIT_RETENTION_DAYS", "30"))
    cleanup_batch_limit: int = int(os.getenv("MUNINN_CLEANUP_BATCH_LIMIT", "2000"))
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


def config_dir() -> str:
    value = os.getenv("MUNINN_CONFIG_DIR")
    if value:
        return str(Path(value).expanduser())
    return settings.config_dir


def data_dir() -> str:
    value = os.getenv("MUNINN_DATA_DIR")
    if value:
        return str(Path(value).expanduser())
    return settings.data_dir


def db_path() -> str:
    value = os.getenv("MUNINN_DB_PATH")
    if value:
        return str(Path(value).expanduser())
    data_override = os.getenv("MUNINN_DATA_DIR")
    if data_override:
        return str(Path(data_override).expanduser() / "muninn.db")
    return settings.db_path


def readonly() -> bool:
    value = os.getenv("MUNINN_READONLY")
    if value is None:
        return settings.readonly
    return value.strip() == "1"


def api_key() -> str | None:
    value = os.getenv("MUNINN_API_KEY")
    if value is not None:
        value = value.strip()
        return value or None
    return settings.api_key


def require_api_key() -> bool:
    value = os.getenv("MUNINN_REQUIRE_API_KEY")
    if value is None:
        return settings.require_api_key
    return value.strip() == "1"


def api_key_header() -> str:
    value = os.getenv("MUNINN_API_KEY_HEADER")
    if value is None:
        value = settings.api_key_header
    value = value.strip()
    return value or "X-API-Key"


def pending_retention_days() -> int:
    raw = os.getenv("MUNINN_PENDING_RETENTION_DAYS", str(settings.pending_retention_days))
    try:
        value = int(raw)
    except ValueError:
        return settings.pending_retention_days
    return max(1, value)


def audit_retention_days() -> int:
    raw = os.getenv("MUNINN_AUDIT_RETENTION_DAYS", str(settings.audit_retention_days))
    try:
        value = int(raw)
    except ValueError:
        return settings.audit_retention_days
    return max(1, value)


def cleanup_batch_limit() -> int:
    raw = os.getenv("MUNINN_CLEANUP_BATCH_LIMIT", str(settings.cleanup_batch_limit))
    try:
        value = int(raw)
    except ValueError:
        return settings.cleanup_batch_limit
    return max(1, value)


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

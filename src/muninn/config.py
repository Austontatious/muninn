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

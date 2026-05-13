from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..human_memory.bootstrap import DEFAULT_CLIENT_NAME, DEFAULT_USER_ID


@dataclass
class MuninnConfig:
    db_path: str | None = None
    space_key: str | None = None
    cwd: str | None = None
    scope: str = "strict"
    user_id: str = DEFAULT_USER_ID
    client_name: str | None = DEFAULT_CLIENT_NAME


def default_db_path() -> str:
    return str(Path("~/.local/share/muninn/human_memory.db").expanduser().resolve())

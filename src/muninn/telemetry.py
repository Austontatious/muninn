from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, TextIO

_DEFAULT_MAX_BYTES = 5 * 1024 * 1024
_DEFAULT_BACKUP_COUNT = 5
_HANDLE: TextIO | None = None
_ACTIVE_PATH: Path | None = None
_FILE_STATE = "not_configured"
_LAST_ERROR: str | None = None
_WARNINGS_EMITTED: set[str] = set()


def _env_flag(names: tuple[str, ...], default: bool) -> bool:
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _env_text(names: tuple[str, ...]) -> str | None:
    for name in names:
        raw = os.getenv(name)
        if raw is None:
            continue
        text = raw.strip()
        if text:
            return text
    return None


def _env_int(names: tuple[str, ...], default: int | None) -> int | None:
    raw = _env_text(names)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value


def resolve_telemetry_path() -> Path | None:
    raw = _env_text(("MUNINN_TELEMETRY_PATH", "MUNINN_MCP_TELEMETRY_PATH"))
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def resolve_telemetry_flush() -> bool:
    return _env_flag(("MUNINN_TELEMETRY_FLUSH", "MUNINN_MCP_TELEMETRY_FLUSH"), False)


def resolve_telemetry_max_bytes() -> int | None:
    value = _env_int(
        ("MUNINN_TELEMETRY_MAX_BYTES", "MUNINN_MCP_TELEMETRY_MAX_BYTES"),
        _DEFAULT_MAX_BYTES,
    )
    if value is None or value <= 0:
        return None
    return value


def resolve_telemetry_backup_count() -> int:
    value = _env_int(
        ("MUNINN_TELEMETRY_BACKUP_COUNT", "MUNINN_MCP_TELEMETRY_BACKUP_COUNT"),
        _DEFAULT_BACKUP_COUNT,
    )
    if value is None:
        return _DEFAULT_BACKUP_COUNT
    return max(0, value)


def close_telemetry_handle() -> None:
    global _HANDLE
    if _HANDLE is None:
        return
    try:
        _HANDLE.close()
    except Exception:
        pass
    _HANDLE = None


def reset_telemetry_state() -> None:
    global _ACTIVE_PATH, _FILE_STATE, _LAST_ERROR, _WARNINGS_EMITTED
    close_telemetry_handle()
    _ACTIVE_PATH = None
    _FILE_STATE = "not_configured"
    _LAST_ERROR = None
    _WARNINGS_EMITTED = set()


def _warn_once(key: str, message: str) -> None:
    global _LAST_ERROR
    _LAST_ERROR = message
    if key in _WARNINGS_EMITTED:
        return
    _WARNINGS_EMITTED.add(key)
    print(
        f"Muninn telemetry warning: {message}. Falling back to console/journal telemetry.",
        file=sys.stderr,
    )


def _backup_path(path: Path, index: int) -> Path:
    return path.parent / f"{path.name}.{index}"


def _rotate_file_if_needed(path: Path, *, upcoming_bytes: int) -> bool:
    global _FILE_STATE
    max_bytes = resolve_telemetry_max_bytes()
    if max_bytes is None or not path.exists():
        return False
    try:
        current_size = path.stat().st_size
    except OSError as exc:
        _warn_once(f"stat:{path}", f"cannot stat telemetry file {path}: {exc}")
        _FILE_STATE = "file_unavailable"
        return False
    if current_size + max(0, upcoming_bytes) <= max_bytes:
        return False

    backup_count = resolve_telemetry_backup_count()
    try:
        close_telemetry_handle()
        if backup_count <= 0:
            path.unlink(missing_ok=True)
            _FILE_STATE = "rotated_truncate"
            return True
        oldest = _backup_path(path, backup_count)
        if oldest.exists():
            oldest.unlink()
        for index in range(backup_count, 1, -1):
            src = _backup_path(path, index - 1)
            dst = _backup_path(path, index)
            if src.exists():
                src.replace(dst)
        path.replace(_backup_path(path, 1))
        _FILE_STATE = "rotated"
        return True
    except Exception as exc:
        _warn_once(f"rotate:{path}", f"cannot rotate telemetry file {path}: {exc}")
        _FILE_STATE = "file_rotation_failed"
        return False


def _ensure_file_handle(path: Path) -> bool:
    global _HANDLE, _ACTIVE_PATH, _FILE_STATE
    if _ACTIVE_PATH != path:
        close_telemetry_handle()
        _ACTIVE_PATH = path
    if _HANDLE is not None:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _HANDLE = path.open("a", encoding="utf-8")
        if _FILE_STATE not in {"rotated", "rotated_truncate"}:
            _FILE_STATE = "ready"
        return True
    except Exception as exc:
        _warn_once(f"open:{path}", f"cannot open telemetry file {path}: {exc}")
        _FILE_STATE = "file_unavailable"
        _ACTIVE_PATH = None
        return False


def telemetry_context() -> dict[str, Any]:
    path = resolve_telemetry_path()
    if path is None:
        file_state = "not_configured"
        fallback = "console_or_journal_only"
    elif _FILE_STATE == "file_unavailable":
        file_state = _FILE_STATE
        fallback = "console_or_journal_only"
    else:
        file_state = _FILE_STATE if _FILE_STATE != "not_configured" else "configured"
        fallback = "console_and_jsonl" if file_state in {"ready", "rotated", "rotated_truncate"} else "console_or_journal_only"
    return {
        "telemetry_path": str(path) if path is not None else None,
        "telemetry_rotation_max_bytes": resolve_telemetry_max_bytes(),
        "telemetry_backup_count": resolve_telemetry_backup_count(),
        "telemetry_flush": resolve_telemetry_flush(),
        "telemetry_file_state": file_state,
        "telemetry_fallback": fallback,
        "telemetry_last_error": _LAST_ERROR,
    }


def append_json_event(event: dict[str, Any]) -> None:
    global _FILE_STATE
    path = resolve_telemetry_path()
    if path is None:
        _FILE_STATE = "not_configured"
        return
    payload = dict(event)
    payload.setdefault("ts", round(time.time(), 3))
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    _rotate_file_if_needed(path, upcoming_bytes=len(serialized) + 1)
    if not _ensure_file_handle(path):
        return
    try:
        _HANDLE.write(serialized + "\n")
        if resolve_telemetry_flush():
            _HANDLE.flush()
        if _FILE_STATE not in {"rotated", "rotated_truncate"}:
            _FILE_STATE = "ready"
    except Exception as exc:
        close_telemetry_handle()
        _FILE_STATE = "file_unavailable"
        _warn_once(f"write:{path}", f"cannot write telemetry file {path}: {exc}")


def emit_event(
    event: dict[str, Any],
    *,
    stream_prefix: str | None = None,
    stream: str = "stdout",
) -> None:
    payload = dict(event)
    payload.setdefault("ts", round(time.time(), 3))
    serialized = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    if stream_prefix:
        target = sys.stderr if stream == "stderr" else sys.stdout
        print(f"{stream_prefix} {serialized}", file=target)
    append_json_event(payload)

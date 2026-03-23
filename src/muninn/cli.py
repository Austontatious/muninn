from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import platform
import re
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import uvicorn

from . import __version__, db
from .config import config_dir, data_dir, db_path, readonly, settings
from .human_memory.bootstrap import (
    DEFAULT_USER_ID as HUMAN_MEMORY_DEFAULT_USER_ID,
    apply_init_schema as human_memory_apply_init_schema,
    bootstrap_defaults as human_memory_bootstrap_defaults,
    open_db as human_memory_open_db,
)
from .human_memory.interactions import list_interaction_events as human_memory_list_interaction_events
from .human_memory.heal import run_heal as run_human_memory_heal
from .human_memory.policy import POLICY_KINDS, query_policy_cards as human_memory_query_policy_cards
from .human_memory.spaces import (
    ResolvedSpace as HumanMemoryResolvedSpace,
    canonicalize_space_key as human_memory_canonicalize_space_key,
    get_or_create_space as human_memory_get_or_create_space,
    get_space_summary as human_memory_get_space_summary,
    resolve_space_from_cwd as human_memory_resolve_space_from_cwd,
)
from .migrations import apply_migrations
from .telemetry import emit_event as emit_telemetry_event, telemetry_context
from .vector import store as vector_store


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    host = args.host or os.getenv("MUNINN_HOST", settings.host)
    port = int(args.port or int(os.getenv("MUNINN_PORT", str(settings.port))))
    resolved_db_path = args.db_path or os.getenv("MUNINN_DB_PATH") or db_path()
    resolved_config_dir = config_dir()
    resolved_data_dir = data_dir()
    namespace_default = os.getenv("MUNINN_NAMESPACE", "default")
    if resolved_db_path:
        os.environ["MUNINN_DB_PATH"] = resolved_db_path
    return {
        "host": host,
        "port": port,
        "config_dir": resolved_config_dir,
        "data_dir": resolved_data_dir,
        "db_path": resolved_db_path,
        "namespace_default": namespace_default,
        "readonly": readonly(),
    }


def _ensure_runtime_dirs(config_dir_path: str, data_dir_path: str, db_path_value: str) -> None:
    Path(config_dir_path).expanduser().mkdir(parents=True, exist_ok=True)
    Path(data_dir_path).expanduser().mkdir(parents=True, exist_ok=True)
    Path(db_path_value).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _init_schema_and_migrations() -> None:
    conn = db.connect()
    try:
        db.init_db(conn)
    except sqlite3.OperationalError as exc:
        # Existing pre-v0.5 DBs may fail schema apply before namespace migration.
        if "no such column: namespace" not in str(exc).lower():
            raise
        conn.rollback()
    apply_migrations(conn)
    db.init_db(conn)
    conn.close()


def _port_available(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _display_path(path: str) -> str:
    expanded = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    try:
        relative = expanded.relative_to(home)
    except ValueError:
        return str(expanded)
    return f"~/{relative.as_posix()}"


def _print_up_banner(config: dict[str, Any]) -> None:
    base_url = f"http://{config['host']}:{config['port']}"
    print("Muninn running")
    print(f"API: {base_url}")
    print(f"DB:  {_display_path(str(config['db_path']))}")
    print(f"Namespace default: {config['namespace_default']}")
    print(f"Readonly: {str(config['readonly']).lower()}")


def _cmd_up(args: argparse.Namespace) -> int:
    config = _resolve_runtime_config(args)
    host = str(config["host"])
    port = int(config["port"])

    if not _port_available(host, port):
        suggested_port = 8010 if port == 8000 else (port + 1)
        print(f"Port {port} already in use.", file=sys.stderr)
        print(f"Run: muninn up --port {suggested_port}", file=sys.stderr)
        return 1

    try:
        _ensure_runtime_dirs(
            str(config["config_dir"]),
            str(config["data_dir"]),
            str(config["db_path"]),
        )
        _init_schema_and_migrations()
    except Exception as exc:
        print(f"Failed to initialize Muninn: {exc}", file=sys.stderr)
        print("Run: muninn doctor", file=sys.stderr)
        return 1

    _print_up_banner(config)

    uvicorn.run(
        "muninn.api:app",
        host=host,
        port=port,
        reload=bool(args.reload),
        log_level=str(args.log_level),
    )
    return 0


def _cmd_mcp_up(args: argparse.Namespace) -> int:
    try:
        from .mcp_server import run_mcp_server
    except ModuleNotFoundError as exc:
        if exc.name == "mcp":
            print(
                "MCP runtime dependency is missing. Install project dependencies (pip install -e .).",
                file=sys.stderr,
            )
            return 1
        raise

    host = args.host or "127.0.0.1"
    port = int(args.port or 8765)
    base_url = args.base_url or os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    try:
        run_mcp_server(host=host, port=port, base_url=base_url)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _cmd_mcp_stdio(args: argparse.Namespace) -> int:
    try:
        from .mcp_server import run_mcp_stdio
    except ModuleNotFoundError as exc:
        if exc.name == "mcp":
            print(
                "MCP runtime dependency is missing. Install project dependencies (pip install -e .).",
                file=sys.stderr,
            )
            return 1
        raise

    base_url = args.base_url or os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    run_mcp_stdio(base_url=base_url)
    return 0


def _connector_config_path() -> Path:
    return Path(config_dir()).expanduser() / "config.json"


def _load_connector_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return dict(payload)


def _save_connector_config(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _ensure_connector_api_key(config_path: Path) -> tuple[str, str]:
    payload = _load_connector_config(config_path)
    header_name = (
        os.getenv("MUNINN_API_KEY_HEADER") or str(payload.get("api_key_header") or "X-API-Key")
    )
    header_name = header_name.strip() or "X-API-Key"
    api_key = os.getenv("MUNINN_API_KEY") or str(payload.get("api_key") or "")
    api_key = api_key.strip()

    changed = False
    if not api_key:
        api_key = f"sk_muninn_{secrets.token_urlsafe(32)}"
        changed = True

    if payload.get("api_key") != api_key:
        payload["api_key"] = api_key
        changed = True
    if payload.get("api_key_header") != header_name:
        payload["api_key_header"] = header_name
        changed = True
    if "updated_at" not in payload:
        payload["updated_at"] = int(time.time())
        changed = True

    if changed:
        payload["updated_at"] = int(time.time())
        _save_connector_config(config_path, payload)

    return api_key, header_name


def _spawn_background(command: list[str], env: dict[str, str], log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] starting: {' '.join(command)}\n"
        )
    with open(log_path, "a", encoding="utf-8") as log_file:
        return subprocess.Popen(
            command,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )


def _is_api_healthy(base_url: str) -> bool:
    health_url = f"{base_url.rstrip('/')}/health"
    try:
        response = httpx.get(health_url, timeout=2.0)
    except Exception:
        return False
    return response.status_code == 200


def _is_mcp_available(mcp_url: str, header_name: str, api_key: str) -> bool:
    headers = {"accept": "text/event-stream", header_name: api_key}
    try:
        response = httpx.get(mcp_url, headers=headers, timeout=2.0)
    except Exception:
        return False
    return response.status_code in {200, 400, 406}


def _wait_until_ready(check_fn, timeout_s: float = 15.0, interval_s: float = 0.25) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if check_fn():
            return True
        time.sleep(interval_s)
    return False


def _ensure_api_running(
    host: str,
    port: int,
    api_key: str,
    header_name: str,
    resolved_config_dir: str,
    resolved_data_dir: str,
    resolved_db_path: str,
) -> tuple[bool, bool]:
    base_url = f"http://{host}:{port}"
    if _is_api_healthy(base_url):
        return True, False

    log_path = Path(resolved_data_dir).expanduser() / "muninn-api.log"
    env = os.environ.copy()
    env["MUNINN_CONFIG_DIR"] = resolved_config_dir
    env["MUNINN_DATA_DIR"] = resolved_data_dir
    env["MUNINN_DB_PATH"] = resolved_db_path
    env["MUNINN_API_KEY"] = api_key
    env["MUNINN_API_KEY_HEADER"] = header_name
    env["MUNINN_REQUIRE_API_KEY"] = "1"

    process = _spawn_background(
        [
            sys.executable,
            "-m",
            "muninn.cli",
            "up",
            "--host",
            host,
            "--port",
            str(port),
        ],
        env=env,
        log_path=log_path,
    )

    if _wait_until_ready(lambda: _is_api_healthy(base_url), timeout_s=20.0):
        return True, True

    if process.poll() is not None:
        print(f"Failed to start Muninn API. See log: {_display_path(str(log_path))}", file=sys.stderr)
    else:
        print(
            f"Muninn API did not become healthy in time. See log: {_display_path(str(log_path))}",
            file=sys.stderr,
        )
    print("Run: muninn up", file=sys.stderr)
    return False, True


def _ensure_mcp_running(
    host: str,
    port: int,
    base_url: str,
    api_key: str,
    header_name: str,
    resolved_data_dir: str,
) -> tuple[bool, bool]:
    mcp_url = f"http://{host}:{port}/mcp"
    if _is_mcp_available(mcp_url, header_name, api_key):
        return True, False

    log_path = Path(resolved_data_dir).expanduser() / "muninn-mcp.log"
    env = os.environ.copy()
    env["MUNINN_BASE_URL"] = base_url
    env["MUNINN_API_KEY"] = api_key
    env["MUNINN_API_KEY_HEADER"] = header_name
    env["MUNINN_MCP_REQUIRE_API_KEY"] = "1"

    process = _spawn_background(
        [
            sys.executable,
            "-m",
            "muninn.cli",
            "mcp",
            "up",
            "--host",
            host,
            "--port",
            str(port),
            "--base-url",
            base_url,
        ],
        env=env,
        log_path=log_path,
    )

    if _wait_until_ready(lambda: _is_mcp_available(mcp_url, header_name, api_key), timeout_s=20.0):
        return True, True

    if process.poll() is not None:
        print(f"Failed to start Muninn MCP. See log: {_display_path(str(log_path))}", file=sys.stderr)
    else:
        print(
            f"Muninn MCP did not become ready in time. See log: {_display_path(str(log_path))}",
            file=sys.stderr,
        )
    print("Run: muninn mcp up", file=sys.stderr)
    return False, True


def _cmd_enable_chatgpt(args: argparse.Namespace) -> int:
    api_host = "127.0.0.1"
    mcp_host = "127.0.0.1"
    api_port = int(args.api_port)
    mcp_port = int(args.mcp_port)
    resolved_config_dir = config_dir()
    resolved_data_dir = data_dir()
    resolved_db_path = db_path()

    try:
        _ensure_runtime_dirs(resolved_config_dir, resolved_data_dir, resolved_db_path)
        _init_schema_and_migrations()
    except Exception as exc:
        print(f"Failed to prepare runtime: {exc}", file=sys.stderr)
        print("Run: muninn up", file=sys.stderr)
        return 1

    config_path = _connector_config_path()
    api_key, header_name = _ensure_connector_api_key(config_path)
    base_url = f"http://{api_host}:{api_port}"
    mcp_url = f"http://{mcp_host}:{mcp_port}/mcp"

    api_ready, api_started = _ensure_api_running(
        host=api_host,
        port=api_port,
        api_key=api_key,
        header_name=header_name,
        resolved_config_dir=resolved_config_dir,
        resolved_data_dir=resolved_data_dir,
        resolved_db_path=resolved_db_path,
    )
    if not api_ready:
        return 1

    mcp_ready, mcp_started = _ensure_mcp_running(
        host=mcp_host,
        port=mcp_port,
        base_url=base_url,
        api_key=api_key,
        header_name=header_name,
        resolved_data_dir=resolved_data_dir,
    )
    if not mcp_ready:
        return 1

    if api_started:
        print("Started Muninn API in background.")
    else:
        print("Muninn API already running.")
    if mcp_started:
        print("Started Muninn MCP in background.")
    else:
        print("Muninn MCP already running.")

    print()
    print("MCP local endpoint:")
    print(mcp_url)
    print()
    print("Header name:")
    print(header_name)
    print()
    print("API key:")
    print(api_key)
    print()
    if args.tunnel:
        success, tunnel_url, reason = _start_cloudflared_tunnel(
            mcp_port=mcp_port,
            resolved_data_dir=resolved_data_dir,
        )
        if not success:
            print(f"Cloudflared tunnel failed: {reason}", file=sys.stderr)
            print(f"Run manually: cloudflared tunnel --url http://127.0.0.1:{mcp_port}", file=sys.stderr)
            print("Install cloudflared manually if needed: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
            return 1
        print("MCP public endpoint:")
        print(f"{tunnel_url}/mcp")
        print()
        print("Use this URL in ChatGPT -> Settings -> Connectors")
    else:
        print(f"Start tunnel to http://127.0.0.1:{mcp_port}")
        print("Use resulting https://.../mcp in ChatGPT -> Settings -> Connectors")
    print(f"Add header {header_name}: {api_key}")
    print("Note: ChatGPT connector requires HTTPS.")
    return 0


def _cloudflared_download_url() -> str | None:
    system_name = platform.system().lower()
    machine = platform.machine().lower()
    if system_name == "linux" and machine in {"x86_64", "amd64"}:
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    if system_name == "linux" and machine in {"aarch64", "arm64"}:
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    return None


def _resolve_cloudflared_binary(resolved_data_dir: str) -> tuple[str | None, str | None]:
    existing = shutil.which("cloudflared")
    if existing:
        return existing, None

    local_bin = Path(resolved_data_dir).expanduser() / "bin" / "cloudflared"
    if local_bin.exists():
        return str(local_bin), None

    download_url = _cloudflared_download_url()
    if not download_url:
        return None, "cloudflared auto-download unsupported on this platform"

    local_bin.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(download_url, timeout=30) as response:
            local_bin.write_bytes(response.read())
        local_bin.chmod(0o755)
    except Exception as exc:
        return None, f"download failed ({exc})"

    return str(local_bin), None


def _extract_trycloudflare_url(text: str) -> str | None:
    match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", text)
    if not match:
        return None
    return match.group(0)


def _start_cloudflared_tunnel(mcp_port: int, resolved_data_dir: str) -> tuple[bool, str | None, str]:
    cloudflared_bin, error = _resolve_cloudflared_binary(resolved_data_dir)
    if not cloudflared_bin:
        return False, None, error or "cloudflared unavailable"

    log_path = Path(resolved_data_dir).expanduser() / "cloudflared.log"
    command = [
        cloudflared_bin,
        "tunnel",
        "--url",
        f"http://127.0.0.1:{mcp_port}",
        "--no-autoupdate",
    ]
    process = _spawn_background(command, env=os.environ.copy(), log_path=log_path)

    deadline = time.time() + 25.0
    while time.time() < deadline:
        if process.poll() is not None:
            return False, None, f"process exited early (code {process.poll()})"
        if log_path.exists():
            url = _extract_trycloudflare_url(log_path.read_text(encoding="utf-8", errors="ignore"))
            if url:
                return True, url, ""
        time.sleep(0.25)

    return False, None, "timed out waiting for tunnel URL"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="muninn",
        description="Muninn CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"muninn {__version__}",
    )

    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status", help="Check Muninn service health")
    status.add_argument(
        "--base-url",
        default=os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000"),
        help="Muninn base URL (default: %(default)s)",
    )
    status.add_argument(
        "--mcp-url",
        default=os.getenv("MUNINN_MCP_URL", "http://127.0.0.1:8765/mcp"),
        help="Muninn MCP URL (default: %(default)s)",
    )
    status.add_argument("--timeout", type=float, default=5.0, help="Request timeout seconds")
    audit = sub.add_parser(
        "audit",
        help="Analyze MCP tool usage and memory-discipline adherence",
    )
    audit.add_argument(
        "--last",
        default="2h",
        help="Lookback window (e.g. 30m, 2h, 1d). Ignored if --since is set.",
    )
    audit.add_argument(
        "--since",
        default=None,
        help="Absolute start time (e.g. '2026-02-19 15:00').",
    )
    audit.add_argument(
        "--telemetry-path",
        default=os.getenv("MUNINN_MCP_TELEMETRY_PATH", "~/.local/share/muninn/mcp_telemetry.jsonl"),
        help="JSONL telemetry file path (default: %(default)s).",
    )
    audit.add_argument(
        "--unit",
        default="muninn-mcp.service",
        help="systemd user unit for journal fallback (default: %(default)s).",
    )
    audit.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="Maximum events to analyze after filtering (default: %(default)s).",
    )
    audit.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON report.",
    )

    heal = sub.add_parser(
        "heal",
        help="Run memory maintenance: detect duplicates/conflicts/stale cards and optionally apply merges",
    )
    heal.add_argument(
        "--space-key",
        default=None,
        help="Optional space key to scope healing (default: all spaces).",
    )
    heal.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Lookback window in days for duplicate/conflict analysis (default: %(default)s).",
    )
    heal.add_argument(
        "--max-actions",
        type=int,
        default=20,
        help="Maximum merge actions when --apply is enabled (default: %(default)s).",
    )
    heal.add_argument(
        "--apply",
        action="store_true",
        help="Apply merge actions; without this flag heal runs in report-only mode.",
    )
    heal.add_argument(
        "--db-path",
        default=_default_human_memory_db_path(),
        help="Human-memory DB path (default: %(default)s).",
    )
    heal.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON report.",
    )

    policy = sub.add_parser(
        "policy",
        help="Inspect learned policy-state and recent interaction signals",
    )
    policy_sub = policy.add_subparsers(dest="policy_command")

    policy_list = policy_sub.add_parser("list", help="List active policy cards for a space")
    policy_list.add_argument("--space-key", default=None, help="Explicit space key (default: auto from --cwd).")
    policy_list.add_argument("--cwd", default=None, help="Project cwd for auto space resolution.")
    policy_list.add_argument(
        "--db-path",
        default=_default_human_memory_db_path(),
        help="Human-memory DB path (default: %(default)s).",
    )
    policy_list.add_argument("--query", default=None, help="Optional lexical filter over policy content.")
    policy_list.add_argument(
        "--scope-type",
        action="append",
        dest="scope_types",
        default=None,
        help="Scope type filter; repeat for multiple values.",
    )
    policy_list.add_argument("--scope-key", default=None, help="Optional exact scope key filter.")
    policy_list.add_argument("--tool-name", default=None, help="Optional tool-name filter.")
    policy_list.add_argument("--task-type", default=None, help="Optional task-type filter.")
    policy_list.add_argument(
        "--include-global",
        action="store_true",
        help="Include global policy fallback in addition to the canonical project space.",
    )
    policy_list.add_argument("--limit", type=int, default=10, help="Maximum cards to return.")
    policy_list.add_argument("--include-body", action="store_true", help="Include full card bodies.")
    policy_list.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")

    policy_show = policy_sub.add_parser("show", help="Show one policy card in detail")
    policy_show.add_argument("card_id", help="Policy card id.")
    policy_show.add_argument(
        "--db-path",
        default=_default_human_memory_db_path(),
        help="Human-memory DB path (default: %(default)s).",
    )
    policy_show.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")

    policy_events = policy_sub.add_parser("events", help="List recent interaction events")
    policy_events.add_argument("--space-key", default=None, help="Explicit space key (default: auto from --cwd).")
    policy_events.add_argument("--cwd", default=None, help="Project cwd for auto space resolution.")
    policy_events.add_argument(
        "--db-path",
        default=_default_human_memory_db_path(),
        help="Human-memory DB path (default: %(default)s).",
    )
    policy_events.add_argument("--session-id", default=None, help="Optional session id filter.")
    policy_events.add_argument(
        "--event-type",
        action="append",
        dest="event_types",
        default=None,
        help="Optional interaction event type filter; repeat for multiple values.",
    )
    policy_events.add_argument(
        "--promoted",
        choices=["all", "promoted", "unpromoted"],
        default="all",
        help="Filter by promotion state.",
    )
    policy_events.add_argument("--limit", type=int, default=20, help="Maximum events to return.")
    policy_events.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON.")

    up = sub.add_parser("up", help="Start Muninn API server")
    up.add_argument("--host", default=None, help="Host bind (default from MUNINN_HOST or config)")
    up.add_argument("--port", type=int, default=None, help="Port (default from MUNINN_PORT or config)")
    up.add_argument(
        "--db-path",
        default=None,
        help="SQLite DB path (default from MUNINN_DB_PATH or config)",
    )
    up.add_argument("--reload", action="store_true", help="Enable uvicorn reload mode")
    up.add_argument("--log-level", default="info", help="Uvicorn log level")

    doctor = sub.add_parser("doctor", help="Run diagnostics and print PASS/FAIL checks")
    doctor.add_argument("--host", default=None, help="Host for port check")
    doctor.add_argument("--port", type=int, default=None, help="Port for port check")
    doctor.add_argument("--db-path", default=None, help="DB path check")
    doctor.add_argument(
        "--base-url",
        default=None,
        help="Base URL for running-instance checks (defaults to host:port)",
    )

    mcp = sub.add_parser("mcp", help="Run Muninn MCP wrapper server")
    mcp_sub = mcp.add_subparsers(dest="mcp_command")

    mcp_up = mcp_sub.add_parser("up", help="Start local MCP server (streamable HTTP, default)")
    mcp_up.add_argument(
        "--host",
        default="127.0.0.1",
        help="MCP bind host (default loopback; non-loopback requires auth)",
    )
    mcp_up.add_argument("--port", type=int, default=8765, help="MCP bind port")
    mcp_up.add_argument(
        "--base-url",
        default=os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000"),
        help="Muninn HTTP base URL to forward requests to",
    )

    mcp_stdio = mcp_sub.add_parser(
        "stdio",
        help="Start Muninn MCP over stdio (compatibility mode)",
    )
    mcp_stdio.add_argument(
        "--base-url",
        default=os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000"),
        help="Muninn HTTP base URL to forward requests to",
    )

    enable_chatgpt = sub.add_parser(
        "enable-chatgpt",
        help="Prepare local MCP connector info and provision API key",
    )
    enable_chatgpt.add_argument("--api-port", type=int, default=8000, help="Muninn API port")
    enable_chatgpt.add_argument("--mcp-port", type=int, default=8765, help="Muninn MCP port")
    enable_chatgpt.set_defaults(tunnel=True)
    enable_chatgpt.add_argument(
        "--tunnel",
        dest="tunnel",
        action="store_true",
        help="Start Cloudflare quick tunnel (default)",
    )
    enable_chatgpt.add_argument(
        "--no-tunnel",
        dest="tunnel",
        action="store_false",
        help="Skip tunnel setup and print manual instructions",
    )

    return parser


def _default_human_memory_db_path() -> str:
    configured = os.getenv("MUNINN_HUMAN_MEMORY_DB_PATH")
    if configured:
        return str(Path(configured).expanduser().resolve())
    return str(Path("~/.local/share/muninn/human_memory.db").expanduser().resolve())


def _new_cli_request_id() -> str:
    return secrets.token_hex(8)


def _emit_cli_command_event(command: str, *, request_id: str, status: str, **payload: Any) -> None:
    emit_telemetry_event(
        {
            "event": "cli_command",
            "module": "muninn.cli",
            "command": command,
            "request_id": request_id,
            "status": status,
            **telemetry_context(),
            **payload,
        },
        stream_prefix="MUNINN_CLI",
        stream="stderr",
    )


def _open_human_memory_conn_with_init(
    db_path_value: str,
    *,
    correlation_id: str | None = None,
) -> tuple[sqlite3.Connection, Path]:
    db_path = Path(str(db_path_value)).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = human_memory_open_db(str(db_path))
    human_memory_apply_init_schema(conn, correlation_id=correlation_id)
    human_memory_bootstrap_defaults(conn, correlation_id=correlation_id)
    return conn, db_path


def _resolve_cli_policy_space(
    conn: sqlite3.Connection,
    *,
    cwd: str | None,
    space_key: str | None,
) -> dict[str, Any]:
    requested_space_key = str(space_key or "").strip()
    if requested_space_key:
        if requested_space_key != "global":
            human_memory_get_or_create_space(
                conn,
                user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
                resolved=HumanMemoryResolvedSpace(
                    key=requested_space_key,
                    label=requested_space_key,
                    meta_json='{"source":"cli_space_key"}',
                ),
            )
        canonical_key = human_memory_canonicalize_space_key(
            conn,
            user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
            space_key=requested_space_key,
        )
        summary = human_memory_get_space_summary(
            conn,
            user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
            space_key=canonical_key,
        )
        return {
            "requested_space_key": requested_space_key,
            "cwd": cwd,
            "space": summary,
            "resolution_kind": "explicit_space_key",
        }

    resolved_cwd = str(cwd or os.getcwd()).strip()
    resolved = human_memory_resolve_space_from_cwd(resolved_cwd)
    human_memory_get_or_create_space(
        conn,
        user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
        resolved=resolved,
    )
    summary = human_memory_get_space_summary(
        conn,
        user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
        space_key=resolved.key,
    )
    return {
        "requested_space_key": None,
        "cwd": resolved_cwd,
        "space": summary,
        "resolution_kind": "cwd_auto",
    }


def _load_policy_card_by_id(conn: sqlite3.Connection, *, card_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT c.id, s.key AS space_key, c.kind, c.title, c.summary, c.body,
               c.created_at, c.updated_at, c.context_json
        FROM cards c
        JOIN spaces s ON s.id = c.space_id
        WHERE c.user_id = ?
          AND c.id = ?
          AND c.kind IN ({placeholders})
        LIMIT 1
        """.format(placeholders=", ".join(["?"] * len(POLICY_KINDS))),
        (HUMAN_MEMORY_DEFAULT_USER_ID, card_id, *POLICY_KINDS),
    ).fetchone()
    if row is None:
        return None
    payload = human_memory_query_policy_cards(
        conn,
        user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
        space_key=str(row["space_key"]),
        include_global=False,
        limit=100,
        include_body=True,
    )
    for card in payload.get("cards", []):
        if str(card.get("id")) == str(row["id"]):
            return card
    return None


def _derive_mcp_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    if port == 8000:
        port = 8765
    return f"{scheme}://{host}:{port}/mcp"


def _extract_sse_json_body(body: str) -> dict[str, Any]:
    for raw in body.splitlines():
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        candidate = line[5:].strip()
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    raise ValueError("no_json_data_event")


def _check_mcp_ping(mcp_url: str, timeout: float) -> tuple[bool, dict[str, Any] | None, str | None]:
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
    }
    try:
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "muninn-status", "version": __version__},
            },
        }
        init_resp = httpx.post(mcp_url, headers=headers, json=init_payload, timeout=timeout)
        init_resp.raise_for_status()
        session_id = init_resp.headers.get("mcp-session-id")
        if not session_id:
            return False, None, "missing_mcp_session_id"

        call_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "muninn.system.ping",
                "arguments": {},
            },
        }
        call_headers = dict(headers)
        call_headers["mcp-session-id"] = session_id
        call_resp = httpx.post(mcp_url, headers=call_headers, json=call_payload, timeout=timeout)
        call_resp.raise_for_status()
        outer = _extract_sse_json_body(call_resp.text)
        result = outer.get("result")
        if not isinstance(result, dict):
            return False, None, "missing_result"
        if bool(result.get("isError")):
            return False, None, "tool_error"
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            return False, None, "missing_structured_content"
        return bool(structured.get("ok", False)), structured, None
    except Exception as exc:
        return False, None, str(exc)


def _cmd_status(base_url: str, mcp_url: str | None, timeout: float) -> int:
    effective_mcp_url = (mcp_url or "").strip() or _derive_mcp_url(base_url)
    health_url = base_url.rstrip("/") + "/health"
    api_ok = False
    api_payload: dict[str, Any] | None = None
    api_error: str | None = None
    try:
        response = httpx.get(health_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict):
            api_payload = payload
            api_ok = bool(payload.get("ok", False))
        else:
            api_payload = {"raw": payload}
            api_ok = True
    except Exception as exc:
        api_error = str(exc)

    mcp_ok, mcp_ping, mcp_error = _check_mcp_ping(effective_mcp_url, timeout)
    overall_ok = api_ok and mcp_ok
    out: dict[str, Any] = {
        "ok": overall_ok,
        "version": __version__,
        "api": {
            "base_url": base_url,
            "health_url": health_url,
            "ok": api_ok,
            "health": api_payload,
            "error": api_error,
        },
        "mcp": {
            "url": effective_mcp_url,
            "ok": mcp_ok,
            "ping": mcp_ping,
            "error": mcp_error,
        },
        "db_paths": {
            "core": str(Path(db_path()).expanduser().resolve()),
            "human_memory": _default_human_memory_db_path(),
        },
    }
    print(json.dumps(out))
    return 0 if overall_ok else 1


def _parse_last_seconds(last_value: str) -> int:
    raw = str(last_value).strip().lower()
    match = re.fullmatch(r"(\d+)\s*([smhd])", raw)
    if not match:
        raise ValueError("invalid_last_format")
    value = int(match.group(1))
    unit = match.group(2)
    multiplier = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
    }[unit]
    return max(1, value * multiplier)


def _parse_since_epoch(since_value: str | None) -> float | None:
    if not since_value:
        return None
    raw = str(since_value).strip()
    if not raw:
        return None
    try:
        if re.fullmatch(r"\d+(\.\d+)?", raw):
            return float(raw)
    except ValueError:
        pass
    try:
        return float(datetime.fromisoformat(raw).timestamp())
    except Exception:
        pass
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    )
    for fmt in formats:
        try:
            return float(datetime.strptime(raw, fmt).timestamp())
        except Exception:
            continue
    return None


def _event_timestamp(event: dict[str, Any]) -> float | None:
    raw = event.get("ts")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _normalize_tool_event(raw: dict[str, Any], idx: int) -> dict[str, Any] | None:
    tool = raw.get("tool")
    if not isinstance(tool, str) or not tool.strip():
        return None
    payload = dict(raw)
    payload["tool"] = tool.strip()
    payload["invoked_as"] = str(payload.get("invoked_as") or payload["tool"])
    payload["deprecated_alias"] = bool(payload.get("deprecated_alias", False))
    status = str(payload.get("status", "")).strip().lower()
    has_error = bool(payload.get("error_code")) or status == "error"
    payload["event"] = str(payload.get("event") or ("tool_error" if has_error else "tool_call"))
    payload["_idx"] = idx
    return payload


def _load_events_from_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except Exception:
                continue
            if not isinstance(payload, dict):
                continue
            event = _normalize_tool_event(payload, idx)
            if event is None:
                continue
            rows.append(event)
    return rows


def _parse_mcp_tool_line(line: str, idx: int) -> dict[str, Any] | None:
    if "MCP_TOOL" not in line:
        return None
    _, _, raw_json = line.partition("MCP_TOOL")
    raw_json = raw_json.strip()
    if not raw_json:
        return None
    try:
        payload = json.loads(raw_json)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return _normalize_tool_event(payload, idx)


def _load_events_from_journal(unit: str, since_arg: str | None) -> tuple[list[dict[str, Any]], str | None]:
    cmd = ["journalctl", "--user", "-u", unit, "--no-pager", "-o", "cat"]
    if since_arg:
        cmd.extend(["--since", since_arg])
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return [], "journalctl unavailable"
    if proc.returncode not in {0, 1}:
        detail = proc.stderr.strip() if proc.stderr else f"journalctl exit {proc.returncode}"
        return [], detail
    rows: list[dict[str, Any]] = []
    for idx, line in enumerate(proc.stdout.splitlines()):
        event = _parse_mcp_tool_line(line, idx)
        if event is not None:
            rows.append(event)
    return rows, None


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = max(0, int(math.ceil(0.95 * len(ordered))) - 1)
    return float(ordered[idx])


def _event_space_signature(event: dict[str, Any]) -> str | None:
    space_key = event.get("space_key")
    if isinstance(space_key, str) and space_key.strip():
        return space_key.strip()
    space_keys = event.get("space_keys")
    if isinstance(space_keys, list):
        normalized = [str(item).strip() for item in space_keys if str(item).strip()]
        if normalized:
            return ",".join(normalized)
    return None


def _sessionize_events(events: list[dict[str, Any]], gap_seconds: int = 600) -> list[list[dict[str, Any]]]:
    if not events:
        return []
    ordered = sorted(
        events,
        key=lambda item: (
            _event_timestamp(item) if _event_timestamp(item) is not None else float("inf"),
            int(item.get("_idx", 0)),
        ),
    )
    sessions: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    prev_ts: float | None = None
    prev_space: str | None = None
    for event in ordered:
        ts = _event_timestamp(event)
        space_sig = _event_space_signature(event)
        start_new = False
        if current:
            if ts is not None and prev_ts is not None and (ts - prev_ts) > gap_seconds:
                start_new = True
            elif (
                space_sig
                and prev_space
                and space_sig != prev_space
                and (ts is None or prev_ts is None or (ts - prev_ts) > 5)
            ):
                start_new = True
        if start_new:
            sessions.append(current)
            current = []
        current.append(event)
        if ts is not None:
            prev_ts = ts
        if space_sig is not None:
            prev_space = space_sig
    if current:
        sessions.append(current)
    return sessions


def _build_audit_report(
    events: list[dict[str, Any]],
    *,
    source: str,
    window: dict[str, Any],
) -> dict[str, Any]:
    normalized = sorted(
        events,
        key=lambda item: (
            _event_timestamp(item) if _event_timestamp(item) is not None else float("inf"),
            int(item.get("_idx", 0)),
        ),
    )
    tool_counts: dict[str, int] = {}
    tool_errors: dict[str, int] = {}
    durations_by_tool: dict[str, list[float]] = {}
    search_events: list[dict[str, Any]] = []
    upsert_ok_events: list[dict[str, Any]] = []
    for event in normalized:
        tool = str(event.get("tool", ""))
        if not tool:
            continue
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
        status = str(event.get("status", "")).lower()
        if str(event.get("event", "")) == "tool_error" or status == "error":
            tool_errors[tool] = tool_errors.get(tool, 0) + 1
        duration_ms = event.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            durations_by_tool.setdefault(tool, []).append(float(duration_ms))
        if tool == "muninn.cards.search" and status == "ok":
            search_events.append(event)
        if tool == "muninn.cards.upsert" and status == "ok":
            upsert_ok_events.append(event)

    sessions = _sessionize_events(normalized)
    session_reports: list[dict[str, Any]] = []
    for idx, session in enumerate(sessions, start=1):
        first_tool = None
        for event in session:
            name = str(event.get("tool", ""))
            if name == "muninn.system.ping":
                continue
            first_tool = name
            break
        resolve_idx = next(
            (
                pos
                for pos, event in enumerate(session)
                if str(event.get("tool", "")) == "muninn.spaces.resolve"
            ),
            None,
        )
        recent_idx = next(
            (
                pos
                for pos, event in enumerate(session)
                if str(event.get("tool", "")) == "muninn.cards.recent"
                and str(event.get("scope", "")) == "strict"
            ),
            None,
        )
        search_idx = next(
            (
                pos
                for pos, event in enumerate(session)
                if str(event.get("tool", "")) == "muninn.cards.search"
                and str(event.get("scope", "")) == "soft"
            ),
            None,
        )
        ordered_start = (
            resolve_idx is not None
            and recent_idx is not None
            and search_idx is not None
            and resolve_idx < recent_idx < search_idx
        )
        upserts_ok = sum(
            1
            for event in session
            if str(event.get("tool", "")) == "muninn.cards.upsert"
            and str(event.get("status", "")).lower() == "ok"
        )
        rate_limit_hits = sum(
            1
            for event in session
            if str(event.get("error_code", "")) == "WriteRateLimited"
        )
        session_reports.append(
            {
                "session_id": idx,
                "events": len(session),
                "resolve_first": first_tool == "muninn.spaces.resolve",
                "has_recent_strict": recent_idx is not None,
                "has_search_soft": search_idx is not None,
                "ordered_start": ordered_start,
                "upserts_ok": upserts_ok,
                "rate_limit_hits": rate_limit_hits,
            }
        )

    sessions_total = len(session_reports)
    ordered_sessions = sum(1 for item in session_reports if item["ordered_start"])
    resolve_first_sessions = sum(1 for item in session_reports if item["resolve_first"])
    upserts_per_session = [int(item["upserts_ok"]) for item in session_reports]
    sessions_with_upserts = sum(1 for value in upserts_per_session if value > 0)
    sessions_upsert_1_3 = sum(1 for value in upserts_per_session if 1 <= value <= 3)
    sessions_upsert_over_3 = sum(1 for value in upserts_per_session if value > 3)
    rate_limit_hits_total = sum(int(item["rate_limit_hits"]) for item in session_reports)

    total_matches_values: list[int] = []
    top_scores: list[float] = []
    search_durations: list[float] = []
    short_queries = 0
    for event in search_events:
        tm = event.get("total_matches")
        if isinstance(tm, (int, float)):
            total_matches_values.append(int(tm))
        top_score = event.get("top_score")
        if isinstance(top_score, (int, float)):
            top_scores.append(float(top_score))
        duration_ms = event.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            search_durations.append(float(duration_ms))
        query = str(event.get("query", "")).strip()
        if len(query) < 12:
            short_queries += 1

    zero_match_count = sum(1 for value in total_matches_values if value == 0)
    low_top_score_count = sum(1 for value in top_scores if value < 0.35)
    low_summary_count = sum(
        1
        for event in upsert_ok_events
        if isinstance(event.get("summary_chars"), (int, float))
        and int(event.get("summary_chars", 0)) < 24
    )
    long_summary_count = sum(
        1
        for event in upsert_ok_events
        if isinstance(event.get("summary_chars"), (int, float))
        and int(event.get("summary_chars", 0)) > 320
    )
    missing_evidence_warning_count = sum(
        1
        for event in upsert_ok_events
        if isinstance(event.get("warning_codes"), list)
        and "missing_evidence" in {str(code) for code in event.get("warning_codes", [])}
    )

    tool_summary = []
    for name in sorted(tool_counts):
        durations = durations_by_tool.get(name, [])
        tool_summary.append(
            {
                "tool": name,
                "calls": int(tool_counts.get(name, 0)),
                "errors": int(tool_errors.get(name, 0)),
                "p95_duration_ms": _p95(durations),
            }
        )

    flags: list[str] = []
    if sessions_total and (ordered_sessions / sessions_total) < 0.8:
        flags.append(
            f"Task-start discipline sequence resolve->recent(strict)->search(soft) met in only "
            f"{ordered_sessions}/{sessions_total} sessions."
        )
    if sessions_total and (resolve_first_sessions / sessions_total) < 0.8:
        flags.append(
            f"muninn.spaces.resolve was first meaningful call in only "
            f"{resolve_first_sessions}/{sessions_total} sessions."
        )
    if total_matches_values:
        zero_rate = zero_match_count / max(1, len(total_matches_values))
        if zero_rate > 0.5:
            flags.append(
                f"High zero-match search rate ({zero_match_count}/{len(total_matches_values)})."
            )
    if top_scores:
        low_score_rate = low_top_score_count / max(1, len(top_scores))
        if low_score_rate > 0.4:
            flags.append(
                f"Many low-confidence search results (top_score<0.35 in {low_top_score_count}/{len(top_scores)})."
            )
    if sessions_upsert_over_3 > 0:
        flags.append(f"{sessions_upsert_over_3} sessions exceeded 3 successful upserts.")
    if rate_limit_hits_total > 0:
        flags.append(f"Write rate limiter hit {rate_limit_hits_total} times.")
    if missing_evidence_warning_count > 0:
        flags.append(
            f"{missing_evidence_warning_count} successful upserts were missing evidence."
        )
    search_p95 = _p95(search_durations)
    if search_p95 is not None and search_p95 > 500:
        flags.append(f"Search p95 latency is elevated at {search_p95:.0f}ms.")
    if short_queries > 0 and search_events:
        short_ratio = short_queries / max(1, len(search_events))
        if short_ratio > 0.4:
            flags.append(f"Many short search queries ({short_queries}/{len(search_events)}).")
    flags = flags[:5]

    recommendations: list[str] = []
    if sessions_total and ordered_sessions < sessions_total:
        recommendations.append(
            "AGENTS.md: require ordered task-start calls "
            "(muninn.spaces.resolve -> muninn.cards.recent strict -> muninn.cards.search soft)."
        )
    if sessions_upsert_over_3 > 0 or rate_limit_hits_total > 0:
        recommendations.append(
            "AGENTS.md: enforce 1-3 upserts per meaningful completion and prefer updates/supersedes."
        )
    if (total_matches_values and zero_match_count > 0) or short_queries > 0:
        recommendations.append(
            "AGENTS.md: shape search queries with concrete nouns (feature, file, invariant) before coding."
        )
    if missing_evidence_warning_count > 0:
        recommendations.append(
            "Require evidence refs for decision/constraint/interface/runbook cards or warn explicitly in review."
        )
    if not recommendations:
        recommendations.append("Keep current protocol and re-run audit after the next coding session.")
    recommendations = recommendations[:3]

    return {
        "source": source,
        "window": window,
        "events_analyzed": len(normalized),
        "sessions": sessions_total,
        "summary": {
            "tool_counts": tool_summary,
            "resolve_first_sessions": resolve_first_sessions,
            "ordered_start_sessions": ordered_sessions,
        },
        "discipline": {
            "sessions_total": sessions_total,
            "resolve_first_rate": (resolve_first_sessions / sessions_total) if sessions_total else None,
            "ordered_start_rate": (ordered_sessions / sessions_total) if sessions_total else None,
            "sessions_with_upserts": sessions_with_upserts,
            "sessions_upsert_1_3": sessions_upsert_1_3,
            "sessions_upsert_over_3": sessions_upsert_over_3,
        },
        "retrieval_quality": {
            "search_calls": len(search_events),
            "zero_match_count": zero_match_count,
            "total_matches_p95": _p95([float(v) for v in total_matches_values]),
            "top_score_p50": (sorted(top_scores)[len(top_scores) // 2] if top_scores else None),
            "low_top_score_count": low_top_score_count,
            "short_query_count": short_queries,
        },
        "write_hygiene": {
            "upsert_calls_ok": len(upsert_ok_events),
            "rate_limit_hits": rate_limit_hits_total,
            "short_summary_count": low_summary_count,
            "long_summary_count": long_summary_count,
            "missing_evidence_warning_count": missing_evidence_warning_count,
        },
        "performance": {
            "p95_duration_ms_by_tool": {
                item["tool"]: item["p95_duration_ms"] for item in tool_summary
            },
        },
        "top_problem_flags": flags,
        "recommendations": recommendations,
    }


def _print_audit_text(report: dict[str, Any]) -> None:
    print("Muninn audit report")
    print(
        f"source={report['source']} events={report['events_analyzed']} sessions={report['sessions']}"
    )
    print("Tool counts:")
    for row in report["summary"]["tool_counts"]:
        p95 = row["p95_duration_ms"]
        p95_text = f"{p95:.0f}" if isinstance(p95, (int, float)) else "n/a"
        print(
            f"- {row['tool']}: calls={row['calls']} errors={row['errors']} p95_ms={p95_text}"
        )
    discipline = report["discipline"]
    print("Discipline:")
    print(
        f"- ordered_start_rate={discipline['ordered_start_rate']} "
        f"resolve_first_rate={discipline['resolve_first_rate']}"
    )
    print(
        f"- sessions_upsert_1_3={discipline['sessions_upsert_1_3']} "
        f"sessions_upsert_over_3={discipline['sessions_upsert_over_3']}"
    )
    retrieval = report["retrieval_quality"]
    print("Retrieval quality:")
    print(
        f"- search_calls={retrieval['search_calls']} zero_match_count={retrieval['zero_match_count']} "
        f"low_top_score_count={retrieval['low_top_score_count']}"
    )
    write_hygiene = report["write_hygiene"]
    print("Write hygiene:")
    print(
        f"- upsert_calls_ok={write_hygiene['upsert_calls_ok']} "
        f"rate_limit_hits={write_hygiene['rate_limit_hits']} "
        f"missing_evidence_warning_count={write_hygiene['missing_evidence_warning_count']}"
    )
    print("Top problem flags:")
    if report["top_problem_flags"]:
        for idx, flag in enumerate(report["top_problem_flags"], start=1):
            print(f"{idx}. {flag}")
    else:
        print("1. No major issues detected in the selected window.")
    print("Suggested AGENTS.md tweaks:")
    for idx, rec in enumerate(report["recommendations"], start=1):
        print(f"{idx}. {rec}")


def _cmd_audit(args: argparse.Namespace) -> int:
    request_id = _new_cli_request_id()
    telemetry_path = Path(str(args.telemetry_path)).expanduser()
    limit = max(1, int(args.limit))
    since_epoch = _parse_since_epoch(args.since)
    if args.since and since_epoch is None:
        _emit_cli_command_event(
            "audit",
            request_id=request_id,
            status="error",
            error_text="invalid_since_format",
            telemetry_path=str(telemetry_path),
        )
        print("Invalid --since format. Example: --since '2026-02-19 15:00'", file=sys.stderr)
        return 1
    try:
        last_seconds = _parse_last_seconds(str(args.last))
    except ValueError:
        _emit_cli_command_event(
            "audit",
            request_id=request_id,
            status="error",
            error_text="invalid_last_format",
            telemetry_path=str(telemetry_path),
        )
        print("Invalid --last format. Use values like 30m, 2h, or 1d.", file=sys.stderr)
        return 1
    if since_epoch is None:
        since_epoch = time.time() - float(last_seconds)
    since_journal_arg = str(args.since).strip() if args.since else f"{last_seconds} seconds ago"

    source = "none"
    events: list[dict[str, Any]] = []
    if telemetry_path.exists():
        events = _load_events_from_jsonl(telemetry_path)
        source = "jsonl"
    else:
        journal_events, journal_error = _load_events_from_journal(args.unit, since_journal_arg)
        if journal_events:
            events = journal_events
            source = "journalctl"
        else:
            _emit_cli_command_event(
                "audit",
                request_id=request_id,
                status="error",
                telemetry_path=str(telemetry_path),
                unit=args.unit,
                error_text="no_telemetry_events_found",
            )
            print("No telemetry events found.", file=sys.stderr)
            print(
                "Set MUNINN_MCP_TELEMETRY_PATH to enable JSONL telemetry or run under systemd and retry.",
                file=sys.stderr,
            )
            if journal_error:
                print(f"journalctl detail: {journal_error}", file=sys.stderr)
            return 1

    filtered: list[dict[str, Any]] = []
    for event in events:
        ts = _event_timestamp(event)
        if since_epoch is not None and ts is not None and ts < since_epoch:
            continue
        filtered.append(event)
    if len(filtered) > limit:
        filtered = filtered[-limit:]
    if not filtered:
        _emit_cli_command_event(
            "audit",
            request_id=request_id,
            status="error",
            telemetry_path=str(telemetry_path),
            error_text="no_events_in_window",
        )
        print("No telemetry events in requested window.", file=sys.stderr)
        return 1

    report = _build_audit_report(
        filtered,
        source=source,
        window={
            "since_epoch": since_epoch,
            "since": args.since,
            "last": args.last,
            "limit": limit,
            "telemetry_path": str(telemetry_path),
            "unit": args.unit,
        },
    )
    if args.as_json:
        print(json.dumps(report))
    else:
        _print_audit_text(report)
    _emit_cli_command_event(
        "audit",
        request_id=request_id,
        status="ok",
        telemetry_path=str(telemetry_path),
        source=source,
        events_analyzed=int(report.get("events_analyzed") or 0),
        sessions=int(report.get("sessions") or 0),
    )
    return 0


def _cmd_heal(args: argparse.Namespace) -> int:
    request_id = _new_cli_request_id()
    db_path = Path(str(args.db_path)).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = human_memory_open_db(str(db_path))
    try:
        human_memory_apply_init_schema(conn, correlation_id=request_id)
        human_memory_bootstrap_defaults(conn, correlation_id=request_id)
        report = run_human_memory_heal(
            conn,
            user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
            space_key=(str(args.space_key).strip() if args.space_key else None),
            window_days=max(1, int(args.window_days)),
            apply=bool(args.apply),
            max_actions=max(0, int(args.max_actions)),
        )
    except Exception as exc:
        _emit_cli_command_event(
            "heal",
            request_id=request_id,
            status="error",
            db_target=str(db_path),
            error_text=str(exc),
        )
        print(f"heal failed: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    report["db_path"] = str(db_path)
    if args.as_json:
        print(json.dumps(report))
    else:
        print("Muninn heal report")
        print(
            f"scope={report['scope']} window_days={report['window_days']} "
            f"apply={str(report['apply_mode']).lower()}"
        )
        print(
            f"duplicates_by_fingerprint={len(report['duplicates_by_fingerprint'])} "
            f"duplicates_by_title={len(report['duplicates_by_title'])} "
            f"contradictions={len(report['contradictions'])} "
            f"stale_candidates={len(report['stale_candidates'])}"
        )
        print(f"actions_applied={report['actions_applied']}")
        if report["applied"]:
            for idx, action in enumerate(report["applied"], start=1):
                print(
                    f"{idx}. {action['action']} space={action['space_key']} "
                    f"reason={action['reason']} merged={action['merged_card_id']} "
                    f"superseded={len(action['superseded_card_ids'])}"
                )
        else:
            print("1. No merge actions applied in this run.")
    _emit_cli_command_event(
        "heal",
        request_id=request_id,
        status="ok",
        db_target=str(db_path),
        scope=str(report.get("scope")),
        actions_applied=int(report.get("actions_applied") or 0),
        duplicates_by_fingerprint=len(report.get("duplicates_by_fingerprint") or []),
        contradictions=len(report.get("contradictions") or []),
    )
    return 0


def _policy_kind_counts(cards: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for card in cards:
        kind = str(card.get("kind") or "")
        if not kind:
            continue
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _cmd_policy_list(args: argparse.Namespace) -> int:
    request_id = _new_cli_request_id()
    command_name = "policy.list"
    try:
        conn, db_path = _open_human_memory_conn_with_init(
            str(args.db_path),
            correlation_id=request_id,
        )
    except Exception as exc:
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="error",
            error_text=str(exc),
            db_target=str(Path(str(args.db_path)).expanduser()),
        )
        print(f"policy list failed: {exc}", file=sys.stderr)
        return 1
    try:
        resolved = _resolve_cli_policy_space(
            conn,
            cwd=args.cwd,
            space_key=args.space_key,
        )
        summary = resolved["space"]
        payload = human_memory_query_policy_cards(
            conn,
            user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
            space_key=str(summary["key"]),
            query=args.query,
            scope_types=args.scope_types,
            scope_key=args.scope_key,
            tool_name=args.tool_name,
            task_type=args.task_type,
            include_global=bool(args.include_global),
            limit=max(1, int(args.limit)),
            include_body=bool(args.include_body),
        )
        cards = list(payload.get("cards") or [])
        result = {
            "space": {
                "requested_space_key": resolved["requested_space_key"],
                "cwd": resolved["cwd"],
                "resolution_kind": resolved["resolution_kind"],
                "key": summary["key"],
                "label": summary["label"],
                "lookup_keys": summary["lookup_keys"],
            },
            "cards": cards,
            "counts": {
                "total": len(cards),
                "by_kind": _policy_kind_counts(cards),
            },
            "filters": payload.get("filters") or {},
            "diagnostics": payload.get("diagnostics") or {},
            "db_path": str(db_path),
        }
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="ok",
            target_space=str(summary["key"]),
            result_count=len(cards),
            by_kind=result["counts"]["by_kind"],
            invalid_policy_rows=int((result["diagnostics"].get("invalid_policy_rows") or 0)),
            db_target=str(db_path),
        )
        if args.as_json:
            print(json.dumps(result))
        else:
            print("Muninn policy cards")
            print(
                f"space={summary['key']} label={summary['label']} "
                f"lookup_keys={len(summary['lookup_keys'])} total={len(cards)}"
            )
            if result["counts"]["by_kind"]:
                by_kind = " ".join(f"{kind}={count}" for kind, count in result["counts"]["by_kind"].items())
                print(f"by_kind {by_kind}")
            invalid_rows = int((result["diagnostics"].get("invalid_policy_rows") or 0))
            if invalid_rows > 0:
                print(f"invalid_policy_rows={invalid_rows}")
            if cards:
                for idx, card in enumerate(cards, start=1):
                    policy = card.get("policy") or {}
                    scope = policy.get("scope") or {}
                    print(
                        f"{idx}. {card['id']} {card['kind']} score={card.get('score')} "
                        f"scope={scope.get('type')}:{scope.get('key') or '*'}"
                    )
                    print(
                        f"   title={card.get('title')} confidence={policy.get('confidence')} "
                        f"repetition={policy.get('repetition_count')} updated_at={card.get('updated_at')}"
                    )
            else:
                print("1. No policy cards matched the selected filters.")
        return 0
    finally:
        conn.close()


def _cmd_policy_show(args: argparse.Namespace) -> int:
    request_id = _new_cli_request_id()
    command_name = "policy.show"
    try:
        conn, db_path = _open_human_memory_conn_with_init(
            str(args.db_path),
            correlation_id=request_id,
        )
    except Exception as exc:
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="error",
            error_text=str(exc),
            db_target=str(Path(str(args.db_path)).expanduser()),
        )
        print(f"policy show failed: {exc}", file=sys.stderr)
        return 1
    try:
        card = _load_policy_card_by_id(conn, card_id=str(args.card_id).strip())
        if card is None:
            _emit_cli_command_event(
                command_name,
                request_id=request_id,
                status="error",
                card_id=str(args.card_id).strip(),
                error_text="policy_card_not_found",
                db_target=str(db_path),
            )
            print("Policy card not found.", file=sys.stderr)
            return 1
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="ok",
            card_id=str(card["id"]),
            target_space=str(card["space_key"]),
            db_target=str(db_path),
        )
        if args.as_json:
            print(json.dumps(card))
        else:
            policy = card.get("policy") or {}
            scope = policy.get("scope") or {}
            print("Muninn policy card")
            print(f"id={card['id']} kind={card['kind']} space={card['space_key']}")
            print(
                f"scope={scope.get('type')}:{scope.get('key') or '*'} "
                f"confidence={policy.get('confidence')} repetition={policy.get('repetition_count')}"
            )
            print(f"title={card.get('title')}")
            print(f"summary={card.get('summary')}")
            if card.get("body"):
                print("body:")
                print(str(card["body"]))
        return 0
    finally:
        conn.close()


def _cmd_policy_events(args: argparse.Namespace) -> int:
    request_id = _new_cli_request_id()
    command_name = "policy.events"
    try:
        conn, db_path = _open_human_memory_conn_with_init(
            str(args.db_path),
            correlation_id=request_id,
        )
    except Exception as exc:
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="error",
            error_text=str(exc),
            db_target=str(Path(str(args.db_path)).expanduser()),
        )
        print(f"policy events failed: {exc}", file=sys.stderr)
        return 1
    try:
        resolved = _resolve_cli_policy_space(
            conn,
            cwd=args.cwd,
            space_key=args.space_key,
        )
        summary = resolved["space"]
        event_types = list(args.event_types or ["policy_signal"])
        events = human_memory_list_interaction_events(
            conn,
            user_id=HUMAN_MEMORY_DEFAULT_USER_ID,
            space_key=str(summary["key"]),
            limit=max(1, int(args.limit)),
            session_id=args.session_id,
            event_types=event_types,
            promotion_state=args.promoted,
        )
        promoted_count = sum(1 for event in events if event.get("promoted_card_id"))
        result = {
            "space": {
                "requested_space_key": resolved["requested_space_key"],
                "cwd": resolved["cwd"],
                "resolution_kind": resolved["resolution_kind"],
                "key": summary["key"],
                "label": summary["label"],
                "lookup_keys": summary["lookup_keys"],
            },
            "events": events,
            "counts": {
                "total": len(events),
                "promoted": promoted_count,
                "unpromoted": len(events) - promoted_count,
            },
            "filters": {
                "session_id": args.session_id,
                "event_types": event_types,
                "promoted": args.promoted,
                "limit": max(1, int(args.limit)),
            },
            "db_path": str(db_path),
        }
        _emit_cli_command_event(
            command_name,
            request_id=request_id,
            status="ok",
            target_space=str(summary["key"]),
            result_count=len(events),
            promoted=promoted_count,
            unpromoted=len(events) - promoted_count,
            db_target=str(db_path),
        )
        if args.as_json:
            print(json.dumps(result))
        else:
            print("Muninn policy interaction events")
            print(
                f"space={summary['key']} total={len(events)} promoted={promoted_count} "
                f"unpromoted={len(events) - promoted_count}"
            )
            if events:
                for idx, event in enumerate(events, start=1):
                    promoted = "yes" if event.get("promoted_card_id") else "no"
                    print(
                        f"{idx}. {event['id']} type={event['event_type']} actor={event['actor']} "
                        f"promoted={promoted} created_at={event['created_at']}"
                    )
                    print(
                        f"   signal={event.get('signal_type')} outcome={event.get('outcome_type')} "
                        f"scope={event.get('scope_type')}:{event.get('scope_key') or '*'}"
                    )
                    print(f"   summary={event.get('summary')}")
            else:
                print("1. No interaction events matched the selected filters.")
        return 0
    finally:
        conn.close()


def _check_python_version() -> tuple[bool, str, str]:
    min_major = 3
    min_minor = 11
    requires_raw = ">=3.11"
    pyproject = _repo_root() / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomllib

            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            requires_raw = str(data.get("project", {}).get("requires-python", requires_raw))
            if requires_raw.startswith(">="):
                version_str = requires_raw.replace(">=", "").strip()
                parts = version_str.split(".")
                min_major = int(parts[0])
                min_minor = int(parts[1]) if len(parts) > 1 else 0
        except Exception:
            pass

    current = sys.version_info
    ok = (current.major, current.minor) >= (min_major, min_minor)
    detail = f"Python {current.major}.{current.minor}.{current.micro} (requires {requires_raw})"
    fix = f"Use Python {min_major}.{min_minor}+ for Muninn" if not ok else ""
    return ok, detail, fix


def _check_imports() -> tuple[bool, str, str]:
    deps = ["fastapi", "uvicorn", "pydantic", "httpx"]
    missing: list[str] = []
    for dep in deps:
        try:
            importlib.import_module(dep)
        except Exception:
            missing.append(dep)
    if missing:
        return False, f"Missing imports: {', '.join(missing)}", "Install deps with: pip install -e ."
    return True, "Required imports available", ""


def _check_port(host: str, port: int, base_url: str) -> tuple[bool, str, str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True, f"Port {port} on {host} is free", ""
    except OSError:
        health_url = base_url.rstrip("/") + "/health"
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200:
                return True, f"Port {port} in use by running service at {health_url}", ""
        except Exception:
            pass
        return False, f"Port {port} on {host} is in use", f"Free port {port} or set MUNINN_PORT"
    finally:
        sock.close()


def _check_db_path_writable(db_path: str) -> tuple[bool, str, str]:
    target = Path(db_path).expanduser()
    parent = target.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        created = False
        if target.exists():
            with open(target, "a", encoding="utf-8"):
                pass
        else:
            target.touch()
            created = True
        if created:
            target.unlink()
        return True, f"DB path writable: {target}", ""
    except Exception as exc:
        return False, f"DB path not writable: {target} ({exc})", "Set writable MUNINN_DB_PATH"


def _check_schema(db_path: str) -> tuple[bool, str, str]:
    conn = None
    try:
        conn = db.connect()
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name IN ('schema_migrations', 'entities', 'facts', 'episodes', 'preferences')
            """
        ).fetchall()
    except Exception as exc:
        return False, f"Schema check failed: {exc}", "Run: muninn up"
    finally:
        if conn is not None:
            conn.close()

    names = {str(row["name"]) for row in rows}
    required = {"schema_migrations", "entities", "facts", "episodes", "preferences"}
    missing = sorted(required - names)
    if missing:
        return False, f"Missing schema objects: {', '.join(missing)}", "Run: muninn up"
    return True, "Core schema objects exist", ""


def _check_vector_backend() -> tuple[bool, str, str]:
    try:
        backend_config, sqlite_loaded, effective = vector_store.effective_backend()
        detail = (
            f"Vector backend config={backend_config} effective={effective} sqlite_vec_loaded={sqlite_loaded}"
        )
        return True, detail, ""
    except Exception as exc:
        return False, f"Vector backend check failed: {exc}", "Check vector config/env flags"


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = _resolve_runtime_config(args)
    host = str(config["host"])
    port = int(config["port"])
    db_path = str(config["db_path"])
    base_url = args.base_url or f"http://{host}:{port}"

    checks: list[tuple[str, bool, str, str]] = []
    checks.append(("python_version", *_check_python_version()))
    checks.append(("imports", *_check_imports()))
    checks.append(("port", *_check_port(host, port, base_url)))
    checks.append(("db_path", *_check_db_path_writable(db_path)))
    checks.append(("schema", *_check_schema(db_path)))
    checks.append(("vector_backend", *_check_vector_backend()))

    any_fail = False
    print("Muninn doctor")
    for name, ok, detail, fix in checks:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}: {detail}")
        if not ok:
            any_fail = True
            if fix:
                print(f"  fix: {fix}")

    return 1 if any_fail else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "up":
        return _cmd_up(args)

    if args.command == "doctor":
        return _cmd_doctor(args)

    if args.command == "mcp":
        if args.mcp_command == "up":
            return _cmd_mcp_up(args)
        if args.mcp_command == "stdio":
            return _cmd_mcp_stdio(args)
        parser.print_help()
        return 1

    if args.command == "enable-chatgpt":
        return _cmd_enable_chatgpt(args)

    if args.command == "status":
        return _cmd_status(args.base_url, args.mcp_url, args.timeout)
    if args.command == "audit":
        return _cmd_audit(args)
    if args.command == "heal":
        return _cmd_heal(args)
    if args.command == "policy":
        if args.policy_command == "list":
            return _cmd_policy_list(args)
        if args.policy_command == "show":
            return _cmd_policy_show(args)
        if args.policy_command == "events":
            return _cmd_policy_events(args)
        parser.print_help()
        return 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

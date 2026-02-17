from __future__ import annotations

import argparse
import importlib
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from . import __version__, db
from .config import config_dir, data_dir, db_path, readonly, settings
from .migrations import apply_migrations
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
    from .mcp_server import run_mcp_server

    host = args.host or "127.0.0.1"
    port = int(args.port or 8765)
    base_url = args.base_url or os.getenv("MUNINN_BASE_URL", "http://127.0.0.1:8000")
    run_mcp_server(host=host, port=port, base_url=base_url)
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
    print(f"Start tunnel to http://127.0.0.1:{mcp_port}")
    print("Use resulting https://.../mcp in ChatGPT -> Settings -> Connectors")
    print(f"Add header {header_name}: <key>")
    print("Note: ChatGPT connector requires HTTPS.")
    return 0


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
    status.add_argument("--timeout", type=float, default=5.0, help="Request timeout seconds")

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

    mcp_up = mcp_sub.add_parser("up", help="Start local MCP server (streamable HTTP)")
    mcp_up.add_argument("--host", default="127.0.0.1", help="MCP bind host")
    mcp_up.add_argument("--port", type=int, default=8765, help="MCP bind port")
    mcp_up.add_argument(
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

    return parser


def _cmd_status(base_url: str, timeout: float) -> int:
    health_url = base_url.rstrip("/") + "/health"
    try:
        response = httpx.get(health_url, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "version": __version__,
                    "base_url": base_url,
                    "error": str(exc),
                }
            )
        )
        return 1

    print(
        json.dumps(
            {
                "ok": bool(payload.get("ok", False)),
                "version": __version__,
                "base_url": base_url,
                "health": payload,
            }
        )
    )
    return 0


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
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name IN ('schema_migrations', 'entities', 'facts', 'episodes', 'preferences')
            """
        ).fetchall()
        conn.close()
    except Exception as exc:
        return False, f"Schema check failed: {exc}", "Run: muninn up"

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
        parser.print_help()
        return 1

    if args.command == "enable-chatgpt":
        return _cmd_enable_chatgpt(args)

    if args.command == "status":
        return _cmd_status(args.base_url, args.timeout)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

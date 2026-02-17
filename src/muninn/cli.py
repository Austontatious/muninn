from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import sqlite3
import sys
from pathlib import Path
from typing import Any

import httpx
import uvicorn

from . import __version__, db
from .config import readonly, settings
from .migrations import apply_migrations
from .vector import store as vector_store


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_runtime_config(args: argparse.Namespace) -> dict[str, Any]:
    host = args.host or os.getenv("MUNINN_HOST", settings.host)
    port = int(args.port or int(os.getenv("MUNINN_PORT", str(settings.port))))
    db_path = args.db_path or os.getenv("MUNINN_DB_PATH", settings.db_path)
    namespace_default = os.getenv("MUNINN_NAMESPACE", "default")
    if db_path:
        os.environ["MUNINN_DB_PATH"] = db_path
    return {
        "host": host,
        "port": port,
        "db_path": db_path,
        "namespace_default": namespace_default,
        "readonly": readonly(),
    }


def _ensure_db_dir(db_path: str) -> None:
    db_parent = Path(db_path).expanduser().resolve().parent
    db_parent.mkdir(parents=True, exist_ok=True)


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


def _print_up_banner(config: dict[str, Any]) -> None:
    base_url = f"http://{config['host']}:{config['port']}"
    print("Muninn up")
    print(f"  Base URL: {base_url}")
    print(f"  DB path: {config['db_path']}")
    print(f"  Readonly: {config['readonly']}")
    print(f"  Namespace default: {config['namespace_default']}")


def _cmd_up(args: argparse.Namespace) -> int:
    config = _resolve_runtime_config(args)
    _ensure_db_dir(str(config["db_path"]))
    _init_schema_and_migrations()
    _print_up_banner(config)

    uvicorn.run(
        "muninn.api:app",
        host=str(config["host"]),
        port=int(config["port"]),
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

    if args.command == "status":
        return _cmd_status(args.base_url, args.timeout)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx

from . import __version__


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


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "status":
        return _cmd_status(args.base_url, args.timeout)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

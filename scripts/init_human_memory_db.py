from __future__ import annotations

import argparse
from pathlib import Path

from muninn.human_memory.bootstrap import apply_init_schema, bootstrap_defaults, open_db


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize Muninn human-memory v1 schema and bootstrap defaults.",
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Path to SQLite DB file.",
    )
    parser.add_argument(
        "--schema",
        default=None,
        help="Optional path to SQL schema (defaults to migrations/0001_init.sql).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    db_path = Path(args.db).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = open_db(str(db_path))
    apply_init_schema(conn, schema_path=args.schema)
    bootstrap_defaults(conn)
    conn.close()
    print(f"Initialized human-memory schema at {db_path}")


if __name__ == "__main__":
    main()

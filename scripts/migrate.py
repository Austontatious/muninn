#!/usr/bin/env python3
from __future__ import annotations

from muninn import db
from muninn.migrations import apply_migrations


def main() -> None:
    conn = db.connect()
    applied = apply_migrations(conn)
    if applied:
        print("Applied migrations:")
        for migration_id in applied:
            print(f"- {migration_id}")
    else:
        print("No migrations applied")


if __name__ == "__main__":
    main()

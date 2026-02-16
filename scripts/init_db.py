import sqlite3

from muninn import db
from muninn.migrations import apply_migrations


def backfill_fts(conn) -> None:
    # Facts
    conn.execute("DELETE FROM facts_fts")
    conn.execute(
        """
        INSERT INTO facts_fts(id, subject_id, text)
        SELECT id, subject_id, predicate || ': ' || object FROM facts
        """
    )
    # Episodes
    conn.execute("DELETE FROM episodes_fts")
    conn.execute(
        """
        INSERT INTO episodes_fts(id, entity_id, summary)
        SELECT id, entity_id, summary FROM episodes
        """
    )
    # Preferences
    conn.execute("DELETE FROM preferences_fts")
    conn.execute(
        """
        INSERT INTO preferences_fts(id, entity_id, text)
        SELECT id, entity_id, key || '=' || value FROM preferences
        """
    )
    conn.commit()


def main() -> None:
    conn = db.connect()
    try:
        db.init_db(conn)
    except sqlite3.OperationalError as exc:
        # Existing pre-v0.5 DBs may fail schema apply before namespace migration.
        if "no such column: namespace" not in str(exc).lower():
            raise
        conn.rollback()
    applied = apply_migrations(conn)
    db.init_db(conn)
    backfill_fts(conn)
    # Embeddings and sqlite-vec index rows are caller-provided and written via API.
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    print("Initialized DB")


if __name__ == "__main__":
    main()

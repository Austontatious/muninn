from muninn import db


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
    db.init_db(conn)
    backfill_fts(conn)
    print("Initialized DB")


if __name__ == "__main__":
    main()

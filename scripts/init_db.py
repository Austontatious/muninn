from muninn import db


def main() -> None:
    conn = db.connect()
    db.init_db(conn)
    print("Initialized DB")


if __name__ == "__main__":
    main()

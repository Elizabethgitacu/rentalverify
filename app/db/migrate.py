from __future__ import annotations

from app.storage import SQLITE_PATH, init_db


def main() -> None:
    init_db()
    print(f"SQLite database ready: {SQLITE_PATH.resolve()}")


if __name__ == "__main__":
    main()

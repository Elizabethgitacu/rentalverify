from __future__ import annotations

import os
from pathlib import Path

import psycopg


BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def ensure_database_url() -> str:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set.")
    return DATABASE_URL


def main() -> None:
    url = ensure_database_url()
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not files:
        print("No migration files found.")
        return

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute("SELECT filename FROM schema_migrations")
            applied = {row[0] for row in cur.fetchall()}

            for file_path in files:
                if file_path.name in applied:
                    print(f"Skipping {file_path.name}")
                    continue

                sql = file_path.read_text(encoding="utf-8")
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (file_path.name,),
                )
                conn.commit()
                print(f"Applied {file_path.name}")


if __name__ == "__main__":
    main()


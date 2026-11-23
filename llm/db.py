import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "newsradar"),
        user=os.getenv("DB_USER", "newsradar"),
        password=os.getenv("DB_PASSWORD"),
    )


if __name__ == "__main__":
    with get_connection() as conn:
        version = conn.execute("SELECT version()").fetchone()[0]
        tables = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        ).fetchall()
    print("Connected to:", version)
    print("Tables:", [t[0] for t in tables])
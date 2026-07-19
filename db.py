"""SQLite connection and schema initialization for Coach."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "coach.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    # timeout: how long to wait on a locked db before raising, instead of the
    # sqlite3 default of 5s -- multiple MCP server processes (this agent's own
    # session, Desktop's chat session, etc.) can genuinely hit this file at
    # the same time now.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL: readers don't block on a writer (and vice versa), unlike the
    # default rollback-journal mode -- the right mode once more than one
    # process opens this file concurrently, which is now the normal case.
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")

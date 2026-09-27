# db/connection.py — shared SQLite connection helper

import sqlite3
import pathlib
from config import DB_PATH

def get_conn() -> sqlite3.Connection:
    """Return a WAL-mode SQLite connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db() -> None:
    """Run schema.sql and views.sql against the configured database."""
    base = pathlib.Path(__file__).parent
    conn = get_conn()
    with conn:
        conn.executescript((base / "schema.sql").read_text())
        conn.executescript((base / "views.sql").read_text())
    conn.close()
    print(f"Database initialised at: {DB_PATH}")

"""
database.py
-----------
Small SQLite helper for CarbonSense.

Responsibilities:
  * Resolve the path to database/database.db (sibling folder to backend/)
  * Create the schema on first run (users, activities, goals)
  * Provide a get_db() connection factory used by app.py

Kept as plain sqlite3 (no ORM) on purpose — this is a small
project-scale app, and a raw schema is easier to inspect directly
with the `sqlite3` CLI for the assignment's testing/verification
section (e.g. `sqlite3 database/database.db ".tables"`).
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
DB_PATH = os.path.join(DB_DIR, "database.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    category    TEXT NOT NULL CHECK (category IN ('travel','electricity','food','waste')),
    mode        TEXT,
    distance    REAL,
    units       REAL,
    meal_type   TEXT,
    meals       REAL,
    waste_type  TEXT,
    weight      REAL,
    co2         REAL NOT NULL,
    date        TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE,
    target_kg   REAL NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users (id)
);
"""


def ensure_db_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def get_db():
    """Return a new SQLite connection with row access by column name."""
    ensure_db_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they do not exist yet. Safe to call on every startup."""
    ensure_db_dir()
    conn = get_db()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # Allows: python database.py  ->  initialise the DB file standalone
    init_db()
    print(f"Database ready at {os.path.abspath(DB_PATH)}")

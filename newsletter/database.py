"""SQLite database setup for the newsletter app."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.environ.get(
    "NEWSLETTER_DB",
    str(Path(__file__).resolve().parent / "data" / "newsletter.db"),
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS newsletters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    preheader TEXT NOT NULL DEFAULT '',
    blocks TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    list_id INTEGER,
    created_at TEXT NOT NULL,
    UNIQUE(email, list_id),
    FOREIGN KEY(list_id) REFERENCES lists(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    newsletter_id INTEGER NOT NULL,
    list_id INTEGER,
    total INTEGER NOT NULL DEFAULT 0,
    success INTEGER NOT NULL DEFAULT 0,
    failed INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY(newsletter_id) REFERENCES newsletters(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS campaign_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    sent_at TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_recipients_list ON recipients(list_id);
CREATE INDEX IF NOT EXISTS idx_logs_campaign ON campaign_logs(campaign_id);
"""


def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

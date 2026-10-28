"""SQLite history so each run can flag listings it hasn't seen before."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import Listing

SCHEMA = """
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    url TEXT NOT NULL,
    source TEXT,
    location TEXT,
    deadline TEXT,
    description TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
)
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def record(self, listings: list[Listing], now: str | None = None) -> None:
        """Upsert listings and set `first_seen` / `is_new` on each."""
        now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.conn:
            for l in listings:
                row = self.conn.execute(
                    "SELECT first_seen FROM listings WHERE id = ?", (l.id,)
                ).fetchone()
                l.first_seen = row[0] if row else now
                l.is_new = row is None
                self.conn.execute(
                    """INSERT INTO listings VALUES (?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         title=excluded.title, company=excluded.company,
                         location=excluded.location, deadline=excluded.deadline,
                         description=excluded.description, last_seen=excluded.last_seen""",
                    (l.id, l.title, l.company, l.url, l.source, l.location,
                     l.deadline, l.description, l.first_seen, now),
                )

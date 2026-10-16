from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT NOT NULL, event TEXT NOT NULL, person_id TEXT, name TEXT, score REAL, detail TEXT)")

    def record(self, event: str, person_id: str = "", name: str = "", score: float | None = None, detail: str = "") -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO events(at,event,person_id,name,score,detail) VALUES(?,?,?,?,?,?)", (datetime.now(timezone.utc).isoformat(), event, person_id, name, score, detail))

    def recent(self, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(row) for row in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]

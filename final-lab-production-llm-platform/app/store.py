from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class AuditStore:
    """Durable, redacted state and idempotency claims for the bounded agent."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    tool_call_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    idempotency_key TEXT PRIMARY KEY,
                    created_at REAL NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path)
        db.execute("PRAGMA journal_mode=WAL")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def claim_idempotency(self, key: str) -> bool:
        try:
            with self._connect() as db:
                db.execute("INSERT INTO idempotency_keys VALUES (?, ?)", (key, time.time()))
            return True
        except sqlite3.IntegrityError:
            return False

    def append_event(self, task_id: str, tool_call_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        # Callers may send only bounded metadata here; never persist raw tool output.
        with self._connect() as db:
            db.execute(
                "INSERT INTO agent_events(task_id, tool_call_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (task_id, tool_call_id, event_type, json.dumps(payload, ensure_ascii=False), time.time()),
            )

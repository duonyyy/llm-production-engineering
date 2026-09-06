"""Durable, local execution state for the Lab 03 agent.

State is intentionally separate from the prompt/context window. The event log
is the audit trail; the context assembled for one LLM call is disposable.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class SessionStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                status TEXT NOT NULL,
                state_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                session_id TEXT NOT NULL,
                key TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY(session_id, key)
            );
            """
        )
        self.db.commit()

    def load_state(self, session_id: str) -> dict[str, Any]:
        row = self.db.execute("SELECT state_json FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            now = time.time()
            state = {"session_id": session_id, "completed_steps": [], "short_term_memory": [], "audit": []}
            self.db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (session_id, now, now, "active", json.dumps(state)))
            self.db.commit()
            return state
        return json.loads(row[0])

    def save_state(self, session_id: str, state: dict[str, Any], status: str = "active") -> None:
        now = time.time()
        self.db.execute("UPDATE sessions SET updated_at = ?, status = ?, state_json = ? WHERE session_id = ?", (now, status, json.dumps(state, ensure_ascii=False), session_id))
        self.db.commit()

    def append_event(self, session_id: str, task_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO events(session_id, task_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)", (session_id, task_id, event_type, json.dumps(payload, ensure_ascii=False), time.time()))
        self.db.commit()

    def claim_idempotency(self, session_id: str, key: str) -> bool:
        try:
            self.db.execute("INSERT INTO idempotency_keys VALUES (?, ?, ?)", (session_id, key, time.time()))
            self.db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def close(self) -> None:
        self.db.close()

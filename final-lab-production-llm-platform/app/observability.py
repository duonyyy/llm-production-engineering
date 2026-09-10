from __future__ import annotations

import json
import logging
import time
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from prometheus_client import Counter, Histogram


REQUESTS = Counter(
    "final_lab_requests_total",
    "Terminal Final Lab requests without sensitive labels.",
    ("route", "terminal_status", "execution_mode"),
)
LATENCY = Histogram(
    "final_lab_request_e2e_seconds",
    "End-to-end gateway latency.",
    ("route", "terminal_status", "execution_mode"),
)
RETRIEVAL = Histogram("final_lab_retrieval_seconds", "FAISS retrieval latency.", ("terminal_status",))
TOOL_EVENTS = Counter("final_lab_agent_tool_events_total", "Bounded agent tool events.", ("tool", "disposition"))


class SafeEventLog:
    """JSON logger whose call site receives only correlation metadata."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("final_lab")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        handler = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)

    def emit(self, event: str, **metadata: Any) -> None:
        prohibited = {"prompt", "messages", "content", "authorization", "token", "tool_payload", "document"}
        safe = {key: value for key, value in metadata.items() if key.lower() not in prohibited}
        self.logger.info(json.dumps({"observed_at": time.time(), "event": event, **safe}, ensure_ascii=False))

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            handler.close()
            self.logger.removeHandler(handler)


class RecentMetrics:
    """Small in-memory, aggregate-only view for the read-only MCP endpoint."""

    def __init__(self) -> None:
        self.items: deque[dict[str, Any]] = deque(maxlen=200)

    def add(self, route: str, terminal_status: str, elapsed_ms: float) -> None:
        self.items.append({"at": time.time(), "route": route, "terminal_status": terminal_status, "e2e_ms": round(elapsed_ms, 3)})

    def summary(self, window_minutes: int) -> dict[str, Any]:
        cutoff = time.time() - window_minutes * 60
        selected = [item for item in self.items if item["at"] >= cutoff]
        completed = sum(item["terminal_status"] == "completed" for item in selected)
        return {"sample_count": len(selected), "completed_count": completed, "error_count": len(selected) - completed, "window_minutes": window_minutes}

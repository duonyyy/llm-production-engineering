"""Stdlib-only benchmark helpers with explicit NA semantics."""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} is not an object")
        rows.append(value)
    return rows


def _usage_from_event(event: Any) -> dict[str, Any] | None:
    if not isinstance(event, dict):
        return None
    usage = event.get("usage")
    if isinstance(usage, dict):
        return usage
    return None


def request_stream(url: str, payload: dict[str, Any], timeout: float = 60.0, headers: dict[str, str] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, method="POST", headers=request_headers)
    started = time.perf_counter()
    first_event_s: float | None = None
    events: list[Any] = []
    response_headers: dict[str, str] = {}
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_headers = {key.lower(): value for key, value in response.headers.items()}
            content_type = response_headers.get("content-type", "")
            if "text/event-stream" in content_type:
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        continue
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    events.append(event)
                    if first_event_s is None:
                        first_event_s = time.perf_counter()
            else:
                raw = response.read()
                events.append(json.loads(raw.decode("utf-8")))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {"status": "ERROR", "error": str(exc), "ttft_ms": "NA", "e2e_ms": "NA"}

    ended = time.perf_counter()
    usage = next((value for value in reversed(events) if _usage_from_event(value)), None)
    usage = _usage_from_event(usage) if usage else None
    token_status = "api_usage" if usage and usage.get("completion_tokens") is not None else "unavailable"
    completion_tokens = usage.get("completion_tokens") if usage else "NA"
    prompt_tokens = usage.get("prompt_tokens") if usage else "NA"
    cached_tokens = "NA"
    if usage:
        details = usage.get("prompt_tokens_details")
        if isinstance(details, dict) and details.get("cached_tokens") is not None:
            cached_tokens = details["cached_tokens"]
    ttft_ms = (first_event_s - started) * 1000 if first_event_s is not None else (ended - started) * 1000
    e2e_ms = (ended - started) * 1000
    tpot_ms = "NA"
    if isinstance(completion_tokens, int) and completion_tokens > 1 and first_event_s is not None:
        tpot_ms = ((ended - first_event_s) * 1000) / (completion_tokens - 1)
    return {
        "status": "OK",
        "ttft_ms": round(ttft_ms, 3),
        "e2e_ms": round(e2e_ms, 3),
        "tpot_ms": round(tpot_ms, 3) if isinstance(tpot_ms, float) else tpot_ms,
        "completion_tokens": completion_tokens,
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "token_metric_status": token_status,
        "response_headers": response_headers,
        "events": events,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("status\nNO_ROWS\n", encoding="utf-8")
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)

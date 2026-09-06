#!/usr/bin/env python3
"""Small dependency-free streaming client for the Lab 02 OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


NA = "NA"
FIELDS = [
    "request_id",
    "workload_id",
    "backend",
    "started_at",
    "ended_at",
    "prompt_chars",
    "prompt_tokens",
    "completion_tokens",
    "ttft_s",
    "e2e_latency_s",
    "status",
    "http_status",
    "stream_complete",
    "finish_reason",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="OpenAI-compatible /v1/chat/completions URL")
    parser.add_argument("--model", required=True)
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--requests", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--backend-label", default=NA)
    return parser.parse_args()


def load_workload(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(item, dict) or "messages" not in item:
                raise ValueError(f"Each workload row needs an object with messages: {path}:{line_number}")
            if not isinstance(item["messages"], list) or not item["messages"]:
                raise ValueError(f"messages must be a non-empty list: {path}:{line_number}")
            items.append(item)
    if not items:
        raise ValueError(f"Workload is empty: {path}")
    return items


def numeric(value: Any) -> str | float | int:
    if value is None:
        return NA
    if isinstance(value, bool):
        return NA
    if isinstance(value, (int, float)):
        return value
    return NA


def parse_sse_line(line: str) -> dict[str, Any] | None:
    if not line.startswith("data:"):
        return None
    data = line[5:].strip()
    if not data or data == "[DONE]":
        return {"_done": data == "[DONE]"}
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_text_delta(event: dict[str, Any]) -> str:
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        return ""
    delta = choice.get("delta")
    if isinstance(delta, dict) and isinstance(delta.get("content"), str):
        return delta["content"]
    return ""


def run_request(args: argparse.Namespace, item: dict[str, Any], index: int) -> dict[str, Any]:
    request_id = f"req-{index:05d}-{uuid.uuid4().hex[:8]}"
    messages = item["messages"]
    prompt_chars = sum(len(str(message.get("content", ""))) for message in messages if isinstance(message, dict))
    payload = {
        "model": args.model,
        "messages": messages,
        "max_tokens": args.max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    started = time.time()
    first_token_at: float | None = None
    usage: dict[str, Any] = {}
    finish_reason: Any = None
    stream_complete = False
    http_status: int | str = NA
    backend = args.backend_label
    error = ""
    status = "error"

    try:
        request = Request(
            args.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
            method="POST",
        )
        with urlopen(request, timeout=args.timeout) as response:
            http_status = response.status
            backend = response.headers.get("x-backend") or response.headers.get("x-served-by") or backend
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                event = parse_sse_line(line)
                if event is None:
                    continue
                if event.get("_done"):
                    stream_complete = True
                    continue
                if first_token_at is None and extract_text_delta(event):
                    first_token_at = time.time()
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices")
                if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                    finish_reason = choices[0].get("finish_reason") or finish_reason
            ended = time.time()
            status = "ok" if stream_complete else "incomplete"
    except HTTPError as exc:
        ended = time.time()
        http_status = exc.code
        error = exc.read().decode("utf-8", errors="replace")[:500]
    except (URLError, TimeoutError, OSError) as exc:
        ended = time.time()
        error = str(exc)[:500]
    except Exception as exc:  # keep one failed request from hiding the rest of the raw run
        ended = time.time()
        error = f"{type(exc).__name__}: {exc}"[:500]

    prompt_tokens = usage.get("prompt_tokens", usage.get("prompt_token_ids"))
    completion_tokens = usage.get("completion_tokens")
    return {
        "request_id": request_id,
        "workload_id": item.get("id", NA),
        "backend": backend or NA,
        "started_at": f"{started:.6f}",
        "ended_at": f"{ended:.6f}",
        "prompt_chars": prompt_chars,
        "prompt_tokens": numeric(prompt_tokens),
        "completion_tokens": numeric(completion_tokens),
        "ttft_s": f"{(first_token_at - started):.6f}" if first_token_at else NA,
        "e2e_latency_s": f"{(ended - started):.6f}",
        "status": status,
        "http_status": http_status,
        "stream_complete": str(stream_complete).lower(),
        "finish_reason": finish_reason or NA,
        "error": error,
    }


def write_output(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    if args.concurrency < 1 or args.requests < 1 or args.max_tokens < 1:
        raise SystemExit("--concurrency, --requests and --max-tokens must be positive")
    workload = load_workload(args.input_file)
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(run_request, args, workload[index % len(workload)], index + 1) for index in range(args.requests)]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: row["request_id"])
    write_output(args.output, rows)
    ok = sum(row["status"] == "ok" for row in rows)
    print(json.dumps({"output": str(args.output), "requests": len(rows), "ok": ok, "failed_or_incomplete": len(rows) - ok}))
    return 0 if ok == len(rows) else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"load_generator error: {exc}", file=sys.stderr)
        raise SystemExit(1)

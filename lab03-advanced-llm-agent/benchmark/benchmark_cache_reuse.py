"""Measure repeated-prefix requests when the serving API exposes usage data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_jsonl, request_stream, write_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "live", "design"], default="auto")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--dataset", default=str(Path(__file__).parents[1] / "datasets" / "repeated_prefix.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).parents[1] / "results" / "cache_reuse_raw.csv"))
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    records = load_jsonl(Path(args.dataset))
    if args.mode == "design":
        write_csv(Path(args.output), [{"status": "DESIGN_ONLY", "reason": "Cache hits are not inferred from prompt similarity."}])
        return
    rows = []
    for record in records:
        payload = {
            "model": record.get("model", "Qwen/Qwen2.5-0.5B-Instruct"),
            "messages": [{"role": "user", "content": record["prompt"]}],
            "max_tokens": record.get("max_tokens", 32),
            "temperature": 0,
            "stream": True,
            "router_mode": "colocated",
            "prefix_key": record.get("prefix_key"),
        }
        result = request_stream(args.url, payload, args.timeout, {"X-Request-ID": f"lab03-cache-{record['id']}"})
        rows.append({"benchmark": "cache_reuse", "workload_id": record["id"], "prefix_group": record.get("prefix_group", ""), "expected_shared_prefix": record.get("shared_prefix", False), "status": result.get("status"), "ttft_ms": result.get("ttft_ms", "NA"), "e2e_ms": result.get("e2e_ms", "NA"), "prompt_tokens": result.get("prompt_tokens", "NA"), "cached_tokens": result.get("cached_tokens", "NA"), "token_metric_status": result.get("token_metric_status", "unavailable"), "error": result.get("error", "")})
    write_csv(Path(args.output), rows)


if __name__ == "__main__":
    main()

"""Compare colocated and P/D routing without fabricating unavailable metrics."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_jsonl, request_stream, write_csv  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "live", "design"], default="auto")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    parser.add_argument("--dataset", default=str(Path(__file__).parents[1] / "datasets" / "mixed_workload.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).parents[1] / "results" / "pd_raw.csv"))
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    rows = load_jsonl(Path(args.dataset))
    if args.mode == "design":
        write_csv(Path(args.output), [{"status": "DESIGN_ONLY", "reason": "P/D requires two GPUs and a validated connector; no latency is inferred."}])
        return

    results = []
    for item in rows:
        for route in ("colocated", "pd"):
            request_id = f"lab03-pd-{item['id']}-{route}"
            payload = {
                "model": item.get("model", "Qwen/Qwen2.5-0.5B-Instruct"),
                "messages": [{"role": "user", "content": item["prompt"]}],
                "max_tokens": int(item.get("max_tokens", 32)),
                "temperature": 0,
                "stream": True,
                "router_mode": route,
                "prefix_key": item.get("prefix_key"),
            }
            if args.mode == "auto":
                # The router is the only authority for live reachability. An error row remains evidence.
                pass
            result = request_stream(args.url, payload, args.timeout, {"X-Request-ID": request_id})
            results.append({
                "benchmark": "pd",
                "workload_id": item["id"],
                "route": route,
                "request_id": request_id,
                "status": result.get("status"),
                "ttft_ms": result.get("ttft_ms", "NA"),
                "tpot_ms": result.get("tpot_ms", "NA"),
                "e2e_ms": result.get("e2e_ms", "NA"),
                "completion_tokens": result.get("completion_tokens", "NA"),
                "token_metric_status": result.get("token_metric_status", "unavailable"),
                "kv_transfer_ms": result.get("response_headers", {}).get("x-lab03-kv-transfer-ms", "NA"),
                "kv_transfer_status": result.get("response_headers", {}).get("x-lab03-kv-transfer-status", "unavailable"),
                "error": result.get("error", ""),
                "started_unix": time.time(),
            })
    write_csv(Path(args.output), results)


if __name__ == "__main__":
    main()

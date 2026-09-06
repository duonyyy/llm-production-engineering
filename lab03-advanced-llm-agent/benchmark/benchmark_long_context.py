"""Run the long-context workload against an already-started router."""

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
    parser.add_argument("--dataset", default=str(Path(__file__).parents[1] / "datasets" / "long_context.jsonl"))
    parser.add_argument("--output", default=str(Path(__file__).parents[1] / "results" / "long_context_raw.csv"))
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    records = load_jsonl(Path(args.dataset))
    if args.mode == "design":
        write_csv(Path(args.output), [{"status": "DESIGN_ONLY", "reason": "No endpoint was called."}])
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
        }
        result = request_stream(args.url, payload, args.timeout, {"X-Request-ID": f"lab03-long-{record['id']}"})
        rows.append({"benchmark": "long_context", "workload_id": record["id"], **{key: result.get(key, "NA") for key in ("status", "ttft_ms", "tpot_ms", "e2e_ms", "prompt_tokens", "completion_tokens", "token_metric_status")}, "error": result.get("error", "")})
    write_csv(Path(args.output), rows)


if __name__ == "__main__":
    main()

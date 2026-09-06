#!/usr/bin/env python3
"""
benchmark_prefix_cache.py — Benchmark đánh giá Automatic Prefix Caching (A/B Test).

So sánh 2 điều kiện:
    1. Workload có Shared Prefix (datasets/shared_prefix_prompts.jsonl)
    2. Workload không có Shared Prefix làm Control (datasets/normal_prompts.jsonl)

Chạy trên cả 2 cấu hình server:
    - Server Baseline (Prefix Cache OFF) -> kết quả: results/prefix_cache_off.csv
    - Server Prefix Cache (Prefix Cache ON) -> kết quả: results/prefix_cache_on.csv

Cách dùng:
    # 1. Chạy với server Prefix Cache OFF:
    python benchmark/benchmark_prefix_cache.py \
        --url http://localhost:8000 \
        --model "Qwen/Qwen2.5-0.5B-Instruct" \
        --label "prefix_cache_off" \
        --output results/prefix_cache_off.csv

    # 2. Đổi server sang Prefix Cache ON rồi chạy:
    python benchmark/benchmark_prefix_cache.py \
        --url http://localhost:8000 \
        --model "Qwen/Qwen2.5-0.5B-Instruct" \
        --label "prefix_cache_on" \
        --output results/prefix_cache_on.csv
"""

import argparse
import asyncio
import csv
import json
import sys
import time
import uuid
from pathlib import Path

import httpx
import numpy as np

from benchmark_common import (
    approx_tpot,
    build_payload,
    finalize_token_counts,
    inspect_event,
    load_tokenizer,
    new_stream_state,
    parse_data_line,
)

# Thiết lập UTF-8 cho stdout/stderr trên mọi hệ điều hành (tránh UnicodeEncodeError trên Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ==============================================================================
# Async SSE Streaming Request
# ==============================================================================
async def benchmark_single_async(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    request_id: str,
    timeout: float = 180.0,
    tokenizer=None,
    include_usage: bool = False,
) -> dict:
    """Gửi một request streaming và đo latency/token metrics minh bạch."""

    payload = build_payload(model, messages, max_tokens, include_usage)
    state = new_stream_state(messages)

    result = {
        "request_id": request_id,
        "prompt_chars": state["prompt_chars"],
        "prompt_tokens": None,
        "completion_tokens": None,
        "output_chunks": 0,
        "token_count_source": "unavailable",
        "start_time": 0.0,
        "first_token_time": 0.0,
        "end_time": 0.0,
        "ttft": 0.0,
        "e2e_latency": 0.0,
        "approx_tpot": None,
        "success": False,
        "stream_complete": False,
        "finish_reason": None,
        "http_status": 0,
        "error": "",
    }

    start = time.perf_counter()
    result["start_time"] = start

    try:
        async with client.stream(
            "POST",
            f"{url}/v1/chat/completions",
            json=payload,
            timeout=timeout,
        ) as response:
            result["http_status"] = response.status_code
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                result["end_time"] = time.perf_counter()
                result["e2e_latency"] = result["end_time"] - start
                return result

            first_token_received = False
            buffer = ""

            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    event, done = parse_data_line(line)
                    if done:
                        state["stream_done"] = True
                        break
                    if event is None:
                        continue
                    content = inspect_event(event, state)
                    if content and not first_token_received:
                        result["first_token_time"] = time.perf_counter()
                        result["ttft"] = result["first_token_time"] - start
                        first_token_received = True

                if state["stream_done"]:
                    break

            if not state["stream_done"]:
                result["end_time"] = time.perf_counter()
                result["e2e_latency"] = result["end_time"] - start
                result["error"] = "stream ended without SSE [DONE]"
                return result

        end = time.perf_counter()
        result["end_time"] = end
        result["e2e_latency"] = end - start
        finalize_token_counts(state, messages, tokenizer)
        result["prompt_tokens"] = state["prompt_tokens"]
        result["completion_tokens"] = state["completion_tokens"]
        result["output_chunks"] = state["output_chunks"]
        result["token_count_source"] = state["token_count_source"]
        result["stream_complete"] = state["stream_done"]
        result["finish_reason"] = state["finish_reason"]
        result["success"] = True

        result["approx_tpot"] = approx_tpot(
            result["e2e_latency"],
            result["ttft"],
            result["completion_tokens"],
        )

    except httpx.TimeoutException:
        result["end_time"] = time.perf_counter()
        result["e2e_latency"] = result["end_time"] - start
        result["error"] = "timeout"
    except Exception as e:
        result["end_time"] = time.perf_counter()
        result["e2e_latency"] = result["end_time"] - start
        result["error"] = str(e)

    return result


# ==============================================================================
# Chạy một batch requests với Shared HTTP Client
# ==============================================================================
async def run_batch(
    url: str,
    model: str,
    prompts: list[list[dict]],
    max_tokens: int,
    concurrency: int,
    label: str,
    timeout: float,
    tokenizer=None,
    include_usage: bool = False,
) -> tuple[list[dict], float]:
    """Chạy toàn bộ batch và trả về raw results cùng wall duration."""
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency * 2, max_keepalive_connections=concurrency * 2)

    async with httpx.AsyncClient(limits=limits) as client:
        async def bounded(msgs: list[dict], idx: int) -> dict:
            async with semaphore:
                req_id = f"{label[:4]}-{idx:03d}"
                r = await benchmark_single_async(
                    client,
                    url,
                    model,
                    msgs,
                    max_tokens,
                    req_id,
                    timeout,
                    tokenizer=tokenizer,
                    include_usage=include_usage,
                )
                r["label"] = label
                r["seq_index"] = idx
                return r

        batch_start = time.perf_counter()
        tasks = [bounded(msgs, i) for i, msgs in enumerate(prompts)]
        results = await asyncio.gather(*tasks)
        batch_duration = time.perf_counter() - batch_start

    return list(results), batch_duration


# ==============================================================================
# Phân tích thống kê cho từng workload
# ==============================================================================
def summarize_results(results: list[dict], label: str, wall_duration: float) -> dict:
    ok = [r for r in results if r["success"]]
    failed = len(results) - len(ok)

    if not ok:
        return {
            "label": label,
            "requests": len(results),
            "success": 0,
            "failed": failed,
            "ttft_p50": 0.0,
            "ttft_p90": 0.0,
            "ttft_p95": 0.0,
            "e2e_p50": 0.0,
            "e2e_p95": 0.0,
            "approx_tpot_p50": 0.0,
            "requests_per_sec": 0.0,
            "tokens_per_sec": None,
            "token_metrics_complete": False,
        }

    ttfts = np.array([r["ttft"] for r in ok])
    e2es = np.array([r["e2e_latency"] for r in ok])
    tpots = np.array([r["approx_tpot"] for r in ok if r["approx_tpot"] is not None])
    token_values = [
        r["completion_tokens"]
        for r in ok
        if isinstance(r["completion_tokens"], int)
    ]
    token_metrics_complete = len(token_values) == len(ok)
    total_tokens = sum(token_values) if token_values else None

    # Phân tích Cold Request (request đầu tiên) vs Warm Requests (request từ thứ 2 trở đi)
    first_req = next(
        (row for row in ok if row.get("seq_index") == 0),
        ok[0] if ok else None,
    )
    first_ttft = first_req["ttft"] if first_req else 0.0

    warm_rows = [row for row in ok if row is not first_req]
    warm_ttfts = np.array([row["ttft"] for row in warm_rows]) if warm_rows else ttfts
    warm_ttft_p50 = float(np.percentile(warm_ttfts, 50)) if len(warm_ttfts) > 0 else 0.0

    return {
        "label": label,
        "requests": len(results),
        "success": len(ok),
        "failed": failed,
        "wall_duration_s": round(wall_duration, 2),
        "first_req_ttft": round(first_ttft, 4),
        "warm_ttft_p50": round(warm_ttft_p50, 4),
        "ttft_p50": round(float(np.percentile(ttfts, 50)), 4),
        "ttft_p90": round(float(np.percentile(ttfts, 90)), 4),
        "ttft_p95": round(float(np.percentile(ttfts, 95)), 4),
        "e2e_p50": round(float(np.percentile(e2es, 50)), 4),
        "e2e_p95": round(float(np.percentile(e2es, 95)), 4),
        "approx_tpot_p50": round(float(np.percentile(tpots, 50)), 4) if len(tpots) > 0 else 0.0,
        "requests_per_sec": round(len(ok) / wall_duration, 2) if wall_duration > 0 else 0.0,
        "tokens_per_sec": round(total_tokens / wall_duration, 2)
        if token_metrics_complete and wall_duration > 0
        else None,
        "token_metrics_complete": token_metrics_complete,
    }


# ==============================================================================
# Helper I/O
# ==============================================================================
def load_prompts(filepath: str) -> list[list[dict]]:
    prompts = []
    path = Path(filepath)
    if not path.exists():
        print(f"✗ File không tồn tại: {filepath}")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                messages = data.get("messages", [])
                if messages:
                    prompts.append(messages)
            except json.JSONDecodeError:
                continue
    return prompts


FIELDNAMES = [
    "label",
    "seq_index",
    "request_id",
    "prompt_chars",
    "prompt_tokens",
    "completion_tokens",
    "output_chunks",
    "token_count_source",
    "ttft",
    "e2e_latency",
    "approx_tpot",
    "success",
    "stream_complete",
    "finish_reason",
    "http_status",
    "error",
]


def save_csv(results: list[dict], filepath: str) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(f"  CSV đã lưu: {path}")


# ==============================================================================
# Main
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Benchmark Prefix Caching (A/B Test)."
    )
    parser.add_argument(
        "--url", default="http://localhost:8000", help="vLLM server URL"
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Model name",
    )
    parser.add_argument(
        "--shared-prefix-file",
        default="datasets/shared_prefix_prompts.jsonl",
        help="File chứa prompts có shared prefix",
    )
    parser.add_argument(
        "--control-file",
        default="datasets/normal_prompts.jsonl",
        help="File chứa prompts control (không shared prefix)",
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=10,
        help="Số requests cho mỗi workload (profile 4GB mặc định: 10)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=2,
        help="Concurrency khi benchmark (giữ cố định giữa A và B)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=64, help="Max output tokens"
    )
    parser.add_argument(
        "--timeout", type=float, default=180.0, help="Timeout mỗi request"
    )
    parser.add_argument(
        "--tokenizer",
        default=None,
        help="Tokenizer HF để fallback token count; nên dùng cùng tokenizer của server.",
    )
    parser.add_argument(
        "--include-usage",
        action="store_true",
        help="Yêu cầu usage chunk cuối stream; version-sensitive.",
    )
    parser.add_argument(
        "--label",
        required=True,
        help="Nhãn cho lần chạy (ví dụ: prefix_cache_off hoặc prefix_cache_on)",
    )
    parser.add_argument(
        "--output",
        default="results/prefix_cache_results.csv",
        help="File CSV lưu kết quả raw",
    )

    args = parser.parse_args()

    # Load datasets
    shared_prompts = load_prompts(args.shared_prefix_file)[: args.num_requests]
    control_prompts = load_prompts(args.control_file)[: args.num_requests]

    print("================================================================")
    print("  LAB 01 — BENCHMARK PREFIX CACHING EXPERIMENT")
    print(f"  Label        : {args.label}")
    print(f"  Server URL   : {args.url}")
    print(f"  Model        : {args.model}")
    print(f"  Concurrency  : {args.concurrency}")
    print(f"  Max tokens   : {args.max_tokens}")
    print(f"  Shared Reqs  : {len(shared_prompts)}")
    print(f"  Control Reqs : {len(control_prompts)}")
    print(f"  Tokenizer    : {args.tokenizer or '(server usage only)'}")
    print("================================================================")

    tokenizer, _ = load_tokenizer(args.tokenizer)

    # 1. Chạy Shared Prefix Workload
    print(f"\n[Phase 1] Đang chạy Shared-Prefix Workload ({len(shared_prompts)} reqs)...")
    shared_results, shared_wall = asyncio.run(
        run_batch(
            url=args.url,
            model=args.model,
            prompts=shared_prompts,
            max_tokens=args.max_tokens,
            concurrency=args.concurrency,
            label=f"{args.label}_shared",
            timeout=args.timeout,
            tokenizer=tokenizer,
            include_usage=args.include_usage,
        )
    )
    shared_summary = summarize_results(shared_results, f"{args.label}_shared", shared_wall)

    # 2. Chạy Control Workload
    print(f"\n[Phase 2] Đang chạy Control Workload ({len(control_prompts)} reqs)...")
    control_results, control_wall = asyncio.run(
        run_batch(
            url=args.url,
            model=args.model,
            prompts=control_prompts,
            max_tokens=args.max_tokens,
            concurrency=args.concurrency,
            label=f"{args.label}_control",
            timeout=args.timeout,
            tokenizer=tokenizer,
            include_usage=args.include_usage,
        )
    )
    control_summary = summarize_results(control_results, f"{args.label}_control", control_wall)

    # Gộp kết quả
    all_results = shared_results + control_results
    save_csv(all_results, args.output)

    # Lưu Summary JSON
    summary_path = Path(args.output).with_suffix(".summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump([shared_summary, control_summary], f, indent=2, ensure_ascii=False)
    print(f"  Summary JSON: {summary_path}")

    # In bảng so sánh
    print("\n" + "=" * 80)
    print("  KẾT QUẢ PHÂN TÍCH TỔNG HỢP")
    print("=" * 80)
    print(f"{'Workload':<25} {'TTFT p50':<12} {'TTFT p95':<12} {'Warm TTFT':<12} {'Throughput':<12}")
    print("-" * 80)
    print(
        f"{shared_summary['label']:<25} "
        f"{shared_summary['ttft_p50'] * 1000:<10.1f}ms "
        f"{shared_summary['ttft_p95'] * 1000:<10.1f}ms "
        f"{shared_summary['warm_ttft_p50'] * 1000:<10.1f}ms "
        f"{shared_summary['requests_per_sec']:<8.2f} r/s"
    )
    print(
        f"{control_summary['label']:<25} "
        f"{control_summary['ttft_p50'] * 1000:<10.1f}ms "
        f"{control_summary['ttft_p95'] * 1000:<10.1f}ms "
        f"{control_summary['warm_ttft_p50'] * 1000:<10.1f}ms "
        f"{control_summary['requests_per_sec']:<8.2f} r/s"
    )
    print("=" * 80)
    print("\n💡 Gợi ý quan sát:")
    print("  - Nếu Prefix Cache ON: TTFT của 'shared' (đặc biệt warm requests) sẽ giảm mạnh so với OFF.")
    print("  - Workload 'control' sẽ không có sự khác biệt lớn giữa ON và OFF vì prefix không lặp lại.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
benchmark_concurrency.py — Benchmark vLLM với các mức concurrency khác nhau.

Đo lường chi tiết:
    - TTFT p50, p90, p95, p99 (Time to First Token)
    - E2E Latency p50, p90, p95, p99 (End-to-End Latency)
    - Approximate TPOT p50, p95 (Time Per Output Token)
    - Request throughput (req/s) đo theo wall-clock duration thực tế
    - Output token throughput (tokens/s)
    - Error rate & HTTP status accounting

Cấu trúc output:
    - Summary CSV: Chỉ số tổng hợp p50/p95/throughput theo từng concurrency level
    - Raw CSV: Từng request riêng lẻ với timestamp, TTFT, E2E để phân tích sâu
    - JSON summary: Dành cho automated pipeline

Cách dùng:
    python benchmark/benchmark_concurrency.py \
        --url http://localhost:8000 \
        --model "Qwen/Qwen2.5-0.5B-Instruct" \
        --input-file datasets/normal_prompts.jsonl \
        --concurrency 1 2 4 \
        --requests-per-level 5 \
        --max-tokens 64 \
        --output results/concurrency_sweep.csv
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
# Async SSE streaming benchmark cho 1 request
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
    """Gửi một streaming request và đo latency/token metrics minh bạch."""

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
# Chạy một mức concurrency với Client Connection Pool tái sử dụng
# ==============================================================================
async def run_concurrency_level(
    url: str,
    model: str,
    prompts: list[list[dict]],
    max_tokens: int,
    concurrency: int,
    timeout: float,
    tokenizer=None,
    include_usage: bool = False,
) -> tuple[list[dict], float]:
    """Chạy prompts với concurrency giới hạn bằng semaphore và đo tổng wall duration."""

    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(
        max_connections=concurrency * 2,
        max_keepalive_connections=concurrency * 2,
    )

    async with httpx.AsyncClient(limits=limits) as shared_client:
        async def bounded_request(messages: list[dict]) -> dict:
            async with semaphore:
                req_id = str(uuid.uuid4())[:8]
                res = await benchmark_single_async(
                    shared_client,
                    url,
                    model,
                    messages,
                    max_tokens,
                    req_id,
                    timeout,
                    tokenizer=tokenizer,
                    include_usage=include_usage,
                )
                res["concurrency_level"] = concurrency
                return res

        batch_start = time.perf_counter()
        tasks = [bounded_request(msgs) for msgs in prompts]
        results = await asyncio.gather(*tasks)
        batch_duration = time.perf_counter() - batch_start

    return list(results), batch_duration


# ==============================================================================
# Tính toán thống kê theo percentile và throughput
# ==============================================================================
def compute_stats(
    results: list[dict], concurrency: int, wall_duration: float
) -> dict:
    """Tính p50, p90, p95, p99 TTFT, E2E và Throughput chính xác dựa trên wall_duration."""
    ok = [r for r in results if r["success"]]
    failed = len(results) - len(ok)

    if not ok:
        return {
            "concurrency": concurrency,
            "requests": len(results),
            "success": 0,
            "failed": failed,
            "error_rate": 1.0,
            "wall_duration_s": round(wall_duration, 2),
            "ttft_p50": 0.0,
            "ttft_p90": 0.0,
            "ttft_p95": 0.0,
            "ttft_p99": 0.0,
            "e2e_p50": 0.0,
            "e2e_p90": 0.0,
            "e2e_p95": 0.0,
            "e2e_p99": 0.0,
            "approx_tpot_p50": 0.0,
            "approx_tpot_p95": 0.0,
            "total_tokens": None,
            "token_metrics_complete": False,
            "requests_per_sec": 0.0,
            "tokens_per_sec": None,
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

    return {
        "concurrency": concurrency,
        "requests": len(results),
        "success": len(ok),
        "failed": failed,
        "error_rate": round(failed / len(results), 4),
        "wall_duration_s": round(wall_duration, 2),
        "ttft_p50": round(float(np.percentile(ttfts, 50)), 4),
        "ttft_p90": round(float(np.percentile(ttfts, 90)), 4),
        "ttft_p95": round(float(np.percentile(ttfts, 95)), 4),
        "ttft_p99": round(float(np.percentile(ttfts, 99)), 4),
        "e2e_p50": round(float(np.percentile(e2es, 50)), 4),
        "e2e_p90": round(float(np.percentile(e2es, 90)), 4),
        "e2e_p95": round(float(np.percentile(e2es, 95)), 4),
        "e2e_p99": round(float(np.percentile(e2es, 99)), 4),
        "approx_tpot_p50": round(float(np.percentile(tpots, 50)), 4) if len(tpots) > 0 else 0.0,
        "approx_tpot_p95": round(float(np.percentile(tpots, 95)), 4) if len(tpots) > 0 else 0.0,
        "total_tokens": total_tokens,
        "token_metrics_complete": token_metrics_complete,
        "requests_per_sec": round(len(ok) / wall_duration, 2) if wall_duration > 0 else 0.0,
        "tokens_per_sec": round(total_tokens / wall_duration, 2)
        if token_metrics_complete and wall_duration > 0
        else None,
    }


# ==============================================================================
# Load prompts từ JSONL
# ==============================================================================
def load_prompts(filepath: str) -> list[list[dict]]:
    prompts = []
    path = Path(filepath)
    if not path.exists():
        print(f"✗ File không tồn tại: {filepath}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                messages = data.get("messages", [])
                if messages:
                    prompts.append(messages)
            except json.JSONDecodeError as e:
                print(f"  Dòng {line_num}: JSON lỗi — {e}")
    return prompts


# ==============================================================================
# Lưu file CSV
# ==============================================================================
SUMMARY_FIELDS = [
    "concurrency",
    "requests",
    "success",
    "failed",
    "error_rate",
    "wall_duration_s",
    "ttft_p50",
    "ttft_p90",
    "ttft_p95",
    "ttft_p99",
    "e2e_p50",
    "e2e_p90",
    "e2e_p95",
    "e2e_p99",
    "approx_tpot_p50",
    "approx_tpot_p95",
    "total_tokens",
    "token_metrics_complete",
    "requests_per_sec",
    "tokens_per_sec",
]

RAW_FIELDS = [
    "concurrency_level",
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


def save_summary_csv(stats: list[dict], filepath: str) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(stats)
    print(f"  Summary CSV: {path}")


def save_raw_csv(raw_results: list[dict], filepath: str) -> None:
    path = Path(filepath)
    raw_path = path.with_name(path.stem + "_raw.csv")
    with open(raw_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(raw_results)
    print(f"  Raw CSV: {raw_path}")


# ==============================================================================
# Main
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Benchmark vLLM với Concurrency Sweep."
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
        "--input-file",
        default="datasets/normal_prompts.jsonl",
        help="File JSONL chứa prompts",
    )
    parser.add_argument(
        "--concurrency",
        nargs="+",
        type=int,
        default=[1, 2, 4],
        help="Danh sách mức concurrency (mặc định cho RTX 3050 4GB: 1 2 4)",
    )
    parser.add_argument(
        "--requests-per-level",
        type=int,
        default=5,
        help="Số requests cho mỗi mức concurrency (profile 4GB)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=64, help="Max output tokens"
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Timeout mỗi request (s)",
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
        "--output",
        default="results/concurrency_sweep.csv",
        help="File CSV lưu summary",
    )

    args = parser.parse_args()

    # Load prompts
    all_prompts = load_prompts(args.input_file)
    if not all_prompts:
        print("✗ Không có prompts hợp lệ.")
        sys.exit(1)

    print("================================================================")
    print("  LAB 01 — BENCHMARK CONCURRENCY SWEEP")
    print(f"  Server URL   : {args.url}")
    print(f"  Model        : {args.model}")
    print(f"  Dataset      : {args.input_file} ({len(all_prompts)} prompts)")
    print(f"  Concurrency  : {args.concurrency}")
    print(f"  Reqs / Level : {args.requests_per_level}")
    print(f"  Max tokens   : {args.max_tokens}")
    print(f"  Output CSV   : {args.output}")
    print(f"  Tokenizer    : {args.tokenizer or '(server usage only)'}")

    tokenizer, _ = load_tokenizer(args.tokenizer)
    print("================================================================")

    # Warmup 1 request để đảm bảo GPU kernel đã compile
    print("\n[Warm-up] Gửi 1 request khởi động...")
    try:
        with httpx.Client(timeout=60.0) as warmup_client:
            warmup_resp = warmup_client.post(
                f"{args.url}/v1/chat/completions",
                json={
                    "model": args.model,
                    "messages": [{"role": "user", "content": "Ping"}],
                    "max_tokens": 10,
                },
            )
            if warmup_resp.status_code == 200:
                print("  ✓ Warm-up thành công.")
            else:
                print(f"  ⚠ Warm-up status: {warmup_resp.status_code}")
    except Exception as e:
        print(f"  ⚠ Warm-up gặp lỗi (vẫn tiếp tục): {e}")

    summary_stats = []
    all_raw_results = []

    for c in args.concurrency:
        # Chọn mẫu prompts
        if len(all_prompts) >= args.requests_per_level:
            level_prompts = all_prompts[: args.requests_per_level]
        else:
            # Lặp lại nếu thiếu
            repeats = (args.requests_per_level // len(all_prompts)) + 1
            level_prompts = (all_prompts * repeats)[: args.requests_per_level]

        print(f"\n--- Đang chạy Concurrency = {c} ({len(level_prompts)} requests) ---")

        results, wall_duration = asyncio.run(
            run_concurrency_level(
                url=args.url,
                model=args.model,
                prompts=level_prompts,
                max_tokens=args.max_tokens,
                concurrency=c,
                timeout=args.timeout,
                tokenizer=tokenizer,
                include_usage=args.include_usage,
            )
        )

        all_raw_results.extend(results)
        stats = compute_stats(results, c, wall_duration)
        summary_stats.append(stats)

        print(f"  Hoàn thành trong: {stats['wall_duration_s']}s")
        print(f"  Thành công      : {stats['success']}/{stats['requests']} (Lỗi: {stats['error_rate'] * 100:.1f}%)")
        print(f"  TTFT p50        : {stats['ttft_p50'] * 1000:.1f} ms  |  TTFT p95: {stats['ttft_p95'] * 1000:.1f} ms")
        print(f"  E2E p50         : {stats['e2e_p50']:.3f} s   |  E2E p95 : {stats['e2e_p95']:.3f} s")
        tokens_per_sec = (
            f"{stats['tokens_per_sec']:.2f} tokens/s"
            if stats["tokens_per_sec"] is not None
            else "token metrics unavailable"
        )
        print(f"  Throughput      : {stats['requests_per_sec']:.2f} req/s  |  {tokens_per_sec}")

    # Lưu kết quả
    print("\n--- Đang lưu kết quả ---")
    save_summary_csv(summary_stats, args.output)
    save_raw_csv(all_raw_results, args.output)

    # Lưu JSON summary
    json_path = Path(args.output).with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2, ensure_ascii=False)
    print(f"  Summary JSON: {json_path}")

    # Bảng tổng kết ASCII
    print("\n" + "=" * 80)
    print(f"{'Conc':<6} {'Reqs':<6} {'TTFT p50':<12} {'TTFT p95':<12} {'E2E p95':<12} {'Req/s':<10} {'Tok/s':<10} {'Err%':<6}")
    print("-" * 80)
    for s in summary_stats:
        print(
            f"{s['concurrency']:<6} "
            f"{s['requests']:<6} "
            f"{s['ttft_p50'] * 1000:<10.1f}ms "
            f"{s['ttft_p95'] * 1000:<10.1f}ms "
            f"{s['e2e_p95']:<10.3f}s "
            f"{s['requests_per_sec']:<10.2f} "
            f"{str(s['tokens_per_sec'] if s['tokens_per_sec'] is not None else 'NA'):<10} "
            f"{s['error_rate'] * 100:<6.1f}"
        )
    print("=" * 80)


if __name__ == "__main__":
    main()

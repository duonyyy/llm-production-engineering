#!/usr/bin/env python3
"""Benchmark ảnh hưởng của prompt length lên TTFT.

Script tạo workload deterministic theo ngân sách ký tự, sau đó lưu cả
``prompt_chars`` và ``prompt_tokens`` (API usage hoặc tokenizer estimate).
Không dùng số ký tự để gọi là token.
"""

from __future__ import annotations

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


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def make_messages(bucket: str, target_chars: int, index: int) -> list[dict]:
    """Tạo prompt deterministic; target là ký tự, token count đo riêng."""

    paragraph = (
        "Hệ thống inference cần quan sát queue, Prefill, Decode, KV Cache và "
        "tail latency. Nội dung này chỉ tạo tải có kiểm soát cho bài lab. "
    )
    question = f"\nCâu hỏi {index}: Hãy tóm tắt cơ chế của workload {bucket}."
    repeat_count = max(1, target_chars // len(paragraph) + 2)
    content = (paragraph * repeat_count)[: max(0, target_chars - len(question))] + question
    return [{"role": "user", "content": content}]


async def benchmark_one(
    client: httpx.AsyncClient,
    url: str,
    model: str,
    messages: list[dict],
    bucket: str,
    target_chars: int,
    index: int,
    max_tokens: int,
    timeout: float,
    tokenizer=None,
    include_usage: bool = False,
) -> dict:
    """Gửi một request và yêu cầu stream kết thúc bằng [DONE]."""

    start = time.perf_counter()
    state = new_stream_state(messages)
    result = {
        "bucket": bucket,
        "target_prompt_chars": target_chars,
        "request_id": f"{bucket[:3]}-{index:03d}-{uuid.uuid4().hex[:6]}",
        "prompt_chars": state["prompt_chars"],
        "prompt_tokens": None,
        "completion_tokens": None,
        "output_chunks": 0,
        "token_count_source": "unavailable",
        "ttft": 0.0,
        "e2e_latency": 0.0,
        "approx_tpot": None,
        "success": False,
        "stream_complete": False,
        "finish_reason": None,
        "http_status": 0,
        "error": "",
    }

    try:
        async with client.stream(
            "POST",
            f"{url.rstrip('/')}/v1/chat/completions",
            json=build_payload(model, messages, max_tokens, include_usage),
            timeout=timeout,
        ) as response:
            result["http_status"] = response.status_code
            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                return result

            first_content = False
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    event, done = parse_data_line(line)
                    if done:
                        state["stream_done"] = True
                        break
                    if event is None:
                        continue
                    content = inspect_event(event, state)
                    if content and not first_content:
                        result["ttft"] = time.perf_counter() - start
                        first_content = True
                if state["stream_done"]:
                    break

            if not state["stream_done"]:
                result["error"] = "stream ended without SSE [DONE]"
                return result

        result["e2e_latency"] = time.perf_counter() - start
        finalize_token_counts(state, messages, tokenizer)
        result["prompt_tokens"] = state["prompt_tokens"]
        result["completion_tokens"] = state["completion_tokens"]
        result["output_chunks"] = state["output_chunks"]
        result["token_count_source"] = state["token_count_source"]
        result["stream_complete"] = state["stream_done"]
        result["finish_reason"] = state["finish_reason"]
        result["approx_tpot"] = approx_tpot(
            result["e2e_latency"], result["ttft"], result["completion_tokens"]
        )
        result["success"] = True
    except httpx.TimeoutException:
        result["error"] = "timeout"
    except Exception as exc:
        result["error"] = str(exc)
    finally:
        result["e2e_latency"] = result["e2e_latency"] or time.perf_counter() - start

    return result


async def run_bucket(
    url: str,
    model: str,
    bucket: str,
    target_chars: int,
    requests_count: int,
    concurrency: int,
    max_tokens: int,
    timeout: float,
    tokenizer=None,
    include_usage: bool = False,
) -> tuple[list[dict], float]:
    semaphore = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(
        max_connections=concurrency * 2,
        max_keepalive_connections=concurrency * 2,
    )
    async with httpx.AsyncClient(limits=limits) as client:
        async def bounded(index: int) -> dict:
            async with semaphore:
                return await benchmark_one(
                    client,
                    url,
                    model,
                    make_messages(bucket, target_chars, index),
                    bucket,
                    target_chars,
                    index,
                    max_tokens,
                    timeout,
                    tokenizer,
                    include_usage,
                )

        start = time.perf_counter()
        results = await asyncio.gather(*(bounded(i) for i in range(requests_count)))
        return list(results), time.perf_counter() - start


def summarize(results: list[dict], wall_duration: float) -> dict:
    ok = [row for row in results if row["success"]]
    token_values = [row["completion_tokens"] for row in ok if isinstance(row["completion_tokens"], int)]
    tpot_values = [row["approx_tpot"] for row in ok if row["approx_tpot"] is not None]
    prompt_token_values = [row["prompt_tokens"] for row in ok if isinstance(row["prompt_tokens"], int)]
    return {
        "bucket": results[0]["bucket"] if results else "",
        "target_prompt_chars": results[0]["target_prompt_chars"] if results else 0,
        "requests": len(results),
        "success": len(ok),
        "failed": len(results) - len(ok),
        "error_rate": round((len(results) - len(ok)) / len(results), 4) if results else 1.0,
        "prompt_chars_p50": round(float(np.percentile([r["prompt_chars"] for r in ok], 50)), 1) if ok else None,
        "prompt_tokens_p50": round(float(np.percentile(prompt_token_values, 50)), 1) if prompt_token_values else None,
        "ttft_p50": round(float(np.percentile([r["ttft"] for r in ok], 50)), 4) if ok else None,
        "ttft_p95": round(float(np.percentile([r["ttft"] for r in ok], 95)), 4) if ok else None,
        "e2e_p50": round(float(np.percentile([r["e2e_latency"] for r in ok], 50)), 4) if ok else None,
        "e2e_p95": round(float(np.percentile([r["e2e_latency"] for r in ok], 95)), 4) if ok else None,
        "approx_tpot_p50": round(float(np.percentile(tpot_values, 50)), 4) if tpot_values else None,
        "completion_tokens_total": sum(token_values) if len(token_values) == len(ok) else None,
        "wall_duration_s": round(wall_duration, 4),
        "requests_per_sec": round(len(ok) / wall_duration, 4) if wall_duration > 0 else 0.0,
        "tokens_per_sec": round(sum(token_values) / wall_duration, 4) if len(token_values) == len(ok) and wall_duration > 0 else None,
        "token_metrics_complete": len(token_values) == len(ok) and bool(ok),
    }


RAW_FIELDS = [
    "bucket", "target_prompt_chars", "request_id", "prompt_chars", "prompt_tokens",
    "completion_tokens", "output_chunks", "token_count_source", "ttft", "e2e_latency",
    "approx_tpot", "success", "stream_complete", "finish_reason", "http_status", "error",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark prompt length vs TTFT.")
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--targets", nargs="+", default=["short:128", "medium:512", "long:1024"], help="bucket:target_chars")
    parser.add_argument("--requests-per-bucket", type=int, default=10)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=32)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--tokenizer", default=None, help="Tokenizer HF cùng model để fallback token count.")
    parser.add_argument("--include-usage", action="store_true", help="Yêu cầu usage chunk; version-sensitive.")
    parser.add_argument("--output", default="results/prompt_length.csv")
    args = parser.parse_args()

    if args.requests_per_bucket < 1 or args.concurrency < 1 or args.max_tokens < 1:
        parser.error("requests-per-bucket, concurrency và max-tokens phải >= 1")

    targets: list[tuple[str, int]] = []
    for item in args.targets:
        try:
            bucket, chars_text = item.split(":", 1)
            chars = int(chars_text)
        except ValueError:
            parser.error(f"Target không hợp lệ '{item}'; dùng dạng bucket:chars")
        if not bucket or chars < 1:
            parser.error(f"Target không hợp lệ '{item}'")
        targets.append((bucket, chars))

    tokenizer, _ = load_tokenizer(args.tokenizer)
    all_results: list[dict] = []
    summaries: list[dict] = []
    for bucket, target_chars in targets:
        results, wall = asyncio.run(run_bucket(
            args.url, args.model, bucket, target_chars, args.requests_per_bucket,
            args.concurrency, args.max_tokens, args.timeout, tokenizer, args.include_usage,
        ))
        all_results.extend(results)
        summaries.append(summarize(results, wall))
        print(f"{bucket}: TTFT p50={summaries[-1]['ttft_p50']}s, TTFT p95={summaries[-1]['ttft_p95']}s")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=RAW_FIELDS)
        writer.writeheader()
        writer.writerows(all_results)
    summary_output = output.with_name(output.stem + ".summary.csv")
    summary_fields = list(summaries[0].keys()) if summaries else []
    with summary_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(summaries)
    summary_path = output.with_suffix(".summary.json")
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summaries, handle, indent=2, ensure_ascii=False)
    print(f"Raw CSV: {output}")
    print(f"Summary CSV: {summary_output}")
    print(f"Summary JSON: {summary_path}")


if __name__ == "__main__":
    main()

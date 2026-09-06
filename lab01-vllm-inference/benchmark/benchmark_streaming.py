#!/usr/bin/env python3
"""
benchmark_streaming.py — Benchmark streaming inference trên vLLM OpenAI-compatible API.

Đo lường:
    - TTFT (Time to First Token)
    - E2E Latency (End-to-End)
    - Approximate TPOT (Time Per Output Token)
    - Output token count
    - HTTP status / success

Kết quả được lưu dưới dạng CSV và JSON.

Cách dùng:
    python benchmark/benchmark_streaming.py \
        --url http://localhost:8000 \
        --model "Qwen/Qwen2.5-0.5B-Instruct" \
        --input-file datasets/normal_prompts.jsonl \
        --max-tokens 64 \
        --output results/streaming_baseline.csv
"""

import argparse
import csv
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

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
# SSE Parser — phân tích Server-Sent Events từ vLLM streaming response
# ==============================================================================
def parse_sse_stream(response: httpx.Response):
    """Yield từng SSE data event từ streaming response.

    vLLM trả về dạng:
        data: {"id":...,"choices":[{"delta":{"content":"token"}}]...}
        data: [DONE]
    """
    buffer = ""
    for chunk in response.iter_text():
        buffer += chunk
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            if line.startswith("data: "):
                data_str = line[6:]
                event, done = parse_data_line(line)
                if done:
                    yield {"__stream_done__": True}
                    return
                if event is not None:
                    yield event


# ==============================================================================
# Benchmark một request
# ==============================================================================
def benchmark_single_request(
    client: httpx.Client,
    url: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    request_id: str,
    timeout: float = 120.0,
    tokenizer=None,
    include_usage: bool = False,
) -> dict:
    """Gửi một streaming request và đo latency.

    ``completion_tokens`` lấy từ usage chunk nếu server hỗ trợ; nếu không,
    tokenizer tùy chọn được dùng để ước tính. Số SSE chunk luôn được lưu riêng
    dưới tên ``output_chunks`` và không bị gọi nhầm là token.
    """

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

    try:
        start = time.perf_counter()
        result["start_time"] = start

        with client.stream(
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

            for event in parse_sse_stream(response):
                if event.get("__stream_done__"):
                    state["stream_done"] = True
                    continue
                content = inspect_event(event, state)
                if content:
                    if not first_token_received:
                        result["first_token_time"] = time.perf_counter()
                        result["ttft"] = result["first_token_time"] - start
                        first_token_received = True
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
        result["e2e_latency"] = result["end_time"] - result["start_time"]
        result["error"] = "timeout"
    except Exception as e:
        result["end_time"] = time.perf_counter()
        result["e2e_latency"] = result["end_time"] - result["start_time"]
        result["error"] = str(e)

    return result


# ==============================================================================
# Load prompts từ JSONL
# ==============================================================================
def load_prompts(filepath: str) -> list[list[dict]]:
    """Load prompts từ file JSONL. Mỗi dòng chứa {"messages": [...]}."""
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
                if not messages:
                    print(f"  Dòng {line_num}: thiếu 'messages', bỏ qua.")
                    continue
                prompts.append(messages)
            except json.JSONDecodeError as e:
                print(f"  Dòng {line_num}: JSON lỗi — {e}")
    return prompts


# ==============================================================================
# Lưu kết quả
# ==============================================================================
FIELDNAMES = [
    "request_id",
    "prompt_chars",
    "prompt_tokens",
    "completion_tokens",
    "output_chunks",
    "token_count_source",
    "start_time",
    "first_token_time",
    "end_time",
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
    """Lưu kết quả ra CSV."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(results)
    print(f"  CSV: {path}")


def save_json(results: list[dict], filepath: str) -> None:
    """Lưu kết quả ra JSON."""
    json_path = Path(filepath).with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"  JSON: {json_path}")


# ==============================================================================
# Main
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Benchmark streaming inference trên vLLM."
    )
    parser.add_argument(
        "--url", default="http://localhost:8000", help="vLLM server URL"
    )
    parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Model name (như hiển thị trong /v1/models)",
    )
    parser.add_argument(
        "--input-file",
        default="datasets/normal_prompts.jsonl",
        help="File JSONL chứa prompts",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=64, help="Max output tokens"
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=0,
        help="Số request (0 = toàn bộ file)",
    )
    parser.add_argument(
        "--output",
        default="results/streaming_baseline.csv",
        help="File CSV đầu ra",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Timeout mỗi request (giây)",
    )
    parser.add_argument(
        "--tokenizer",
        default=None,
        help="Tokenizer HF để đếm/ước tính token; bỏ trống nếu server trả usage.",
    )
    parser.add_argument(
        "--include-usage",
        action="store_true",
        help="Yêu cầu usage chunk cuối stream; version-sensitive.",
    )
    args = parser.parse_args()

    # Load prompts
    prompts = load_prompts(args.input_file)
    if args.num_requests > 0:
        prompts = prompts[: args.num_requests]

    print(f"Benchmark Streaming — {len(prompts)} requests")
    print(f"  Server : {args.url}")
    print(f"  Model  : {args.model}")
    print(f"  Max tok: {args.max_tokens}")
    print(f"  Tokenizer: {args.tokenizer or '(server usage only)'}")

    tokenizer, tokenizer_source = load_tokenizer(args.tokenizer)
    if args.tokenizer and tokenizer is None:
        print("⚠ Không có tokenizer fallback; token metrics có thể là None.")
    print()

    results = []
    with httpx.Client() as client:
        for i, messages in enumerate(prompts):
            req_id = str(uuid.uuid4())[:8]
            print(f"  [{i + 1}/{len(prompts)}] {req_id}...", end=" ", flush=True)

            result = benchmark_single_request(
                client=client,
                url=args.url,
                model=args.model,
                messages=messages,
                max_tokens=args.max_tokens,
                request_id=req_id,
                timeout=args.timeout,
                tokenizer=tokenizer,
                include_usage=args.include_usage,
            )
            results.append(result)

            status = "✓" if result["success"] else "✗"
            print(
                f"{status} TTFT={result['ttft']:.3f}s "
                f"E2E={result['e2e_latency']:.3f}s "
                f"completion_tokens={result['completion_tokens']} "
                f"chunks={result['output_chunks']}"
            )

    # Lưu kết quả
    print()
    print("Lưu kết quả:")
    save_csv(results, args.output)
    save_json(results, args.output)

    # Thống kê tóm tắt
    successful = [r for r in results if r["success"]]
    failed = len(results) - len(successful)
    if successful:
        ttfts = [r["ttft"] for r in successful]
        e2es = [r["e2e_latency"] for r in successful]
        token_values = [
            r["completion_tokens"]
            for r in successful
            if isinstance(r["completion_tokens"], int)
        ]
        total_time = max(r["end_time"] for r in successful) - min(
            r["start_time"] for r in successful
        )

        print()
        print("=== Tóm tắt ===")
        print(f"  Requests   : {len(successful)} ok / {failed} failed")
        print(f"  TTFT mean  : {sum(ttfts)/len(ttfts):.4f}s")
        print(f"  E2E mean   : {sum(e2es)/len(e2es):.4f}s")
        if len(token_values) == len(successful):
            total_tokens = sum(token_values)
            print(f"  Total tok  : {total_tokens}")
            if total_time > 0:
                print(f"  Tok/s      : {total_tokens/total_time:.1f}")
        else:
            print("  Tok/s      : unavailable (server usage/tokenizer chưa có)")
    else:
        print("  Không có request thành công.")


if __name__ == "__main__":
    main()

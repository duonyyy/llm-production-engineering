"""Các tiện ích dùng chung cho benchmark Lab 01.

Mục tiêu của module này là giữ rõ ranh giới giữa:

* prompt_chars: số ký tự của prompt;
* prompt_tokens/completion_tokens: số token do API trả về hoặc tokenizer ước tính;
* output_chunks: số chunk SSE có nội dung, không phải số token.

Nếu server không trả usage và người chạy không cung cấp tokenizer, các metric
theo token sẽ để ``None`` thay vì dùng số chunk SSE làm token giả.
"""

from __future__ import annotations

from typing import Any


def message_chars(messages: list[dict[str, Any]]) -> int:
    """Đếm ký tự nội dung message; đây không phải prompt token count."""

    return sum(len(str(message.get("content", ""))) for message in messages)


def build_payload(
    model: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    include_usage: bool = False,
) -> dict[str, Any]:
    """Tạo payload ổn định cho mọi benchmark client."""

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "temperature": 0.0,
    }
    if include_usage:
        # Server/version không hỗ trợ trường này có thể bỏ qua hoặc trả lỗi.
        # Client có cờ --include-usage để người học chủ động kiểm soát.
        payload["stream_options"] = {"include_usage": True}
    return payload


def new_stream_state(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Khởi tạo state trong khi đọc một SSE stream."""

    return {
        "prompt_chars": message_chars(messages),
        "prompt_tokens_api": None,
        "completion_tokens_api": None,
        "output_chunks": 0,
        "completion_text": "",
        "stream_done": False,
        "finish_reason": None,
    }


def inspect_event(event: dict[str, Any], state: dict[str, Any]) -> str:
    """Cập nhật state từ một OpenAI-compatible SSE event.

    Trả về phần content của event. Một event usage cuối stream có thể không có
    choices và vẫn được xử lý bình thường.
    """

    usage = event.get("usage")
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        if isinstance(prompt_tokens, int):
            state["prompt_tokens_api"] = prompt_tokens
        if isinstance(completion_tokens, int):
            state["completion_tokens_api"] = completion_tokens

    choices = event.get("choices", [])
    if not choices:
        return ""

    choice = choices[0] or {}
    if choice.get("finish_reason") is not None:
        state["finish_reason"] = choice.get("finish_reason")
    delta = choice.get("delta", {}) or {}
    content = delta.get("content", "")
    if not isinstance(content, str):
        return ""
    if content:
        state["output_chunks"] += 1
        state["completion_text"] += content
    return content


def load_tokenizer(tokenizer_name: str | None):
    """Tải tokenizer tùy chọn để có fallback token count minh bạch.

    Tokenizer không bắt buộc: API usage được ưu tiên. Nếu không tải được,
    benchmark vẫn đo latency nhưng token metrics sẽ là ``None``.
    """

    if not tokenizer_name:
        return None, "unavailable"
    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_name,
            trust_remote_code=False,
        )
        return tokenizer, "tokenizer_estimate"
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường/cache
        print(f"⚠ Không tải được tokenizer '{tokenizer_name}': {exc}")
        return None, "unavailable"


def tokenizer_prompt_tokens(tokenizer: Any, messages: list[dict[str, Any]]) -> int | None:
    """Đếm prompt token bằng chat template nếu tokenizer hỗ trợ."""

    if tokenizer is None:
        return None
    try:
        if hasattr(tokenizer, "apply_chat_template"):
            encoded = tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
            )
            return len(encoded)
        text = "\n".join(str(message.get("content", "")) for message in messages)
        return len(tokenizer.encode(text, add_special_tokens=True))
    except Exception:
        return None


def finalize_token_counts(
    state: dict[str, Any],
    messages: list[dict[str, Any]],
    tokenizer: Any = None,
) -> dict[str, Any]:
    """Chọn token count theo thứ tự API usage → tokenizer → unavailable."""

    prompt_tokens = state.get("prompt_tokens_api")
    completion_tokens = state.get("completion_tokens_api")
    used_tokenizer = False

    if prompt_tokens is None:
        prompt_tokens = tokenizer_prompt_tokens(tokenizer, messages)
        if prompt_tokens is not None:
            used_tokenizer = True

    if completion_tokens is None and tokenizer is not None:
        try:
            completion_tokens = len(
                tokenizer.encode(
                    state.get("completion_text", ""),
                    add_special_tokens=False,
                )
            )
            used_tokenizer = True
        except Exception:
            completion_tokens = None

    if prompt_tokens is None or completion_tokens is None:
        source = "unavailable"
    elif used_tokenizer:
        source = "tokenizer_estimate"
    else:
        source = "api_usage"

    state["prompt_tokens"] = prompt_tokens
    state["completion_tokens"] = completion_tokens
    state["token_count_source"] = source
    return state


def approx_tpot(e2e_latency: float, ttft: float, completion_tokens: int | None) -> float | None:
    """Tính TPOT theo công thức chuẩn nếu có completion token count."""

    if completion_tokens is None or completion_tokens <= 1 or ttft <= 0:
        return None
    return (e2e_latency - ttft) / (completion_tokens - 1)


def parse_data_line(line: str) -> tuple[dict[str, Any] | None, bool]:
    """Parse một dòng SSE; trả về (event, done)."""

    import json

    line = line.strip()
    if not line.startswith("data:"):
        return None, False
    data = line[5:].strip()
    if data == "[DONE]":
        return None, True
    try:
        event = json.loads(data)
    except json.JSONDecodeError:
        return None, False
    return event if isinstance(event, dict) else None, False

"""Small, auditable OpenAI-compatible router for the Lab 03 experiments.

It is deliberately not a production gateway. The P/D path follows the
documented vLLM experimental handoff shape: a non-streaming prefill request
returns prompt token IDs, then the decode request receives those IDs through
kv_transfer_params. The connector performs the actual KV movement; this
router never pretends to move tensors itself.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def as_bool(value: Any) -> bool:
    return str(value).lower() in {"1", "true", "yes", "on"}


class WorkerPool:
    """Pedagogical cache-aware score; no claim that it is a framework feature."""

    def __init__(self) -> None:
        self.workers = {
            "prefill-0": {"url": os.getenv("PREFILL_URL", "http://127.0.0.1:8101"), "prefixes": {"X"}, "load": 0},
            "prefill-1": {"url": os.getenv("PREFILL_URL", "http://127.0.0.1:8101"), "prefixes": {"Y"}, "load": 0},
        }

    def choose(self, prefix_key: str | None) -> tuple[str, str]:
        w_cache = float(os.getenv("ROUTER_W_CACHE", "1.0"))
        w_load = float(os.getenv("ROUTER_W_LOAD", "0.25"))
        candidates = []
        for worker_id, worker in self.workers.items():
            cache_score = 1.0 if prefix_key and prefix_key in worker["prefixes"] else 0.0
            score = w_cache * cache_score - w_load * float(worker["load"])
            candidates.append((score, worker_id, worker["url"]))
        _, worker_id, url = max(candidates)
        self.workers[worker_id]["load"] += 1
        return worker_id, url

    def release(self, worker_id: str) -> None:
        self.workers[worker_id]["load"] = max(0, self.workers[worker_id]["load"] - 1)


class Lab03Router:
    def __init__(self, timeout_s: float) -> None:
        self.timeout_s = timeout_s
        self.pool = WorkerPool()
        self.allow_fallback = as_bool(os.getenv("ROUTER_ALLOW_FALLBACK", "false"))

    @staticmethod
    def _extra_body(payload: dict[str, Any]) -> dict[str, Any]:
        value = payload.get("extra_body", {})
        return dict(value) if isinstance(value, dict) else {}

    def _post(self, url: str, payload: dict[str, Any], request_id: str) -> tuple[Any, float, dict[str, str]]:
        encoded = json.dumps(payload).encode("utf-8")
        request = Request(
            url.rstrip("/") + "/v1/chat/completions",
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
            },
        )
        started = now_ms()
        with urlopen(request, timeout=self.timeout_s) as response:
            body = response.read()
            elapsed = now_ms() - started
            headers = {key.lower(): value for key, value in response.headers.items()}
        try:
            decoded: Any = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            decoded = {"raw_body": body.decode("utf-8", errors="replace")}
        return decoded, elapsed, headers

    def _post_stream(self, url: str, payload: dict[str, Any], request_id: str):
        encoded = json.dumps(payload).encode("utf-8")
        request = Request(
            url.rstrip("/") + "/v1/chat/completions",
            data=encoded,
            method="POST",
            headers={"Content-Type": "application/json", "X-Request-ID": request_id},
        )
        return urlopen(request, timeout=self.timeout_s), now_ms()

    @staticmethod
    def _token_ids(prefill_response: Any) -> list[int] | None:
        if not isinstance(prefill_response, dict):
            return None
        direct = prefill_response.get("prompt_token_ids")
        if isinstance(direct, list):
            return direct
        choices = prefill_response.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            nested = choices[0].get("prompt_token_ids")
            if isinstance(nested, list):
                return nested
        return None

    def colocated(self, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        url = os.getenv("COLOCATED_URL", "http://127.0.0.1:8000")
        return self._post(url, payload, request_id)[0]

    def pd(self, payload: dict[str, Any], request_id: str) -> dict[str, Any]:
        prefix_key = payload.get("prefix_key")
        worker_id, prefill_url = self.pool.choose(str(prefix_key) if prefix_key else None)
        started = now_ms()
        try:
            prefill_payload = dict(payload)
            prefill_payload.pop("router_mode", None)
            prefill_payload.pop("prefix_key", None)
            prefill_payload["stream"] = False
            extra = self._extra_body(prefill_payload)
            extra.update({"return_token_ids": True, "kv_transfer_params": {"do_remote_decode": True}})
            prefill_payload["extra_body"] = extra
            prefill_response, prefill_ms, _ = self._post(prefill_url, prefill_payload, request_id)
            token_ids = self._token_ids(prefill_response)
            if token_ids is None:
                raise RuntimeError("prefill response did not contain prompt_token_ids")

            decode_url = os.getenv("DECODE_URL", "http://127.0.0.1:8102")
            decode_payload = dict(payload)
            decode_payload.pop("router_mode", None)
            decode_payload.pop("prefix_key", None)
            decode_extra = self._extra_body(decode_payload)
            decode_extra.update({
                "kv_transfer_params": {"do_remote_prefill": True, "prompt_token_ids": token_ids}
            })
            decode_payload["extra_body"] = decode_extra
            result, decode_ms, response_headers = self._post(decode_url, decode_payload, request_id)
            total_ms = now_ms() - started
            return {
                "response": result,
                "route": "pd",
                "request_id": request_id,
                "prefill_worker_id": worker_id,
                "prefill_ms": round(prefill_ms, 3),
                "decode_ms": round(decode_ms, 3),
                "kv_transfer_ms": None,
                "total_router_ms": round(total_ms, 3),
                "kv_transfer_metric_status": "unavailable-unless-exported-by-worker",
                "upstream_headers": response_headers,
            }
        finally:
            self.pool.release(worker_id)

    def stream_colocated(self, payload: dict[str, Any], request_id: str):
        url = os.getenv("COLOCATED_URL", "http://127.0.0.1:8000")
        return self._post_stream(url, payload, request_id)

    def stream_pd(self, payload: dict[str, Any], request_id: str):
        """Open a streaming decode connection after a completed prefill handoff."""
        prefix_key = payload.get("prefix_key")
        worker_id, prefill_url = self.pool.choose(str(prefix_key) if prefix_key else None)
        try:
            prefill_payload = dict(payload)
            prefill_payload.pop("router_mode", None)
            prefill_payload.pop("prefix_key", None)
            prefill_payload["stream"] = False
            extra = self._extra_body(prefill_payload)
            extra.update({"return_token_ids": True, "kv_transfer_params": {"do_remote_decode": True}})
            prefill_payload["extra_body"] = extra
            prefill_response, prefill_ms, _ = self._post(prefill_url, prefill_payload, request_id)
            token_ids = self._token_ids(prefill_response)
            if token_ids is None:
                raise RuntimeError("prefill response did not contain prompt_token_ids")
            decode_payload = dict(payload)
            decode_payload.pop("router_mode", None)
            decode_payload.pop("prefix_key", None)
            decode_extra = self._extra_body(decode_payload)
            decode_extra.update({"kv_transfer_params": {"do_remote_prefill": True, "prompt_token_ids": token_ids}})
            decode_payload["extra_body"] = decode_extra
            upstream, decode_started = self._post_stream(os.getenv("DECODE_URL", "http://127.0.0.1:8102"), decode_payload, request_id)
            return worker_id, prefill_ms, upstream, decode_started
        except Exception:
            self.pool.release(worker_id)
            raise


class Handler(BaseHTTPRequestHandler):
    router: Lab03Router

    def _json(self, status: int, value: Any, headers: dict[str, str] | None = None) -> None:
        raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for key, value in (headers or {}).items():
            self.send_header(key, str(value))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "lab03-router"})
            return
        if self.path == "/ready":
            self._json(200, {
                "status": "router-ready",
                "prefill_url": os.getenv("PREFILL_URL", "http://127.0.0.1:8101"),
                "decode_url": os.getenv("DECODE_URL", "http://127.0.0.1:8102"),
                "colocated_url": os.getenv("COLOCATED_URL", "http://127.0.0.1:8000"),
                "p_d_probe": "not-performed",
            })
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self._json(404, {"error": "not_found"})
            return
        request_id = self.headers.get("X-Request-ID") or f"lab03-{uuid.uuid4().hex}"
        payload: dict[str, Any] = {}
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 2_000_000:
                raise ValueError("request body too large")
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            mode = self.headers.get("X-Lab03-Mode") or payload.get("router_mode", "colocated")
            if mode not in {"colocated", "pd"}:
                raise ValueError("router_mode must be colocated or pd")
            if mode == "pd":
                if as_bool(payload.get("stream", False)):
                    worker_id, prefill_ms, upstream, decode_started = self.router.stream_pd(payload, request_id)
                    self.send_response(getattr(upstream, "status", 200))
                    self.send_header("Content-Type", upstream.headers.get("Content-Type", "text/event-stream"))
                    self.send_header("X-Lab03-Request-Id", request_id)
                    self.send_header("X-Lab03-Route", "pd")
                    self.send_header("X-Lab03-Prefill-Ms", round(prefill_ms, 3))
                    self.send_header("X-Lab03-Kv-Transfer-Ms", "NA")
                    self.send_header("X-Lab03-Kv-Transfer-Status", "unavailable-unless-exported-by-worker")
                    self.end_headers()
                    try:
                        while True:
                            chunk = upstream.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    finally:
                        upstream.close()
                        self.router.pool.release(worker_id)
                    return
                outcome = self.router.pd(payload, request_id)
                self._json(200, outcome["response"], {
                    "X-Lab03-Request-Id": request_id,
                    "X-Lab03-Route": "pd",
                    "X-Lab03-Prefill-Ms": outcome["prefill_ms"],
                    "X-Lab03-Decode-Ms": outcome["decode_ms"],
                    "X-Lab03-Kv-Transfer-Ms": "NA",
                    "X-Lab03-Kv-Transfer-Status": outcome["kv_transfer_metric_status"],
                })
            else:
                if as_bool(payload.get("stream", False)):
                    upstream, _ = self.router.stream_colocated(payload, request_id)
                    self.send_response(getattr(upstream, "status", 200))
                    self.send_header("Content-Type", upstream.headers.get("Content-Type", "text/event-stream"))
                    self.send_header("X-Lab03-Request-Id", request_id)
                    self.send_header("X-Lab03-Route", "colocated")
                    self.end_headers()
                    try:
                        while True:
                            chunk = upstream.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                            self.wfile.flush()
                    finally:
                        upstream.close()
                    return
                result = self.router.colocated(payload, request_id)
                self._json(200, result, {"X-Lab03-Request-Id": request_id, "X-Lab03-Route": "colocated"})
        except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            requested_pd = self.headers.get("X-Lab03-Mode") == "pd" or payload.get("router_mode") == "pd"
            if self.router.allow_fallback and requested_pd:
                try:
                    fallback = self.router.colocated(payload, request_id)
                    self._json(200, fallback, {
                        "X-Lab03-Request-Id": request_id,
                        "X-Lab03-Route": "colocated-fallback",
                        "X-Lab03-Degradation": "availability-preserved-performance-may-degrade",
                    })
                    return
                except Exception as fallback_exc:  # pragma: no cover - runtime path
                    exc = RuntimeError(f"P/D failed ({exc}); fallback failed ({fallback_exc})")
            self._json(502, {
                "error": "routing_failed",
                "request_id": request_id,
                "message": str(exc),
                "retry_policy": "no blind retry; caller may retry only with an idempotent request ID",
            })

    def log_message(self, format: str, *args: Any) -> None:
        # Do not log prompts, authorization headers, or response bodies.
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab 03 educational P/D router")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--timeout", type=float, default=float(os.getenv("ROUTER_TIMEOUT_S", "45")))
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    Handler.router = Lab03Router(args.timeout)
    print(json.dumps({"service": "lab03-router", "host": args.host, "port": args.port}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

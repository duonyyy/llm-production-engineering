"""Fail-closed, read-only agent runtime with explicit state persistence."""

from __future__ import annotations

import argparse
import json
import queue
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from session_store import SessionStore  # noqa: E402


ALLOWED_TOOLS = {"get_cluster_summary", "get_model_health", "get_recent_metrics"}


class StdioMCPClient:
    """Minimal JSON-RPC stdio client for the MCP 2025-era transport.

    The server is spawned explicitly; there is no shell interpolation. This
    keeps the local lab boundary auditable and avoids token passthrough.
    """

    def __init__(self, command: list[str], timeout_s: float = 10.0) -> None:
        self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.timeout_s = timeout_s
        self.next_id = 1

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("MCP stdio is unavailable")
        request_id = self.next_id
        self.next_id += 1
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.process.stdin.write(json.dumps(message) + "\n")
        self.process.stdin.flush()
        output: queue.Queue[str] = queue.Queue(maxsize=1)

        def read_line() -> None:
            try:
                output.put(self.process.stdout.readline())
            except Exception as exc:  # pragma: no cover - subprocess failure
                output.put(f"__ERROR__{exc}")

        reader = threading.Thread(target=read_line, daemon=True)
        reader.start()
        try:
            line = output.get(timeout=self.timeout_s)
        except queue.Empty as exc:
            raise TimeoutError(f"MCP method timed out: {method}") from exc
        if not line:
            raise RuntimeError("MCP server closed stdout")
        response = json.loads(line)
        if response.get("id") != request_id:
            raise RuntimeError("MCP response ID mismatch")
        if "error" in response:
            raise RuntimeError(str(response["error"]))
        return response.get("result", {})

    def initialize(self) -> dict[str, Any]:
        result = self._request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "lab03-agent", "version": "0.1.0"}})
        if self.process.stdin is not None:
            self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            self.process.stdin.flush()
        return result

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in ALLOWED_TOOLS:
            raise PermissionError(f"tool denied by local allowlist: {name}")
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()


class MockMCPClient:
    """Explicit demo adapter; its output is never labelled live."""

    def initialize(self) -> dict[str, Any]:
        return {"serverInfo": {"name": "mock-mcp-read-only", "version": "demo"}}

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in ALLOWED_TOOLS:
            raise PermissionError(f"tool denied by local allowlist: {name}")
        return {"isError": False, "content": [{"type": "text", "text": json.dumps({"source": "MOCK_DEMO", "tool": name, "arguments": arguments})}]}

    def close(self) -> None:
        return


def choose_tool(task: str) -> str | None:
    lowered = task.lower()
    if any(word in lowered for word in ("health", "ready", "worker")):
        return "get_model_health"
    if any(word in lowered for word in ("cluster", "pod", "node")):
        return "get_cluster_summary"
    if any(word in lowered for word in ("metric", "ttft", "latency", "throughput")):
        return "get_recent_metrics"
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--db", default=str(Path(__file__).parents[1] / "results" / "agent_state.sqlite3"))
    parser.add_argument("--mcp-command", nargs="+", default=None, help="Executable and arguments for the trusted local MCP server")
    parser.add_argument("--mock-mcp", action="store_true")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    session_id = args.session_id or f"session-{uuid.uuid4().hex[:12]}"
    task_id = f"task-{uuid.uuid4().hex[:12]}"
    store = SessionStore(args.db)
    state = store.load_state(session_id)
    store.append_event(session_id, task_id, "task_received", {"task_id": task_id, "session_id": session_id})
    state["audit"].append({"task_id": task_id, "event": "task_received", "at": time.time()})

    client: StdioMCPClient | MockMCPClient | None = None
    tool_calls = 0
    try:
        if args.mock_mcp:
            client = MockMCPClient()
        elif args.mcp_command:
            client = StdioMCPClient(args.mcp_command, args.timeout)
        else:
            raise RuntimeError("No MCP client configured; use --mcp-command or explicit --mock-mcp")
        init = client.initialize()
        store.append_event(session_id, task_id, "mcp_initialized", {"server": init.get("serverInfo", {})})
        selected = choose_tool(args.task)
        observation: dict[str, Any] | None = None
        if selected is not None:
            if selected not in ALLOWED_TOOLS:
                raise PermissionError("tool selection failed closed")
            idempotency_key = f"{task_id}:{selected}"
            if not store.claim_idempotency(session_id, idempotency_key):
                raise RuntimeError("duplicate tool call refused by idempotency guard")
            tool_calls += 1
            store.append_event(session_id, task_id, "tool_call_requested", {"tool": selected, "tool_call_id": idempotency_key, "side_effect": "read-only"})
            observation = client.call(selected, {})
            store.append_event(session_id, task_id, "tool_call_completed", {"tool": selected, "tool_call_id": idempotency_key, "is_error": bool(observation.get("isError"))})
            state["completed_steps"].append({"tool": selected, "task_id": task_id})
            state["short_term_memory"] = [{"tool": selected, "observation": observation}]
        answer = {"status": "completed", "task_id": task_id, "session_id": session_id, "llm_calls": 1, "tool_calls": tool_calls, "answer": "Task completed using only the allowed read-only path.", "observation": observation, "provenance": "MOCK_DEMO" if args.mock_mcp else "mcp-stdio"}
        store.append_event(session_id, task_id, "task_completed", {"llm_calls": 1, "tool_calls": tool_calls})
        store.save_state(session_id, state, "completed")
        print(json.dumps(answer, ensure_ascii=False, indent=2))
    except Exception as exc:
        store.append_event(session_id, task_id, "task_failed", {"error_type": type(exc).__name__, "message": str(exc)})
        state["last_error"] = {"type": type(exc).__name__, "message": str(exc), "task_id": task_id}
        store.save_state(session_id, state, "failed")
        print(json.dumps({"status": "failed_closed", "task_id": task_id, "session_id": session_id, "error": str(exc), "state_preserved": True, "dangerous_fallback": False}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    finally:
        if client is not None:
            client.close()
        store.close()


if __name__ == "__main__":
    main()

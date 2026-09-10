"""Dependency-level static smoke test; it never starts vLLM, FAISS or Prometheus."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    state_dir = ROOT / ".runtime-smoke-test"
    # This fixed, ignored workspace path avoids Windows Temp permission failures
    # in restricted local environments. It is never an evidence directory.
    shutil.rmtree(state_dir, ignore_errors=True)
    try:
        os.environ.update(
            {
                "FINAL_API_TOKEN": "static-test-token",
                "FINAL_ALLOWED_KNOWLEDGE_BASES": "operations-public",
                "FINAL_ALLOWED_SCOPES": "internal",
                "FINAL_STATE_DIR": str(state_dir),
            }
        )
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            assert client.get("/healthz").status_code == 200
            denied = client.post(
                "/v1/chat/completions",
                json={"model": "wrong", "messages": [{"role": "user", "content": "hello"}], "max_tokens": 8, "timeout_ms": 1000, "workload_label": "mixed"},
                headers={"Authorization": "Bearer wrong"},
            )
            assert denied.status_code == 401
            unauthorized_kb = client.post(
                "/v1/chat/completions",
                json={
                    "model": "Qwen/Qwen2.5-0.5B-Instruct",
                    "messages": [{"role": "user", "content": "hello"}],
                    "max_tokens": 8,
                    "timeout_ms": 1000,
                    "workload_label": "mixed",
                    "rag": {"mode": "required", "knowledge_base_id": "not-allowed"},
                },
                headers={"Authorization": "Bearer static-test-token"},
            )
            assert unauthorized_kb.status_code == 403
        print("STATIC: API health, authentication and RAG authorization guards passed; no external service was contacted.")
    finally:
        shutil.rmtree(state_dir, ignore_errors=True)


if __name__ == "__main__":
    main()

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


def _csv_env(name: str) -> frozenset[str]:
    return frozenset(item.strip() for item in os.getenv(name, "").split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Environment-only settings; credentials never live in repository files."""

    api_token: str
    principal: str
    vllm_base_url: str
    model_id: str
    timeout_ms: int
    allowed_knowledge_bases: frozenset[str]
    allowed_scopes: frozenset[str]
    state_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        state_dir = Path(os.getenv("FINAL_STATE_DIR", ROOT_DIR / ".runtime"))
        return cls(
            api_token=os.getenv("FINAL_API_TOKEN", ""),
            principal=os.getenv("FINAL_API_PRINCIPAL", "local-operator"),
            vllm_base_url=os.getenv("FINAL_VLLM_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            model_id=os.getenv("FINAL_MODEL_ID", "Qwen/Qwen2.5-0.5B-Instruct"),
            timeout_ms=int(os.getenv("FINAL_REQUEST_TIMEOUT_MS", "45000")),
            allowed_knowledge_bases=_csv_env("FINAL_ALLOWED_KNOWLEDGE_BASES"),
            allowed_scopes=_csv_env("FINAL_ALLOWED_SCOPES"),
            state_dir=state_dir,
        )

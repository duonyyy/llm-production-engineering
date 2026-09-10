"""Static preflight for local Final Lab source/configuration only."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    for source in sorted((ROOT / "app").glob("*.py")):
        ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    required = [
        ROOT / "app" / "main.py",
        ROOT / "app" / "ingest.py",
        ROOT / "nginx" / "nginx.conf",
        ROOT / "observability" / "prometheus.yml",
        ROOT / "contracts" / "api_contract.yaml",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing required core artifacts: {', '.join(missing)}")
    print("STATIC: Final Lab source preflight passed; no dependency, Docker, GPU, vLLM, RAG or Prometheus runtime was executed.")


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${ROUTER_PORT:-8080}"
export PREFILL_URL="${PREFILL_URL:-http://127.0.0.1:8101}"
export DECODE_URL="${DECODE_URL:-http://127.0.0.1:8102}"
export COLOCATED_URL="${COLOCATED_URL:-http://127.0.0.1:8000}"
export ROUTER_ALLOW_FALLBACK="${ROUTER_ALLOW_FALLBACK:-false}"

exec python3 "${ROOT_DIR}/router/router.py" --host 127.0.0.1 --port "${PORT}"

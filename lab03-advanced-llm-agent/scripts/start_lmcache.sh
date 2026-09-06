#!/usr/bin/env bash
set -euo pipefail

if [ "${LAB03_EXECUTE_LINUX:-no}" != "yes" ]; then
  echo "Refusing LMCache start: set LAB03_EXECUTE_LINUX=yes in the intended Linux environment." >&2
  exit 2
fi
if ! command -v lmcache >/dev/null 2>&1; then
  echo "lmcache CLI is unavailable; install the pinned Linux package first." >&2
  exit 2
fi

exec lmcache server \
  --host "${LMCACHE_HOST:-127.0.0.1}" \
  --port "${LMCACHE_PORT:-5555}" \
  --l1-size-gb "${LMCACHE_L1_SIZE_GB:-1}" \
  --eviction-policy LRU \
  --chunk-size "${LMCACHE_CHUNK_SIZE:-256}"

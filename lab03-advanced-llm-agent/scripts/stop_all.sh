#!/usr/bin/env bash
set -u

for name in "${LAB03_COLOCATED_CONTAINER:-lab03-colocated}" \
            "${LAB03_PREFILL_CONTAINER:-lab03-prefill}" \
            "${LAB03_DECODE_CONTAINER:-lab03-decode}" \
            "${LAB03_LMCACHE_CONTAINER:-lab03-lmcache}"; do
  if command -v docker >/dev/null 2>&1; then
    docker rm -f "${name}" >/dev/null 2>&1 || true
    echo "stopped=${name}"
  fi
done
echo "Router processes must be stopped by their owning terminal or process manager."

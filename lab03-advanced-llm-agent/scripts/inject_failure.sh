#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
if [ "${LAB03_EXECUTE_LINUX:-no}" != "yes" ]; then
  echo "Failure injection is gated. Set LAB03_EXECUTE_LINUX=yes in the intended lab environment." >&2
  exit 2
fi
case "${TARGET}" in
  prefill) docker stop "${LAB03_PREFILL_CONTAINER:-lab03-prefill}" ;;
  decode) docker stop "${LAB03_DECODE_CONTAINER:-lab03-decode}" ;;
  lmcache) docker stop "${LAB03_LMCACHE_CONTAINER:-lab03-lmcache}" ;;
  router) echo "Stop the router process from its owning terminal; no blind process kill is performed." >&2; exit 2 ;;
  transfer) echo "Transfer failure is simulated by taking the configured KV endpoint out of service; stop the LMCache worker only after recording a baseline."; docker stop "${LAB03_LMCACHE_CONTAINER:-lab03-lmcache}" ;;
  *) echo "usage: $0 {prefill|decode|lmcache|router|transfer}" >&2; exit 2 ;;
esac
echo "injected=${TARGET}; record error rate, timeout, recovery and whether recompute preserved availability."

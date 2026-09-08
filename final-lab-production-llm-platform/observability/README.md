# Observability boundary

Prometheus collects numeric telemetry; Grafana visualizes queries from
Prometheus. Structured logs are a separate evidence stream, not a Prometheus
replacement. On the single-node baseline, write JSON logs with rotation and
use a local log viewer or collector only when it is configured and measured.

Targets are Nginx, FastAPI, RAG, agent/MCP and vLLM when each component exposes
an approved metrics endpoint. Do not declare a target healthy merely because
its configuration exists. Preserve correlation IDs but never emit raw prompts,
documents, tokens, authorization headers or tool payloads as labels or logs.

The initial files are a contract, not an installed Prometheus, Grafana or log
collector stack.

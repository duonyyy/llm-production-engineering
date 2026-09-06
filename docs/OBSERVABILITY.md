# Observability and evidence

## 1. Purpose

Observability in this repository is not a dashboard requirement by itself. It is the mechanism that lets a student distinguish a successful request from a fast-looking but incomplete, misrouted, cached, or failed request.

Each result must identify its execution mode:

| Mode | Meaning | What may be claimed |
|---|---|---|
| `STATIC` | Configuration or source was inspected only | Contract and validation result |
| `LOCAL` | Ran on the GTX 3050 4 GB device | Measured local result with command and timestamp |
| `REFERENCE` | Ran in the stated multi-GPU or cluster environment | Measured reference-environment result |

Never present `STATIC` or `REFERENCE` results as measurements from the local GPU.

## 2. Correlation contract

Propagate a request identity through every component that participates in a task:

```text
task_id -> llm_request_id -> router_request_id -> tool_call_id
```

- `task_id`: one user-visible agent task.
- `llm_request_id`: one model inference call.
- `router_request_id`: one routing decision or proxy hop.
- `tool_call_id`: one bounded MCP/tool operation.

Use opaque IDs. Do not put raw prompts, access tokens, authorization headers, or private tool payloads in an ID, metric label, or log field.

## 3. Minimal telemetry by layer

| Layer | Minimum fields | Useful metrics | Do not infer |
|---|---|---|---|
| Inference | model, mode, request ID, start/end, input/output token counts when available, error class | end-to-end latency, TTFT, inter-token latency, throughput, error rate | GPU utilization or KV-cache usage without a runtime metric |
| Router/cache | router ID, backend selected, cache decision, hit/miss reason | cache hit rate, routing distribution, transfer time when emitted | a cache hit merely from prompt similarity |
| Agent | task ID, policy decision, allowed tool name, tool-call result | task success rate, tool-call latency, deny/error rate | tool success when the model text says it succeeded |
| Kubernetes/reference | pod/container identity, replica, resource request/limit, rollout revision | replica health, queueing, restart/error count | local-GPU performance |

`TTFT`, `TPOT`/inter-token latency, and tokens per second must have an explicit calculation and data source. If the runtime does not expose the needed timestamps or token counts, record the metric as `NA` and say why.

## 4. Event and failure semantics

| Event | Required record | Safe behaviour |
|---|---|---|
| Model backend unavailable | request ID, selected backend, error class | return a clear failure; do not silently claim completion |
| Cache/routing unavailable | request ID, routing state, fallback used | use the documented fallback or reject the request |
| Tool policy denial | task ID, requested tool, policy reason | preserve the denial; never retry with broader privilege |
| Partial tool failure | task ID, tool ID, side-effect status | report partial completion and avoid duplicate writes |
| Benchmark interruption | run ID, completed samples, reason | mark run incomplete; do not aggregate it as a full run |

For a configuration update, retain the last known-good configuration until the new configuration is validated. A new configuration that has not passed its gate is not a valid fallback.

## 5. Evidence artifacts

Store sanitized evidence under the lab that produced it, for example:

```text
labXX-*/
  runs/
    2026-09-06-local-smoke/
      metadata.json
      commands.md
      metrics.csv
      summary.md
```

`metadata.json` should include model/version, commit SHA, mode, hardware/environment, configuration hashes, and timestamp. `commands.md` records commands and non-sensitive environment assumptions. `summary.md` separates measurements from interpretation and lists known limitations.

Raw prompts, API keys, private endpoints, and personally identifiable data do not belong in committed evidence.

## 6. Review checklist

Before accepting a performance, reliability, routing, or agent-safety statement, check:

1. Is the run mode stated?
2. Can the statement be joined to a request/run ID and raw metric source?
3. Are units, sample count, aggregation, and failures reported?
4. Is a fallback or rejection path observable?
5. Has sensitive data been excluded from artifacts?

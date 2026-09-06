# LAB 03 Report — Advanced LLM Production

> Quy tắc: thay `TBD` bằng evidence hoặc `NA` kèm lý do. Không điền số ước
> lượng vào cột measured. Tách `FACT`, `INFERENCE`, `RECOMMENDATION`.

## 1. Hardware topology

| Field | Value | Evidence path |
|---|---|---|
| OS/kernel | TBD | preflight log |
| GPU model/count/VRAM | TBD | nvidia-smi |
| GPU topology | TBD | nvidia-smi topo |
| network path | TBD | host/network evidence |
| Docker/Kubernetes | TBD | command output |

## 2. Versions

Record exact image digest, vLLM, LMCache, NIXL, CUDA, driver, Python, Node,
MCP SDK, model revision and tokenizer revision.

## 3. Architecture

Paste the actual colocated/P/D/router/agent diagram and state which edges were
executed versus static design only.

## 4. Baseline

| Mode | Request count | Concurrency | TTFT p50/p95 | TPOT | E2E p95 | Throughput | Status |
|---|---:|---:|---:|---:|---:|---:|---|
| Colocated | TBD | TBD | TBD | TBD | TBD | TBD | TBD |
| P/D | TBD | TBD | TBD | TBD | TBD | TBD | NOT_RUN/MEASURED |

## 5. Workload distributions

Describe prompt/output lengths, shared-prefix ratio, concurrency, warm-up,
repetitions and model sampling settings. Attach raw JSONL and CSV.

## 6. Colocated results

Include TTFT, TPOT/ITL, E2E, queue, GPU memory, KV usage and token metric
provenance. Explain whether the data is `api_usage`, `tokenizer_estimate` or
`unavailable`.

## 7. P/D results

| Workload | Prefill worker | Decode worker | Troute | Tprefill | TKV transfer | Tdecode | Error/fallback |
|---|---|---|---:|---:|---:|---:|---|
| TBD | TBD | TBD | TBD | TBD | measured/NA | TBD | TBD |

## 8. KV transfer analysis

Report connector, transport/backend, bytes/tokens, network path, transfer
failures, accuracy and the evidence that the decode side consumed the intended
KV. Do not infer transfer time from E2E without a documented decomposition.

## 9. Cache reuse analysis

Compare repeated-prefix and random-prefix workloads. Report hit tokens/hit
ratio only from API usage or LMCache logs. Include chunk size, eviction policy,
model revision and stale/incompatible cache policy.

## 10. Failure experiments

| Failure | Error rate | Timeout | Recovery | Retry | Fallback | Availability vs performance |
|---|---:|---:|---:|---:|---|---|
| Prefill down | TBD | TBD | TBD | TBD | TBD | TBD |
| Decode down | TBD | TBD | TBD | TBD | TBD | TBD |
| LMCache down | TBD | TBD | TBD | TBD | TBD | TBD |
| Transfer fail | TBD | TBD | TBD | TBD | recompute/NA | TBD |

## 11. Agent architecture

Record task IDs, session IDs, LLM calls/task, tool calls/task, task latency,
state checkpoints, audit retention and failed-closed behavior.

## 12. MCP security analysis

Describe transport, authentication, authorization, token audience, no
passthrough rule, tool schema validation, RBAC, network policy and secret
boundary. State explicitly that MCP does not replace application authorization.

## 13. Trade-off matrix

Copy the matrix from README and fill it with measured evidence or reasoned
inference. Mark topology-dependent claims.

## 14. Production readiness gate

| Gate | Evidence | Verdict | Missing work / owner |
|---|---|---|---|
| Capacity | TBD | PASS/CONDITIONAL/BLOCKED | TBD |
| SLO | TBD | TBD | TBD |
| P/D topology | TBD | TBD | TBD |
| Cache | TBD | TBD | TBD |
| Security | TBD | TBD | TBD |
| Agent | TBD | TBD | TBD |
| Cost | TBD | TBD | TBD |

## 15. Recommendation

Use the form:

```text
FACT: ...
INFERENCE: ...
RECOMMENDATION: ...
ROLLBACK/STOP CONDITION: ...
```

## 16. Limitations

At minimum discuss single-GPU limitations, Docker/Kubernetes availability,
localhost versus RDMA/NVLink, experimental vLLM P/D, connector compatibility,
cache observability, workload representativeness and absence of production
cost data.

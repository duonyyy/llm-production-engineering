# Final Lab — Production LLM Inference Platform

## Status

This directory is the **project scaffold** for the integrated Final Lab. Its
current delivery status is `DESIGN_ONLY`: contracts, boundaries and evidence
locations are versioned, but no component is wired together and no runtime,
GPU, Kubernetes, P/D or benchmark claim is made here.

The scope is efficient, observable and safe LLM inference deployment. RAG,
vector databases, embedding pipelines and retrieval evaluation are explicitly
out of scope.

## Problem statement

An authenticated internal operator needs to submit an LLM inference request or
inspect its health and performance. The platform must route the request through
the documented inference path, preserve correlation IDs, expose only
allowlisted read-only operational tools, and make degradation visible rather
than fabricate success or metrics.

## Start here

1. Read [contracts/api_contract.yaml](contracts/api_contract.yaml),
   [contracts/metrics_schema.yaml](contracts/metrics_schema.yaml), and
   [contracts/error_policy.md](contracts/error_policy.md).
2. Use the local profile in
   [inference/local-rtx3050-4gb.yaml](inference/local-rtx3050-4gb.yaml) only
   for the GTX 3050 Laptop GPU 4 GB baseline.
3. Implement each boundary in its own directory. Do not import or rewrite a
   Lab 01–03 artifact until its interface is mapped and tested.
4. Record actual runs under `results/` and write the outcome with the template
   in [report/final_report_template.md](report/final_report_template.md).

## Directory map

| Path | Responsibility | Current state |
|---|---|---|
| `contracts/` | API, metrics and failure contracts | versioned design |
| `inference/` | model-server profiles and serving boundary | local profile only |
| `router/` | route selection and fallback contract | design only |
| `agent/` | bounded operator workflow and session boundary | design only |
| `mcp-server/` | read-only tool manifest | versioned design |
| `kubernetes/` | reference deployment composition | design only |
| `benchmarks/` | comparable workload definitions | versioned design |
| `chaos/` | failure-injection matrix | versioned design |
| `datasets/` | non-sensitive workload-data rules | empty by design |
| `results/` | sanitized raw evidence and manifests | empty by design |
| `report/` | reader-facing report template | versioned design |

## Execution boundary

| Path | Allowed claim |
|---|---|
| `LOCAL_MODE` | small-model colocated serving, client benchmark logic, agent state, read-only MCP, static manifests |
| `REFERENCE_MODE` | Linux/Kubernetes/multi-GPU experiments, P/D, KV transfer and failure drills when the stated environment exists |

P/D, LMCache transfer, RDMA/NVLink and live Kubernetes autoscaling remain
`NOT_RUN` until their reference-environment raw evidence exists. See the root
[Final Lab plan](../FINAL_LAB_PLAN.md) and [project status](../docs/PROJECT_STATUS.md).

## Composition rule

This project composes stable interfaces from the three labs; it does not claim
that their source files have been copied or executed together. The integration
order is:

```text
Lab 01 serving contract
  -> Lab 03 router contract
  -> Lab 03 agent/MCP policy
  -> Lab 02 reference deployment contract
  -> benchmark + failure evidence
```

Every request uses the correlation chain:

```text
task_id -> llm_request_id -> router_request_id -> tool_call_id
```

# Final Lab — Production LLM Inference Platform

## Status

This directory is the **project scaffold** for the integrated Final Lab. Its
current delivery status is `DESIGN_ONLY`: contracts, boundaries and evidence
locations are versioned, but no component is wired together and no runtime,
GPU, RAG, P/D or benchmark claim is made here.

The scope is a single-node, production-style LLM platform: Nginx, FastAPI,
RAG, an optional bounded Agent/MCP path, vLLM on the local GPU, and an
observability contract. It is not a high-availability deployment.

## Problem statement

An authenticated internal operator needs to submit an LLM inference request,
ask a grounded question over an approved local knowledge base, or inspect its
health and performance. The platform must route the request through the
documented inference path, preserve correlation IDs, expose only allowlisted
read-only operational tools, and make degradation visible rather than
fabricate success, citations, or metrics.

## Start here

1. Read the canonical [architecture](ARCHITECTURE.md).
2. Read [contracts/api_contract.yaml](contracts/api_contract.yaml),
   [contracts/metrics_schema.yaml](contracts/metrics_schema.yaml), and
   [contracts/error_policy.md](contracts/error_policy.md).
3. Use the local profile in
   [inference/local-rtx3050-4gb.yaml](inference/local-rtx3050-4gb.yaml) only
   for the GTX 3050 Laptop GPU 4 GB baseline.
4. Implement each boundary in its own directory. Do not import or rewrite a
   Lab 01–03 artifact until its interface is mapped and tested.
5. Record actual runs under `results/` and write the outcome with the template
   in [report/final_report_template.md](report/final_report_template.md).

## Directory map

| Path | Responsibility | Current state |
|---|---|---|
| `ARCHITECTURE.md` | canonical component, trust and data-flow design | versioned design |
| `contracts/` | API, metrics and failure contracts | versioned design |
| `inference/` | model-server profiles and serving boundary | local profile only |
| `router/` | route selection and fallback contract | design only |
| `rag/` | local ingestion, retrieval and context boundary | CPU-index design |
| `agent/` | bounded operator workflow and session boundary | design only |
| `mcp-server/` | read-only tool manifest | versioned design |
| `observability/` | Prometheus, Grafana and structured-log contract | versioned design |
| `benchmarks/` | comparable workload definitions | versioned design |
| `chaos/` | failure-injection matrix | versioned design |
| `datasets/` | non-sensitive workload-data rules | empty by design |
| `results/` | sanitized raw evidence and manifests | empty by design |
| `report/` | reader-facing report template | versioned design |

## Execution boundary

| Path | Allowed claim |
|---|---|
| `LOCAL_MODE` | small-model colocated serving, CPU RAG, agent state, read-only MCP, Prometheus/logging integration |
| `REFERENCE_MODE` | multi-GPU P/D, KV transfer and failure drills when the stated environment exists |

P/D, LMCache transfer and RDMA/NVLink remain `NOT_RUN` until their
reference-environment raw evidence exists. See the root [Final Lab
plan](../FINAL_LAB_PLAN.md) and [project status](../docs/PROJECT_STATUS.md).

## Composition rule

This project composes stable interfaces from the three labs; it does not claim
that their source files have been copied or executed together. The integration
order is:

```text
Lab 01 serving contract
  -> Lab 03 router contract
  -> RAG context contract
  -> Lab 03 agent/MCP policy
  -> local observability contract
  -> benchmark + failure evidence
```

Every task uses a traceable correlation graph:

```text
task_id
  ├-> retrieval_id (when RAG is requested)
  ├-> llm_request_id -> router_request_id
  └-> tool_call_id (when an MCP tool is requested)
```

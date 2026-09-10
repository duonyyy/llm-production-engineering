# Final Lab — Production LLM Inference Platform

## Status

This directory contains the **Core single-node implementation** for the
integrated Final Lab. FastAPI, the vLLM HTTP client, CPU FAISS ingestion and
retrieval, bounded read-only operations, SQLite audit state, Nginx and
Prometheus configuration are versioned. The runtime status remains `NOT_RUN`:
no GPU, vLLM, embedding download, RAG index, Nginx, Prometheus or benchmark
result is claimed by this repository change.

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
4. Run `python scripts/preflight.py` and `python scripts/smoke_test.py` for
   the source-only `STATIC` gates.
5. Follow [Local run](#local-run) to create a virtual environment, configure
   authentication, start Lab 01 vLLM, build an approved local index and start
   the API.
6. Record actual runs under `results/` and write the outcome with the template
   in [report/final_report_template.md](report/final_report_template.md).

## Directory map

| Path | Responsibility | Current state |
|---|---|---|
| `app/` | FastAPI, vLLM client, RAG indexer/retriever, audit and metrics | implementation; runtime `NOT_RUN` |
| `nginx/` | local reverse-proxy configuration | implementation; runtime `NOT_RUN` |
| `contracts/` | API, metrics and failure contracts | versioned implementation contract |
| `inference/` | model-server profiles and serving boundary | local profile only |
| `router/` | colocated route selection and vLLM client | implementation; runtime `NOT_RUN` |
| `rag/` | local ingestion, retrieval and context boundary | implementation contract |
| `agent/` | bounded operator workflow and SQLite audit boundary | implementation contract |
| `mcp-server/` | read-only tool manifest | versioned allowlist |
| `observability/` | Prometheus config and structured-log boundary | implementation; runtime `NOT_RUN` |
| `benchmarks/` | comparable workload definitions | versioned design |
| `chaos/` | failure-injection matrix | versioned design |
| `datasets/` | non-sensitive workload-data rules | empty by design |
| `results/` | sanitized raw evidence and manifests | empty by design |
| `report/` | reader-facing report template | versioned design |

## Execution boundary

| Path | Allowed claim |
|---|---|
| `LOCAL_MODE` | small-model colocated serving, CPU RAG, agent state, read-only MCP, Prometheus/logging integration |
| `REFERENCE_MODE` | **Advanced Track only:** multi-GPU P/D, KV transfer and failure drills when the stated environment exists |

P/D, LMCache transfer and RDMA/NVLink are Advanced Track work, never a core
completion condition. They remain `NOT_RUN` until reference-environment raw
evidence exists. See the root [Advanced Track](../ADVANCED_TRACK.md), [Final
Lab plan](../FINAL_LAB_PLAN.md), and [project status](../docs/PROJECT_STATUS.md).

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

## Local run

The local path is deliberately conservative. It starts a small-model vLLM
server from Lab 01 separately, then this application proxies only the
OpenAI-compatible HTTP boundary. Do not add vLLM itself to this Python
environment or use this guide to claim a Docker/GPU result before collecting
the required Lab 01 evidence.

```powershell
cd final-lab-production-llm-platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Set FINAL_API_TOKEN in .env, then export it into the active shell.
$env:FINAL_API_TOKEN = "your-local-secret"
$env:FINAL_ALLOWED_KNOWLEDGE_BASES = "operations-public"
$env:FINAL_ALLOWED_SCOPES = "internal"
python scripts/preflight.py
uvicorn app.main:app --host 127.0.0.1 --port 8081
```

The application does not load `.env` automatically, so a secret is never read
implicitly from a file. Use a trusted shell/secret manager to set it. Start
the Lab 01 vLLM server separately at `FINAL_VLLM_BASE_URL`; `/readyz` remains
503 until authentication is configured and `/v1/models` is reachable.

To index approved non-sensitive `.txt` or `.md` documents, choose the
embedding model and chunking policy after corpus/license inspection. Example
values below are placeholders, not a tested recommendation:

```powershell
$env:FINAL_RAG_EMBEDDING_MODEL = "<reviewed-embedding-model>"
python -m app.ingest --source-dir <approved-doc-folder> --knowledge-base-id operations-public --scope internal --embedding-model $env:FINAL_RAG_EMBEDDING_MODEL --chunk-size <chosen-size> --chunk-overlap <chosen-overlap>
```

Requests require `Authorization: Bearer <FINAL_API_TOKEN>`. A RAG request that
lacks an allowed KB, index, model, scope or evidence returns
`insufficient_evidence`; it does not reach vLLM. The operations API exposes
only `get_model_health` and `get_recent_metrics`, requires an idempotency key,
and records redacted audit metadata in local SQLite. These two operations are
local read-only adapters that enforce the MCP tool manifest; connecting them to
an external MCP stdio server remains a Lab 03 integration task, not a claim
that a remote MCP server is running.

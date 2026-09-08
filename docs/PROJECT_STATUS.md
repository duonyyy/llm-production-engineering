# Project status and execution modes

## Status vocabulary

| Label | Meaning |
| --- | --- |
| `MEASURED` | Raw observations exist and include the required environment/workload evidence. |
| `STATIC_VALIDATED` | Source, schema, manifest or parser checks pass; no live service claim follows. |
| `DESIGN_ONLY` | Architecture or experiment design exists but was not executed. |
| `NOT_RUN` | The required runtime or hardware was unavailable. |
| `NA` | A metric is unavailable for this result; it is not zero and not estimated. |

## Active hardware profile

| Field | Current scope |
| --- | --- |
| GPU | NVIDIA RTX 3050 Laptop GPU |
| VRAM | 4 GB |
| local model profile | `Qwen/Qwen2.5-0.5B-Instruct` |
| colocated context limit | 2048 by default for the local profile |
| local concurrency | intentionally low; measure before increasing |
| supported local learning path | colocated inference, client benchmark logic, agent state and read-only MCP |

## Execution modes

### `LOCAL_MODE`

Use this mode for the current device. It can validate client logic, source
contracts, a small colocated inference server when Docker is available, agent
state and read-only MCP behavior.

It cannot prove multi-GPU scheduling, P/D performance, NIXL transport,
LMCache fleet behavior, RDMA/NVLink characteristics or cluster autoscaling.

### `REFERENCE_MODE`

Use this mode only on Linux with the required Docker, NVIDIA runtime, live
Kubernetes environment and, for P/D, two compatible GPUs. Version-sensitive
connectors and transports must be revalidated immediately before execution.

## Current release stance

This repository is educational and experimental. It is not a production
service, does not contain a production deployment and does not carry a
production SLO guarantee. A passing static check or a successful demo request
does not change that stance.

## Final Lab scaffold status

`final-lab-production-llm-platform/` contains the versioned directory
structure, contracts, local hardware profile, CPU RAG/observability boundaries,
benchmark/failure matrices and report template for the integrated Final Lab.
This is `DESIGN_ONLY`: it has no integrated runtime, knowledge-base/index,
benchmark output, Prometheus/Grafana stack or P/D measurement. Runtime claims
remain `NOT_RUN` until the required gate and raw evidence exist.

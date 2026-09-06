# llm-production-engineering

Hands-on labs for building, measuring and operating LLM inference systems.
The repository is structured as an evidence-first learning path: a diagram,
manifest or configuration is never presented as a measured production result.

## What this repository covers

```text
Lab 01: single-node inference fundamentals
    ↓
Lab 02: Kubernetes deployment and observability
    ↓
Lab 03: KV architecture, P/D reference, agent state and MCP
    ↓
Final Lab: one integrated LLM Operations Copilot
```

| Module | Focus | Current execution boundary |
| --- | --- | --- |
| [Lab 01](lab01-vllm-inference/README.md) | vLLM, streaming, KV cache, benchmark methodology | local colocated profile |
| [Lab 02](lab02-kubernetes-llm/README.md) | Kubernetes, monitoring, RBAC, recovery | manifests plus live-cluster path |
| [Lab 03](lab03-advanced-llm-agent/README.md) | LMCache, P/D architecture, agent runtime, MCP | local agent/MCP plus two-GPU reference path |
| [Final Lab plan](FINAL_LAB_PLAN.md) | integrated Production LLM Operations Copilot | design and staged implementation plan |

## Current scope and non-claims

The active local profile is an NVIDIA RTX 3050 Laptop GPU with 4 GB VRAM. It
is appropriate for a small colocated model and low-concurrency experiments. It
does **not** establish two-GPU P/D, LMCache/NIXL transport, RDMA/NVLink,
production autoscaling or live Kubernetes performance.

The project status, execution modes and evidence rules are documented in
[Project status](docs/PROJECT_STATUS.md). Do not relabel `NOT_RUN`, `NA`,
static validation or simulation output as a benchmark result.

## Start here

1. Read [Architecture](docs/ARCHITECTURE.md) to understand the data-plane,
   control-plane, agent-plane and evidence boundaries.
2. Follow [Local run](docs/LOCAL_RUN.md) for the supported hardware profile.
3. Use [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md) before collecting
   numbers.
4. Use [Testing gates](docs/TESTING.md) and [Security boundary](docs/SECURITY.md)
   before reporting a lab as validated.

## Documentation map

| Document | Purpose |
| --- | --- |
| [Documentation index](docs/README.md) | navigation and reader paths |
| [Architecture](docs/ARCHITECTURE.md) | ownership, interfaces and failure semantics |
| [Project status](docs/PROJECT_STATUS.md) | hardware-aware claim boundary |
| [Local run](docs/LOCAL_RUN.md) | supported local workflow and stop conditions |
| [Experiment protocol](docs/EXPERIMENT_PROTOCOL.md) | reproducible benchmark and evidence contract |
| [Observability](docs/OBSERVABILITY.md) | metrics, logs and correlation IDs |
| [Testing](docs/TESTING.md) | layered verification gates |
| [Security](docs/SECURITY.md) | secrets, RBAC, MCP and tool boundaries |
| [Architecture decisions](docs/DECISIONS.md) | current project decisions and reasons |
| [Roadmap](ROADMAP.md) | planned work and explicit prerequisites |

## Repository layout

```text
.
├── docs/                         # cross-lab documentation foundation
├── lab01-vllm-inference/         # serving and benchmarking fundamentals
├── lab02-kubernetes-llm/         # cluster delivery and observability
├── lab03-advanced-llm-agent/     # KV/P-D, agent state and MCP
├── FINAL_LAB_PLAN.md             # integrated-capstone plan
├── ROADMAP.md                    # delivery sequence
├── SECURITY.md                   # vulnerability and secret-handling policy
└── CONTRIBUTING.md               # contribution and evidence rules
```

## Design principles

- Establish a colocated baseline before an optimization claim.
- Treat raw measurements, environment snapshots and workload definitions as
  deliverables.
- Keep the serving data plane independent from management and documentation
  tooling where possible.
- Fail closed for agent tools and authorization boundaries.
- Prefer last-known-good configuration and explicit rollback over silent
  fallback.
- Keep hardware-specific defaults local to their evidence; do not generalize
  them to other GPUs or topologies.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding an experiment or changing
a contract. Never commit credentials, local model caches, raw request data or
runtime state. Report security-sensitive issues using the process in
[SECURITY.md](SECURITY.md).

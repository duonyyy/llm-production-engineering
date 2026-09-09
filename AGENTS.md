# Repository instructions for coding agents

## Mission and scope

This repository is an educational LLM production-engineering lab suite. It contains three focused labs and an integrated Final Lab plan. Improve the requested lab or shared documentation without silently turning a design exercise, static review, or reference topology into a local production claim.

The local device is a GTX 3050 Laptop GPU with 4 GB VRAM. It is suitable for small-model smoke tests and configuration validation. Kubernetes, multi-GPU, and prefill/decode (P/D) disaggregation work require a separate reference environment unless current evidence proves otherwise.

Read [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md), [docs/LOCAL_RUN.md](docs/LOCAL_RUN.md), and the relevant lab README before changing runtime configuration or reporting a result.

## Source-of-truth order

When sources disagree, use this priority order:

1. Current source/configuration and a verified command result.
2. Current acceptance gates and raw run artifacts.
3. Lab README and shared documentation.
4. Historical reports, benchmark CSVs, or prose summaries.

Do not repeat a metric, capability, or readiness claim solely because it appears in an old report. Re-check the current artifact, environment, and gate.

## Evidence and claim labels

Label every meaningful operational result with exactly one execution mode:

| Label | Meaning |
|---|---|
| `STATIC` | source/configuration/parser inspection only |
| `LOCAL` | command ran on the stated GTX 3050 4 GB local machine |
| `REFERENCE` | command ran in the named cluster, multi-GPU, or other reference environment |

Use `NOT_RUN` for a required gate that was not executed and `NA` for a metric that cannot be calculated from available telemetry. Never estimate missing latency, throughput, cache-hit, GPU, or token metrics.

For a measured claim, retain the command, timestamp, model/version, configuration, workload, sample count, units, aggregation rule, error count, and sanitized raw output. See [docs/EXPERIMENT_PROTOCOL.md](docs/EXPERIMENT_PROTOCOL.md) and [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md).

## Lab boundaries

| Lab | Primary concern | Do not assume |
|---|---|---|
| Lab 01 | local vLLM inference and benchmark provenance | that static config proves a Docker/GPU runtime |
| Lab 02 | **Advanced:** Kubernetes/routing/cache topology | that a laptop validates a distributed deployment |
| Lab 03 | agent/MCP core workflow; **Advanced:** P/D reference concepts | that model output grants a tool authority |
| Final Lab | single-node inference, RAG, observability and agent contracts | that the scaffold or a local demo is an end-to-end benchmark |

Keep lab-specific changes inside their lab unless an interface shared by multiple labs actually changes. If a cross-lab contract changes, update the relevant shared document and [FINAL_LAB_PLAN.md](FINAL_LAB_PLAN.md).

## Safe implementation rules

- Inspect the working tree before editing. Preserve user-created, untracked, and unrelated changes.
- Prefer narrow, reversible changes. Do not replace a canonical lab with a new demo directory.
- Do not add model weights, caches, virtual environments, large generated output, credentials, kubeconfigs, or raw sensitive prompts to Git.
- Do not loosen a GPU-memory, timeout, security, or fallback setting just to make a command appear successful; explain the trade-off and update the contract.
- Use existing scripts/configuration when available. Do not invent command output or pretend unavailable Docker, GPU, API, or cluster checks passed.
- Keep documentation synchronized with any changed interface, hardware assumption, benchmark protocol, failure mode, metric, or security boundary.

## Agent, tool, and security boundary

Treat model output and external tool payloads as untrusted. A valid tool call needs an explicit allowlisted tool, schema-validated arguments, bounded execution, and an authorization decision. Default deny.

Never log or commit secrets, authorization headers, private endpoints, raw sensitive prompts, or tool payloads. Keep correlation IDs opaque and use the chain documented in [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md). For deployment and MCP controls, follow [docs/SECURITY.md](docs/SECURITY.md).

## Validation and handoff

Use the smallest applicable gate from [docs/TESTING.md](docs/TESTING.md), then report what passed and what was not run. Static checks are valuable but must be described as static checks.

Before committing:

1. Review the diff and confirm only intended files are staged.
2. Run formatting/link/parser/test checks appropriate to the change.
3. Update status, evidence, limits, and rollback/failure notes where applicable.
4. In the handoff, lead with the outcome, list validation, and state remaining unrun runtime gates.

Use explicit `git add <paths>` rather than broad staging. Do not commit unrelated user files.

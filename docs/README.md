# Documentation index

This documentation is the cross-lab operating manual. Lab-specific commands,
versions and reports remain inside each lab folder; this directory records the
shared contracts that make the labs comparable.

## Reader paths

| If you need to… | Read this first |
| --- | --- |
| understand the system shape | [Architecture](ARCHITECTURE.md) |
| run safely on the current machine | [Project status](PROJECT_STATUS.md), then [Local run](LOCAL_RUN.md) |
| collect benchmark results | [Experiment protocol](EXPERIMENT_PROTOCOL.md) |
| inspect metrics or traces | [Observability](OBSERVABILITY.md) |
| validate a change | [Testing](TESTING.md) |
| add an MCP tool or Kubernetes permission | [Security](SECURITY.md) |
| understand a trade-off | [Architecture decisions](DECISIONS.md) |
| make an agent-led change | [Agent instructions](../AGENTS.md), then [Contributing](../CONTRIBUTING.md) |
| implement the Final Lab | [Final Lab scaffold](../final-lab-production-llm-platform/README.md) |

## Documentation contract

Every document that makes an operational claim should identify:

1. **Scope** — the exact model, hardware, topology and version.
2. **Status** — measured, static-validated, design-only, `NOT_RUN` or `NA`.
3. **Evidence** — raw result, command output, manifest, source file or log.
4. **Limit** — what the evidence does not establish.
5. **Rollback or stop condition** — when an experiment must stop or a change
   must be reverted.

## Sources and provenance

The documentation information architecture was independently designed after
studying the public [Aurora WAF repository](https://github.com/phucle996/aurora-waf):
clear scope statements, a document index, architecture ownership, local-run
contracts, testing gates, observability and security are useful patterns. No
Aurora source code or prose is copied into this repository.

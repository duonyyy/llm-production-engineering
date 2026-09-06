# Contributing

This repository values reproducible learning artifacts over impressive but unverified claims. Keep changes narrow, reviewable, and traceable to the relevant lab.

## Before opening a change

1. Read the relevant lab README and the shared [documentation contract](docs/README.md).
2. State whether the change is `STATIC`, `LOCAL`, or `REFERENCE` evidence.
3. Preserve the GTX 3050 4 GB local scope; do not label a reference topology as locally measured.
4. Avoid adding model weights, caches, credentials, notebooks outputs with private data, or large generated artifacts.

## What a good contribution contains

- a focused purpose and affected lab(s);
- configuration and hardware/environment assumptions;
- commands or tests actually run, plus their result;
- a clear note for unrun gates and known limits;
- updated documentation when an interface, dependency, metric, failure path, or security boundary changes.

For performance claims, include the model version, prompt/workload, decoding configuration, concurrency, warm-up policy, sample count, aggregation, units, and execution mode. A single manually observed response is a smoke test, not a benchmark.

## Validation

At minimum, run the checks that are available to the changed artifact and report the result. Start with the gates in [docs/TESTING.md](docs/TESTING.md). Do not “fix” an unavailable Docker, GPU, cluster, or API environment by fabricating output; record the missing gate instead.

## Security and agent changes

Changes to tools, MCP configuration, Kubernetes permissions, secret handling, routing fallbacks, or external actions must update [docs/SECURITY.md](docs/SECURITY.md) and include a negative/denial test where applicable.

## Commit hygiene

Do not stage unrelated working-tree files. Use a descriptive commit message, such as `docs: define final-lab evidence contract` or `lab03: add denied-tool policy test`.

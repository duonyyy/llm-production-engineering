# Roadmap

The roadmap orders learning and validation work. It is not a promise of production readiness or a schedule.

| Phase | Outcome | Entry condition | Completion evidence |
|---|---|---|---|
| 1. Local foundation | Reliable small-model serving path on the GTX 3050 4 GB profile | Lab 01 configuration and dependencies understood | bounded local smoke or an explicit unrun gate |
| 2. Routing contract | Cache/routing decisions and fallbacks are inspectable | local serving contract exists | static/unit checks and, if available, live routing telemetry |
| 3. RAG boundary | CPU retrieval adds authorized, versioned evidence before vLLM generation | corpus and access-scope contract are defined | retrieval/abstention paths and sanitized evidence matrix |
| 4. Agent boundary | Tool access is capability-scoped and observable | routing/inference and retrieval IDs are defined | success and denial paths tested with sanitized logs |
| 5. Final Lab composition | One single-node problem joins serving, RAG, observability and agent policy | interfaces and failure contracts are documented | integrated evidence matrix and rollback/failure semantics |
| 6. Advanced track (optional) | Kubernetes or P/D assumptions are exercised only in their proper environment | required cluster or multi-GPU hardware | `REFERENCE` telemetry, benchmark protocol, and failure drill |

## Next practical work

- Keep each lab README aligned with its current runnable state and prerequisites.
- Add sanitized `runs/` evidence only after an actual command executes.
- Define the Final Lab’s end-to-end workload, acceptance matrix, and failure injection cases before measuring it.
- Start the [Advanced Track](ADVANCED_TRACK.md) only after the core path; use a separate reference environment for Kubernetes or multi-GPU P/D claims.

The Final Lab plan is in [FINAL_LAB_PLAN.md](FINAL_LAB_PLAN.md). Current, intentionally conservative claim status is in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

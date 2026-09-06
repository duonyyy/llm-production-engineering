# Roadmap

The roadmap orders learning and validation work. It is not a promise of production readiness or a schedule.

| Phase | Outcome | Entry condition | Completion evidence |
|---|---|---|---|
| 1. Local foundation | Reliable small-model serving path on the GTX 3050 4 GB profile | Lab 01 configuration and dependencies understood | bounded local smoke or an explicit unrun gate |
| 2. Routing contract | Cache/routing decisions and fallbacks are inspectable | local serving contract exists | static/unit checks and, if available, live routing telemetry |
| 3. Agent boundary | Tool access is capability-scoped and observable | routing/inference request IDs are defined | success and denial paths tested with sanitized logs |
| 4. Final Lab composition | One end-to-end problem joins serving, routing/cache, and agent policy | Labs 01–03 interfaces documented | integrated evidence matrix and rollback/failure semantics |
| 5. Reference topology | Cluster/P-D assumptions are exercised in their proper environment | access to the required hardware/cluster | deployment revision, telemetry, benchmark protocol, and failure drill |

## Next practical work

- Keep each lab README aligned with its current runnable state and prerequisites.
- Add sanitized `runs/` evidence only after an actual command executes.
- Define the Final Lab’s end-to-end workload, acceptance matrix, and failure injection cases before measuring it.
- Use a separate reference environment for multi-GPU, Kubernetes, or prefill/decode claims.

The Final Lab plan is in [FINAL_LAB_PLAN.md](FINAL_LAB_PLAN.md). Current, intentionally conservative claim status is in [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

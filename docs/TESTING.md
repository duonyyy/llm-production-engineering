# Testing and acceptance gates

## 1. Rule of evidence

A green static check proves only the checked contract. It does not prove a GPU runtime, Kubernetes deployment, P/D disaggregation, cache transfer, or agent integration. Every report must state the highest gate actually passed.

## 2. Layered gates

| Gate | What it validates | Typical command or evidence | Current portability |
|---|---|---|---|
| T0 — documentation | links, stated scope, command prerequisites, claim labels | Markdown review and `git diff --check` | local |
| T1 — syntax/config | Python syntax, JSON/YAML shape, shell/Compose structure | parser/compile checks | local |
| T2 — unit/mock | pure logic, policy denial, retry/fallback paths | deterministic tests with mocks | local |
| T3 — CLI/service smoke | a real local component accepts a bounded request | captured request/result and logs | hardware/dependency dependent |
| T4 — GPU runtime | model server loads and generates on the GTX 3050 4 GB profile | command, environment, metrics, errors | local GPU dependent |
| T5 — reference topology | Kubernetes, multi-GPU, or P/D workflow behaves end-to-end | deployment revision and telemetry | reference environment only |
| T6 — failure drill | declared failures reject or recover as designed | injected failure and observable result | environment dependent |

## 3. Minimum acceptance by lab

| Area | Minimum before calling it complete | Stronger evidence |
|---|---|---|
| Lab 01 local serving | T0–T2 and a stated hardware profile | T3/T4 smoke with measured latency and errors |
| Lab 02 routing/cache | T0–T2 with explicit cache and fallback contracts | live T3/T5 routing distribution and cache telemetry |
| Lab 03 agent/MCP | T0–T2 including an authorization-denial test | real but sandboxed T3 call with correlation IDs |
| Final Lab | single-node inference, RAG, observability and agent contracts plus an evidence matrix | local T3 smoke; T5/T6 only for the separate P/D reference path and failure drill |

## 4. Safe local validation baseline

Run commands from the repository root. Adjust paths when a lab adds its own test runner.

```powershell
git diff --check
Get-ChildItem -Recurse -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
Get-ChildItem -Recurse -Filter *.json | ForEach-Object { Get-Content -Raw $_.FullName | ConvertFrom-Json | Out-Null }
```

For YAML, use the parser bundled with the lab environment; do not treat a file extension check as YAML validation. For Docker, Kubernetes, vLLM, and P/D experiments, follow the prerequisites and mode labels in [LOCAL_RUN.md](LOCAL_RUN.md).

## 5. Test design requirements

- Test a successful request and at least one expected failure per boundary.
- Mock external services in T2; never make a unit test depend on a paid API or a live cluster.
- Ensure test data contains no secrets or sensitive prompts.
- Make timeouts bounded and report timeout behaviour.
- Keep an agent authorization-denial test separate from tool success tests.
- For benchmark comparisons, hold model, prompt set, decoding settings, concurrency, warm-up policy, and aggregation rule constant unless the changed variable is the experiment.

## 6. Reporting an incomplete gate

Use a direct statement such as: `T2 passed locally; T4 was not run because Docker/GPU runtime was unavailable.` This is useful evidence, not a failure to document. Do not replace missing runtime data with estimates.

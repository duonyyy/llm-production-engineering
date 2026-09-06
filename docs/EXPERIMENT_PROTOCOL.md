# Experiment protocol

## Objective

Experiments answer a bounded question such as: “Does prefix reuse reduce TTFT
for this model, workload, cache state and hardware profile?” They do not answer
whether an optimization is universally faster.

## Pre-run contract

Record before execution:

| Category | Required record |
| --- | --- |
| environment | OS, GPU model/count/VRAM, driver, CUDA, Docker/Kubernetes state |
| serving | model ID/revision, image/package versions, full server config |
| workload | dataset hash/path, prompt/output distribution, concurrency, repetitions, warm-up |
| metrics | TTFT, TPOT/ITL, E2E, errors, token provenance, queue/KV/transfer metrics if available |
| hypothesis | expected mechanism, risk and falsification condition |

## Run sequence

1. Establish a health and correctness baseline.
2. Capture an environment snapshot before load.
3. Warm up using the documented policy.
4. Run one immutable workload/configuration combination.
5. Capture raw request rows and telemetry after the run.
6. Repeat only after recording what changed.
7. Summarize measured results separately from inference.

## Comparison rules

For colocated versus P/D, cache on versus off, or route A versus B, keep these
constant unless the experiment explicitly studies them:

- model and revision;
- prompt set and order;
- output limit and sampling parameters;
- request count and concurrency;
- warm-up procedure;
- hardware and server version.

## Metric rules

| Metric | Valid only when |
| --- | --- |
| TTFT | timestamp from request start to the first generated token/event is recorded |
| TPOT/ITL | generated-token timing and token count provenance exist |
| throughput | time window, completed request count and token source are known |
| cache hit | API usage or cache telemetry reports it; prompt similarity alone is insufficient |
| KV transfer time | connector/worker instrumentation reports it; successful response does not mean zero transfer cost |

## Result labels

Use the status vocabulary in [Project status](PROJECT_STATUS.md). A report must
include this shape:

```text
FACT: observed raw metric or validation output
INFERENCE: likely mechanism consistent with the evidence
RECOMMENDATION: scoped next action
LIMITATION: hardware, workload, topology or missing data boundary
```

## Required artifacts

```text
results/<run-id>/
├── environment.md
├── config.json-or-yaml
├── workload-reference.md
├── raw_requests.csv
├── metrics_before.txt
├── metrics_after.txt
├── server.log
└── summary.md
```

Do not overwrite a prior run. If a run is intentionally discarded, preserve a
small note explaining why it is invalid instead of silently deleting evidence.

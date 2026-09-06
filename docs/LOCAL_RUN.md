# Local run guide

## Before starting

The current profile is Windows with an RTX 3050 Laptop GPU and 4 GB VRAM.
Treat it as a small colocated-learning environment. Do not bypass a script's
hardware or Linux gate just to obtain a result.

Read the lab-specific environment contracts first:

- [Lab 01 environment](../lab01-vllm-inference/ENVIRONMENT.md)
- [Lab 02 environment](../lab02-kubernetes-llm/ENVIRONMENT.md)
- [Lab 03 hardware scope](../lab03-advanced-llm-agent/README.md)

## Static validation path

This path is valid even when Docker, WSL or a Kubernetes API is unavailable.
Run from the repository root in PowerShell:

```powershell
python -c "import ast, pathlib; [ast.parse(p.read_text(encoding='utf-8')) for p in pathlib.Path('lab03-advanced-llm-agent').rglob('*.py')]; print('Lab 03 Python syntax OK')"
python lab03-advanced-llm-agent/benchmark/benchmark_pd.py --mode design
python lab03-advanced-llm-agent/agent/agent_runtime.py --task "check model health" --mock-mcp
```

Generated runtime files belong under a results directory and must not be
committed as measured evidence unless their full run metadata is present.

## Colocated inference path

Only run this path when the Docker daemon and NVIDIA container runtime work:

```text
lab01-vllm-inference/scripts/check_gpu.sh
lab01-vllm-inference/scripts/start_vllm.sh
lab01-vllm-inference/scripts/collect_run_metadata.sh
```

The exact command is version and hardware sensitive. Preserve the server
configuration, model revision, `/v1/models` response, metrics snapshots and
raw benchmark rows before judging performance.

## Kubernetes path

Lab 02 uses a real Kubernetes API only when `kubectl get nodes` succeeds.
Until then, YAML/schema checks are valuable but must be labelled
`STATIC_VALIDATED`. Do not run destructive cleanup or install scripts against a
cluster you have not identified.

## P/D and LMCache path

The Lab 03 P/D scripts require a Linux environment and at least two compatible
NVIDIA GPUs. The local RTX 3050 profile must stop before those commands and
write `NOT_RUN` rather than a simulated latency result.

## Stop conditions

Stop an experiment when any of the following occurs:

- GPU OOM, repeated worker crash or unexplained model mismatch;
- Docker or Kubernetes points to an unintended environment;
- request IDs or raw output cannot be captured;
- the workload/model/config changed mid-run;
- credentials would need to be placed in the repository;
- a failure test could affect resources outside this lab namespace.

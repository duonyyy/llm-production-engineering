# Lab 02 — Environment and execution boundary

> **Advanced Track (optional):** không cần chạy Lab 02 để hoàn thành Core
> single-node path. Manifest-only trên laptop là `STATIC`, không phải cluster
> deployment; xem [Advanced Track](../ADVANCED_TRACK.md).

## Hardware profile supplied by the user

- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, **4GB VRAM**.
- Lab 1 profile reused: `Qwen/Qwen2.5-0.5B-Instruct`, `MAX_MODEL_LEN=4096`, `GPU_MEMORY_UTILIZATION=0.80`.
- Lab 1 evidence says Docker daemon was unavailable at the last check. This Lab 2 therefore starts in **manifest-only mode** until a Kubernetes GPU worker is explicitly verified.
- Live check on 2026-09-06: `kubectl` client `v1.28.2`, context `docker-desktop`; API `https://127.0.0.1:6443` refused the connection. No cluster evidence was collected.
- The selected Kubernetes branch is 1.36.x, so the local 1.28 client should be upgraded or replaced with a compatible client before a real cluster run.

## What this laptop can and cannot prove

The local laptop can support:

- YAML rendering and static validation;
- shell/Python syntax checks;
- PromQL review against documented sample metric names;
- load-generator dry-run/help and parser tests;
- architectural reasoning and report preparation.

It cannot, without a reachable GPU Kubernetes cluster, prove:

- `nvidia.com/gpu` allocatable capacity;
- GPU Operator health;
- KServe pod scheduling;
- TTFT/E2E/queue/KV measurements;
- autoscaling events, cold-start duration, or recovery time.

## Evidence required before calling a run measured

Save the following in the report or an ignored local evidence folder:

```text
kubectl version -o yaml
kubectl get nodes -o wide
kubectl describe node <gpu-node>
kubectl get pods -A
kubectl get inferenceservice -n lab02-kubernetes-llm -o yaml
kubectl get pods -n lab02-kubernetes-llm -o wide --show-labels
curl <metrics-endpoint>/metrics
raw load-generator CSV files
Prometheus query responses and timestamps
```

No value is filled in here for GPU utilization, TTFT, E2E, queue, KV, replica count, or recovery time.

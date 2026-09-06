# Lab 02 report — Kubernetes LLM serving

> Điền bằng evidence thật. Giá trị không có raw evidence phải ghi `NOT_RUN`, `UNAVAILABLE` hoặc `NA`; không dùng sample metrics như số đo.

## 1. Metadata and execution mode

| Field | Value |
|---|---|
| Student / date | |
| Mode | `manifest-only` / `cluster-run` |
| Kube context | |
| Kubernetes server version | |
| GPU node(s) | |
| GPU model / VRAM | |
| Driver / runtime | |
| GPU Operator | |
| KServe | |
| vLLM image + digest | |
| Model revision | |
| Prometheus chart | |
| KEDA | `not installed` / version |

Attach or link raw preflight output. If this is the RTX 3050 laptop without a reachable GPU cluster, state that clearly here.

## 2. Architecture and scheduling

Insert:

- Mermaid architecture;
- Kubernetes Scheduler vs inference scheduler diagram;
- namespace/pod/service/metrics topology;
- GPU allocation path: node → device plugin → `nvidia.com/gpu` → pod.

Explain why Kubernetes scheduling and vLLM request scheduling solve different problems.

## 3. Baseline configuration

| Parameter | Value | Evidence |
|---|---|---|
| model | `Qwen/Qwen2.5-0.5B-Instruct` | |
| vLLM image | `vllm/vllm-openai:v0.8.3` | |
| max context | `4096` | |
| GPU memory target | `0.80` | |
| CPU offload | `1 GB` | |
| GPU per pod | `1` | |
| min/max replicas | `1 / 2` | |
| scale signal | CPU baseline; queue/TTFT optional | |

Record any deviations and the reason. Do not claim that `0.80` guarantees no OOM.

## 4. Health, GPU and serving evidence

| Checkpoint | Command/output | Status |
|---|---|---|
| node Ready | | |
| GPU allocatable > 0 | | |
| GPU Operator healthy | | |
| KServe CRD v1beta1 | | |
| InferenceService Ready | | |
| vLLM `/health` | | |
| vLLM `/metrics` | | |
| ServiceMonitor target UP | | |

## 5. Load methodology

Describe warmup, model-cache state, request payloads, timeout, concurrency order, max tokens, cooldown between conditions and whether server restarted between conditions.

Raw files:

```text
results/c1.csv
results/c2.csv
results/c4.csv
```

## 6. Saturation table

| Concurrency | Req/s | TTFT p50 | TTFT p95 | TTFT p99 | E2E p95 | Queue p95 | Waiting | KV util | Error rate | Goodput | SLO pass |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| 2 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |
| 4 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN |

Insert the required charts:

1. TTFT p95 vs concurrency;
2. Queue vs concurrency;
3. Throughput vs concurrency;
4. TTFT + queue + replicas timeline;
5. dashboard screenshots/spec.

Explain the saturation point from demand → running → queue → tail latency. Do not use GPU utilization alone.

## 7. Autoscaling experiment

| Phase | Start/end | desired replicas | ready replicas | queue | event |
|---|---|---:|---:|---:|---|
| Idle | | | | | |
| Low | | | | | |
| Burst | | | | | |
| Sustained high | | | | | |
| Low | | | | | |

Cold-start timeline:

```text
scale event → pod created → scheduled → image pulled → container running
→ GPU allocated → model loaded → warmup → readiness → first successful inference
```

Compare generic CPU/resource signal with queue/running/TTFT/KV signals. If optional KEDA/adapter was not installed, explain why the inference-aware part is design-only.

## 8. Routing/cache experiment

| Workload | Router | backend share | prefix hit ratio | TTFT p95 | queue p95 | hotspot evidence |
|---|---|---|---:|---:|---:|---|
| Prefix A repeated | generic | | | | | |
| Prefix A repeated | cache/load-aware | | | | | |
| Prefix B repeated | generic | | | | | |
| Prefix B repeated | cache/load-aware | | | | | |
| Random control | generic | | | | | |
| Random control | cache/load-aware | | | | | |

If fewer than two live replicas exist, mark this table as simulation/design analysis, not cluster measurement.

## 9. Failure recovery

| Event | failed requests | retry behavior | reschedule time | ready time | capacity loss | SLO impact |
|---|---:|---|---:|---:|---:|---|
| delete one predictor pod | | | | | | |

State whether the test was performed on a disposable lab cluster. One successful restart is not production HA proof.

## 10. SLO, goodput and cost

Chosen lab SLO (not industry default):

```text
TTFT p95 <= ______ s
E2E p95 <= ______ s
error rate <= ______
```

```text
goodput = completed requests meeting all selected SLOs / observation seconds
```

| Configuration | GPU count | Goodput | TTFT SLO pass | Relative cost | Evidence |
|---|---:|---:|---|---|---|
| 1 replica | | | | | |
| 2 replicas | | | | | |
| cache-aware | | | | | |

Do not insert cloud currency without provider, region, billing model and observation window.

## 11. Security review

- [ ] Namespace isolation and Pod Security labels.
- [ ] ServiceAccount token disabled unless required.
- [ ] No token/secret in Git; gated model uses external Secret management.
- [ ] NetworkPolicy reviewed against model download, DNS, metrics and ingress.
- [ ] Image tag and digest recorded; scanner result attached.
- [ ] `nvidia.com/gpu` allocation is separated from application authorization.
- [ ] Production RBAC, admission policy, quota and audit requirements identified.

## 12. Production gate and limitations

| Gate | Evidence | Pass/conditional/block |
|---|---|---|
| capacity/headroom | | |
| SLO/tail latency | | |
| availability/recovery | | |
| autoscaling/cold start | | |
| cache locality | | |
| observability/alerts | | |
| security | | |
| cost/goodput | | |

Final conclusion must separate:

- `FACT`: directly shown by command/raw data;
- `INFERENCE`: reasoned from facts;
- `LIMITATION`: what this environment cannot prove;
- `RECOMMENDATION`: next safe experiment.

## 13. Anti-conclusion check

- [ ] I did not call a static render a benchmark.
- [ ] I did not invent GPU utilization, TTFT, queue, KV, scale or recovery numbers.
- [ ] I did not treat a missing PromQL series as zero.
- [ ] I did not infer production HA from one GPU worker.
- [ ] I did not claim that more replicas or higher GPU utilization automatically improves user experience.

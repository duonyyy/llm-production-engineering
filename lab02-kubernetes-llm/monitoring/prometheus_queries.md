# Prometheus queries for Lab 02

> Metric names below are pinned to the Lab 1 vLLM `v0.8.3` profile where possible. Always verify the live `/metrics` endpoint first. A query returning no series is not a measured zero.

## Verify target and raw names

```promql
up{namespace="lab02-kubernetes-llm"}
```

```bash
kubectl -n lab02-kubernetes-llm port-forward svc/lab02-vllm-metrics 18000:8000
curl -s http://127.0.0.1:18000/metrics | rg "^(vllm|DCGM|DCGM_FI)"
```

## User experience

TTFT p50/p95/p99:

```promql
histogram_quantile(0.50, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket{namespace="lab02-kubernetes-llm"}[5m])))
histogram_quantile(0.95, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket{namespace="lab02-kubernetes-llm"}[5m])))
histogram_quantile(0.99, sum by (le) (rate(vllm:time_to_first_token_seconds_bucket{namespace="lab02-kubernetes-llm"}[5m])))
```

E2E p95:

```promql
histogram_quantile(0.95, sum by (le) (rate(vllm:e2e_request_latency_seconds_bucket{namespace="lab02-kubernetes-llm"}[5m])))
```

Error rate (adapt labels/status if the live metric differs):

```promql
sum(rate(vllm:request_success_total{namespace="lab02-kubernetes-llm", finished_reason="error"}[5m]))
/
sum(rate(vllm:request_success_total{namespace="lab02-kubernetes-llm"}[5m]))
```

If the v0.8.3 image exposes a different counter, use the request status fields from the load-generator CSV for the client-side error rate and document the substitution.

## Scheduler/queue

```promql
vllm:num_requests_running{namespace="lab02-kubernetes-llm"}
vllm:num_requests_waiting{namespace="lab02-kubernetes-llm"}
histogram_quantile(0.95, sum by (le) (rate(vllm:request_queue_time_seconds_bucket{namespace="lab02-kubernetes-llm"}[5m])))
```

## KV/prefix cache

```promql
vllm:gpu_cache_usage_perc{namespace="lab02-kubernetes-llm"}
```

Possible prefix signals in the pinned/other engine versions:

```promql
vllm:gpu_prefix_cache_hit_rate{namespace="lab02-kubernetes-llm"}
vllm:prefix_cache_hits{namespace="lab02-kubernetes-llm"}
vllm:prefix_cache_queries{namespace="lab02-kubernetes-llm"}
```

If only counters exist:

```promql
sum(rate(vllm:prefix_cache_hits{namespace="lab02-kubernetes-llm"}[5m]))
/
sum(rate(vllm:prefix_cache_queries{namespace="lab02-kubernetes-llm"}[5m]))
```

`gpu_cache_usage_perc` and `kv_cache_usage_perc` must not be silently swapped. Record the actual metric name in the report.

## GPU/DCGM

The exact DCGM metric labels depend on GPU Operator/exporter configuration. First inspect target labels, then query a GPU UUID/node:

```promql
DCGM_FI_DEV_GPU_UTIL{namespace="gpu-operator"}
DCGM_FI_DEV_FB_USED{namespace="gpu-operator"}
DCGM_FI_DEV_FB_FREE{namespace="gpu-operator"}
```

If the exporter does not attach `namespace`, join node/pod labels through the exporter’s documented labels instead of inventing a join. GPU utilization is supporting evidence, not the saturation definition.

## Replica/scaling

```promql
count(kube_pod_status_ready{namespace="lab02-kubernetes-llm",condition="true",pod=~".*lab02-vllm.*"})
kube_pod_container_status_restarts_total{namespace="lab02-kubernetes-llm",container="kserve-container"}
kube_horizontalpodautoscaler_status_current_replicas{namespace="lab02-kubernetes-llm"}
```

## Scalar signal for an optional Prometheus/KEDA scaler

KEDA’s Prometheus scaler requires a query that returns one vector/scalar element. A safe first signal is:

```promql
max(vllm:num_requests_waiting{namespace="lab02-kubernetes-llm"})
```

Do not activate this scaler until the target Deployment name, Prometheus service URL, authentication and fallback behavior have been verified.

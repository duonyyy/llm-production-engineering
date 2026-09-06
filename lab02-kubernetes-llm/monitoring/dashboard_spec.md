# Dashboard specification — Lab 02

Dashboard title: `LLM Production Lab 02 — KServe/vLLM`

All panels must show namespace, service, pod/backend and time range. Use a visible annotation for deploy, scale, pod delete and model restart events.

## User experience

1. TTFT p50/p95/p99: `histogram_quantile` over `vllm:time_to_first_token_seconds_bucket`.
2. E2E p50/p95/p99: `vllm:e2e_request_latency_seconds_bucket`.
3. Client error rate: failed requests / total from load CSV, cross-check server counter.
4. Goodput: successful requests satisfying chosen TTFT/E2E/error SLO divided by observation seconds.

## Scheduler/inference

5. Running requests: `vllm:num_requests_running`.
6. Waiting requests: `vllm:num_requests_waiting`.
7. Queue p95: `vllm:request_queue_time_seconds_bucket`.
8. Output-token rate / request rate: use actual vLLM counters present in `/metrics`.

## KV/cache

9. KV cache usage: actual `gpu_cache_usage_perc` or version-specific replacement.
10. Prefix hit ratio: gauge or `rate(hits)/rate(queries)`.

## GPU/cluster

11. DCGM GPU utilization.
12. DCGM framebuffer used/free.
13. Ready/pending replicas and pod restarts.
14. GPU allocatable vs requested: Kubernetes node/exporter evidence.

## Scaling/cold start

15. Desired/current/ready replicas and HPA conditions.
16. Timeline markers: pod created, scheduled, image pulled, container started, ready, first successful request.
17. Queue/TTFT versus replica count in the same time range.

## Visual QA acceptance

- No panel says `0` when the series is absent; use `No data`.
- Every metric panel displays its exact metric name in description.
- A sample metric screenshot is not a measured GPU run.
- Record dashboard JSON/export plus query version in the report.

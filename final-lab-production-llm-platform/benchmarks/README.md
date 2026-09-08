# Benchmark boundary

Run only comparable workloads from `workload_matrix.yaml`. A benchmark report
must capture the model, exact server command/configuration, execution mode,
hardware, prompt set version, concurrency, warm-up policy, raw records and
error count.

Do not derive token throughput from SSE chunk count. If verified API usage or a
documented tokenizer estimate is unavailable, token metrics are `NA` while
latency can still be reported from timestamps.

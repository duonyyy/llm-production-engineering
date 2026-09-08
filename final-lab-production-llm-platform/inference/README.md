# Inference boundary

This directory owns serving profiles and readiness assumptions, not benchmark
results. The first profile is deliberately sized for one GTX 3050 Laptop GPU
with 4 GB VRAM. It must be revalidated against the actual vLLM image, driver,
Docker/NVIDIA runtime and model revision before use.

Use `results/` for a real environment manifest, `/v1/models` response,
`/metrics` snapshot, server logs and raw request records. Until then, every
runtime result remains `NOT_RUN`.

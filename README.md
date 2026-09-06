# llm-production-engineering

Hands-on labs for production LLM serving and infrastructure engineering.

## Labs

- `lab01-vllm-inference/` — vLLM serving, streaming, KV cache and benchmarking.
- `lab02-kubernetes-llm/` — Kubernetes deployment, GPU scheduling, monitoring and recovery.
- `lab03-advanced-llm-agent/` — LMCache, prefill/decode architecture, agent runtime and MCP.

The labs are designed to separate measured results from architecture-only or
hardware-limited experiments. The active local profile uses an NVIDIA RTX 3050
Laptop GPU with 4 GB VRAM; two-GPU P/D and production-topology claims require a
separate Linux environment.

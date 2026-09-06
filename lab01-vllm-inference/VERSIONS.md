# LAB 01 — Version Manifest

Ngày ghi nhận manifest: 2026-09-04

| Thành phần | Version pin | Phạm vi | Trạng thái kiểm tra |
|---|---|---|---|
| vLLM Docker image | `vllm/vllm-openai:v0.8.3` | Server | Flag engine được đối chiếu với official docs v0.8.3; chưa chạy trên máy hiện tại |
| Python client | Python 3.13.x | Benchmark client | Syntax/static check đã chạy |
| httpx | `0.28.1` | HTTP/SSE client | Có trong môi trường client hiện tại |
| aiohttp | `3.14.3` | Fallback client | Có trong môi trường client hiện tại |
| pandas | `2.3.3` | Phân tích CSV | Có trong môi trường client hiện tại |
| matplotlib | `3.10.9` | Biểu đồ | Có trong môi trường client hiện tại |
| numpy | `2.5.2` | Percentile | Có trong môi trường client hiện tại |
| tqdm | `4.67.1` | Progress display | Có trong môi trường client hiện tại |
| transformers | `5.10.2` | Tokenizer fallback, tùy chọn | Có trong môi trường client hiện tại; phải dùng tokenizer cùng model |

## Quy tắc version-sensitive

- `--cpu-offload-gb` trong vLLM 0.8.3 là CPU **weight offload**, không được gọi là KV-cache offload.
- `--enable-prefix-caching` và tên metric phải đối chiếu lại nếu đổi vLLM image.
- `stream_options.include_usage` là tùy chọn version-sensitive. Nếu server không trả usage, benchmark chỉ dùng token count khi có tokenizer fallback; nếu không thì ghi `NA`.
- Không dùng `latest` trong image benchmark.

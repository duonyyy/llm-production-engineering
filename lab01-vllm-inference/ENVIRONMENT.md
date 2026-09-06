# LAB 01 — Environment Contract

## Primary path

- Ubuntu/Linux x86_64 hoặc WSL2 chạy Linux containers.
- Docker Engine/Desktop có daemon hoạt động.
- NVIDIA driver và NVIDIA Container Toolkit.
- GPU khuyến nghị: 16–24 GB VRAM cho model 7B FP16/BF16.
- Python client theo `requirements.txt`.

## Active profile cho thiết bị hiện tại

- GPU: NVIDIA GeForce RTX 3050 Laptop GPU, 4 GB VRAM.
- Model mặc định: `Qwen/Qwen2.5-0.5B-Instruct`.
- `MAX_MODEL_LEN=4096`, `GPU_MEMORY_UTILIZATION=0.80`, shared memory Docker `2g`.
- Benchmark mặc định: concurrency `1 2 4`, tối đa `5` requests/level và `64` output tokens.
- Nếu OOM: hạ `MAX_MODEL_LEN` xuống `2048`, rồi giảm output/concurrency; không chuyển thẳng sang 7B.

## Fallback theo phần cứng

| Hardware | Phạm vi được phép | Không được kết luận |
|---|---|---|
| 16–24 GB VRAM | Baseline 7B và concurrency/prefix benchmark | Không suy rộng sang GPU khác |
| 8–12 GB VRAM | Model nhỏ hơn hoặc quantized đã kiểm thử | Không so sánh trực tiếp với 7B FP16 |
| 4–6 GB VRAM | Chỉ smoke test với model rất nhỏ/quantized phù hợp | Không chạy cấu hình 7B mặc định |
| Không có GPU | Static code/schema review hoặc benchmark server khác | Không gọi là GPU performance result |

## Evidence bắt buộc

Mỗi lần chạy phải lưu:

1. `nvidia-smi` và `docker version`;
2. image ID/model revision;
3. server command/config;
4. `/v1/models` response;
5. `/metrics` snapshot trước/sau benchmark;
6. raw CSV, summary CSV/JSON và log;
7. trạng thái token metric: `api_usage`, `tokenizer_estimate` hoặc `unavailable`.

## Security boundary

Lab local không expose server trực tiếp ra Internet. `--trust-remote-code` không bật mặc định; chỉ bật khi model đã được review và thật sự cần.

## Snapshot runner hiện tại (2026-09-04; không phải benchmark result)

- `nvidia-smi`: thấy NVIDIA GeForce RTX 3050 Laptop GPU, driver 591.74, VRAM vật lý 4096 MiB.
- `docker version`: daemon chưa hoạt động (`docker_engine` pipe không kết nối được).
- `bash -n`/WSL static check: Windows chặn tạo tiến trình với `E_ACCESSDENIED` trong runner hiện tại.
- Kết luận vận hành: chỉ xác nhận được Python/static/schema checks; chưa có quyền gọi đây là kết quả inference GPU hoặc Docker benchmark.

# Lab 02 — Version manifest

> Ngày kiểm tra tài liệu: **2026-09-06** (Asia/Bangkok).
>
> Đây là manifest cho học tập. `Current checked version` là phiên bản đã thấy trong tài liệu/release chính thức tại ngày trên; chưa có nghĩa là phiên bản đó đã chạy thành công trên máy hiện tại.

| Component | Version pin | Current checked version | Compatibility / rationale |
|---|---:|---:|---|
| Kubernetes | `v1.36.x` (khuyến nghị patch mới nhất của nhánh 1.36) | `v1.37.0` latest; 1.36 còn được hỗ trợ | Chọn nhánh 1.36 để giảm rủi ro ecosystem so với latest. Ghi patch thực tế trong report sau `kubectl version`.
| NVIDIA GPU Operator | `v26.7.0` | `v26.7.0` | Tài liệu NVIDIA latest đang ghi 26.7.x được hỗ trợ. Với laptop RTX 3050, operator chỉ chạy trên GPU worker Linux có driver/container runtime tương thích; không cài trên Windows host trực tiếp.
| KServe | `v0.20.0` | `v0.20.0` release | Dùng Standard mode và API `serving.kserve.io/v1beta1`. KServe v0.20 yêu cầu cert-manager cho Standard mode; quick-install không tự biến máy cá nhân thành GPU cluster.
| vLLM image | `vllm/vllm-openai:v0.8.3` | `v0.8.3` | Giữ đồng nhất với Lab 1 đã pin. Không dùng `latest`; phải ghi image digest khi chạy thực tế.
| Model | `Qwen/Qwen2.5-0.5B-Instruct` | — | Profile nhỏ để phù hợp 4GB VRAM; model weights vẫn phải tải vào node, không suy ra từ riêng tên model.
| Prometheus stack | Helm chart `kube-prometheus-stack:88.0.1` | `88.0.1` package release được kiểm tra | Cài Prometheus Operator, Prometheus, Grafana và CRD `ServiceMonitor`/`PrometheusRule`. Có thể hạ chart nếu compatibility matrix của cluster yêu cầu.
| cert-manager | `v1.21.1` | `v1.21.1` | KServe Standard mode cần certificate/webhook support; cert-manager 1.21.x được tài liệu cert-manager ghi hỗ trợ/test trên Kubernetes 1.33–1.36.
| KEDA (optional) | `v2.19.0` | `v2.19.0` | Chỉ bật khi cần scale bằng PromQL. Lab mặc định dùng KServe native scaling; file `autoscaling.yaml` không giả định KEDA đã có.

## Quy tắc cập nhật version

1. Ghi lại `kubectl version`, `helm list -A`, image digest và CRD versions vào report.
2. Nếu đổi một version, phải kiểm tra lại API/flag/metric name tương ứng; không chỉ sửa một dòng pin.
3. Không gọi kết quả là benchmark GPU nếu thiếu cluster GPU thật và raw output.
4. KServe `v0.20.0` có LLMInferenceService riêng cho workload GenAI nâng cao, nhưng Lab này giữ `InferenceService` vì đó là yêu cầu bắt buộc của đề bài; phần routing nâng cao được biểu diễn thành policy ConfigMap, không giả vờ đó là Gateway API CRD.

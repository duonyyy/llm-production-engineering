# Advanced Track — Distributed LLM Systems

Kubernetes và P/D multi-GPU là phần **nâng cao, tùy chọn**. Chúng không phải
điều kiện để hoàn thành lộ trình single-node hoặc Final Lab trên GTX 3050 4 GB.
Các folder gốc được giữ nguyên để bảo toàn provenance, link và bài thực hành.
Thay đổi ở đây là thứ tự học và acceptance criteria, không phải di chuyển code.

## Core path cho người học cá nhân

```text
Lab 01 local vLLM
  -> Final Lab single-node: Nginx + FastAPI + CPU RAG + vLLM + observability
  -> Lab 03 agent/MCP read-only và SQLite state
```

Core chỉ yêu cầu `LOCAL` hoặc `STATIC` evidence. Một dịch vụ local chạy được
không tự trở thành production/HA, nhưng đủ để học serving, RAG, tracing,
metrics, logs, policy và failure handling có kiểm chứng.

## Advanced path A — Kubernetes

**Artifact:** [Lab 02](lab02-kubernetes-llm/README.md)

Chủ đề: scheduler, GPU device plugin, KServe, manifests, monitoring,
autoscaling, replica routing và cluster failure recovery.

Chỉ bắt đầu khi có Linux GPU worker, reachable Kubernetes API, `kubectl`,
NVIDIA runtime và cluster context đã xác định. Laptop có thể kiểm tra
manifest/schema ở mức `STATIC`, nhưng không được gọi là cluster deployment,
autoscaling hay GPU capacity measurement.

## Advanced path B — P/D và multi-GPU

**Artifact:** [Lab 03](lab03-advanced-llm-agent/README.md), phần P/D/LMCache

Chủ đề: prefill/decode disaggregation, KV handoff, LMCache/NIXL, transport,
tail latency, multi-GPU capacity và failure injection giữa worker.

Chỉ bắt đầu khi có Linux và ít nhất hai GPU NVIDIA tương thích. Baseline
colocated phải có raw evidence trước; localhost TCP hoặc single GPU không được
dùng để suy ra P/D, RDMA/NVLink hay production topology.

## Phân tách trong Lab 03

| Nội dung | Track |
|---|---|
| agent state, read-only MCP, authorization denial, audit/idempotency | Core-compatible |
| colocated router contract và static benchmark logic | Core-compatible |
| P/D workers, LMCache MP, NIXL, KV transfer, P/D benchmark/failure drill | Advanced only |
| Kubernetes manifests/RBAC reference | Advanced only |

## Quy tắc báo cáo

- Core completion không bị chặn bởi K8s hoặc P/D `NOT_RUN`.
- Advanced result phải ghi `REFERENCE`, environment, topology, raw evidence và
  failure state; không suy rộng từ một run nhỏ.
- Không điền metric P/D, autoscaling, RDMA/NVLink hoặc cluster capacity bằng
  estimate/diagram. Thiếu telemetry thì ghi `NA` hoặc `NOT_RUN`.

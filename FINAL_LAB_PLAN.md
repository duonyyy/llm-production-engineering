# Final Lab Plan — Production LLM Operations Copilot

## 1. Mục tiêu tổng thể

Xây dựng một nền tảng LLM production-oriented cho trợ lý vận hành nội bộ
(Operations Copilot).

Hệ thống phải giải quyết một bài toán xuyên suốt:

> Người dùng hỏi về tình trạng inference service hoặc yêu cầu giải thích một
> vấn đề hiệu năng; hệ thống trả lời bằng LLM, có thể đọc health/metrics qua
> MCP read-only, lưu state của phiên làm việc và cung cấp evidence có thể truy
> vết.

Final Lab không phải là phép cộng cơ học của ba lab. Ba lab phải dùng chung
request contract, metric contract, error policy và correlation ID.

## 2. Kiến trúc mục tiêu

```text
User
  ↓
Authenticated Gateway
  ↓
Agent Runtime
  ├── Session State
  ├── Policy / Authorization
  ├── MCP Client
  │      ↓
  │   Read-only MCP Tools
  │
  └── Inference Router
         ├── Colocated vLLM Worker
         └── P/D Reference Path
                 ↓
              KV Cache / Transfer
                 ↓
              Decode Worker
```

Correlation bắt buộc:

```text
task_id → llm_request_id → router_request_id → tool_call_id
```

## 3. Vai trò của ba lab con

| Lab | Thành phần được tích hợp |
|---|---|
| Lab 1 | vLLM serving, OpenAI-compatible API, streaming, TTFT/TPOT/E2E, GPU metrics |
| Lab 2 | Kubernetes namespace, Service, RBAC, monitoring, autoscaling và failure recovery |
| Lab 3 | Router, LMCache/KV architecture, P/D reference, agent state, MCP và security boundary |

Các lab con vẫn được giữ độc lập để bảo toàn provenance. Final Lab chỉ lấy các
thành phần cần thiết và tích hợp qua contract chung.

## 4. Contract bắt buộc

### 4.1 Request contract

Mỗi request phải có:

- `request_id`;
- `model`;
- `messages`;
- `max_tokens`;
- `stream`;
- `router_mode`;
- timeout;
- workload label.

### 4.2 Agent contract

Mỗi task phải có:

- `task_id`;
- `session_id`;
- trạng thái execution;
- tool call log;
- retry/idempotency key;
- audit event;
- trạng thái `completed`, `failed_closed` hoặc `waiting_approval`.

### 4.3 Metric contract

Inference:

- TTFT;
- TPOT/ITL;
- E2E latency;
- queue time;
- prompt/completion tokens;
- KV usage;
- GPU memory/utilization;
- transfer latency/failure nếu đo được.

Agent:

- task latency;
- LLM calls/task;
- tool calls/task;
- tool errors;
- retries;
- authorization denials;
- approval events.

Không có số liệu thật thì ghi `NA`, `NOT_RUN` hoặc `DESIGN_ONLY`; không tự suy
đoán.

## 5. Lộ trình thực hiện

### Giai đoạn 0 — Chốt baseline và environment

1. Ghi model, image, driver, CUDA, Python, Node và hardware.
2. Chạy preflight của Lab 1 và Lab 2.
3. Xác định mode thực thi:
   - `LOCAL_MODE`;
   - `REFERENCE_MODE`.
4. Tạo version manifest và run manifest.

**Gate:** mọi kết quả sau này đều biết rõ chạy trên phần cứng và version nào.

### Giai đoạn 1 — Tích hợp colocated inference

Dùng profile hiện tại:

- NVIDIA RTX 3050 Laptop GPU, 4 GB VRAM;
- `Qwen/Qwen2.5-0.5B-Instruct`;
- `max_model_len=2048`;
- concurrency thấp;
- một vLLM worker.

Kiểm tra:

- `/health` hoặc readiness tương ứng;
- `/v1/models`;
- non-streaming request;
- streaming request;
- TTFT, TPOT và E2E;
- `/metrics`;
- GPU memory.

**Gate:** local inference chạy được và có raw evidence.

### Giai đoạn 2 — Đóng gói production

Tích hợp các thành phần vào Kubernetes manifests:

- namespace;
- ServiceAccount;
- Role read-only;
- Service;
- NetworkPolicy;
- readiness/liveness;
- resource limits;
- monitoring metadata.

Nếu Kubernetes API server không hoạt động, chỉ nghiệm thu static manifest/schema;
không gọi là live deployment.

**Gate:** manifest hợp lệ, RBAC không có quyền write, Secrets hoặc `pods/exec`.

### Giai đoạn 3 — Tích hợp Agent và MCP

Agent flow:

```text
Task
  ↓
Load session state
  ↓
Decide / call LLM
  ↓
Select allowed read-only tool
  ↓
Observe
  ↓
Persist state and audit event
  ↓
Return answer
```

Core tools:

- `get_cluster_summary`;
- `get_model_health`;
- `get_recent_metrics`.

Không triển khai shell, generic command execution, filesystem write, Secrets
reader hoặc `kubectl exec`.

Kiểm thử:

1. MCP server down;
2. tool timeout;
3. invalid argument;
4. authorization denial;
5. duplicate retry;
6. restart agent rồi khôi phục session state.

**Gate:** agent fail closed, giữ được state và không fallback sang hành động
nguy hiểm.

### Giai đoạn 4 — Benchmark workload

Giữ cố định giữa các mode:

- model;
- prompt;
- output length;
- concurrency;
- request count;
- sampling parameters.

Workload matrix:

| Workload | Mục đích |
|---|---|
| Short input / short output | latency cơ bản |
| Long input / short output | prefill pressure |
| Short input / long output | decode pressure |
| Long input / long output | tổng hợp pressure |
| Repeated prefix | prefix/KV reuse |
| Mixed workload | workload đại diện hơn |

Output cần có raw CSV, summary, environment snapshot và log.

### Giai đoạn 5 — Optimization reference

So sánh:

```text
Mode A: Colocated
Mode B: P/D + KV transfer
```

P/D thật chỉ được chạy khi có Linux và hai GPU tương thích. Với máy hiện tại:

```text
P/D = architecture/reference only
KV transfer = NA
RDMA/NVLink = not assessed
```

Không dùng single-GPU hoặc localhost TCP để kết luận production P/D topology.

### Giai đoạn 6 — Failure và graceful degradation

Kiểm thử:

- inference worker down;
- router timeout;
- MCP unavailable;
- LMCache unavailable;
- decode failure;
- transfer failure.

Fallback hợp lệ:

```text
P/D unavailable → colocated inference
MCP unavailable → trả lời với trạng thái thiếu evidence
Cache unavailable → recompute
```

Phải phân biệt:

- availability degradation: request vẫn phục vụ được;
- performance degradation: request vẫn chạy nhưng chậm hơn.

Không retry mù đối với action có side effect.

### Giai đoạn 7 — Báo cáo và production gate

Báo cáo phải tách:

```text
FACT
INFERENCE
RECOMMENDATION
LIMITATION
```

Các gate cần đánh giá:

| Gate | Câu hỏi |
|---|---|
| Capacity | saturation point và long-context capacity là bao nhiêu? |
| SLO | TTFT, TPOT, E2E, error rate có đạt mục tiêu không? |
| P/D | transfer overhead và failure path đã đo chưa? |
| Cache | hit ratio, eviction và compatibility đã biết chưa? |
| Security | AuthN, AuthZ, least privilege và secret boundary đã rõ chưa? |
| Agent | state, retry, idempotency, audit và approval đã có chưa? |
| Cost | GPU-hours, CPU RAM, network và external KV cost là bao nhiêu? |

Gate chưa có evidence phải ghi `NOT ASSESSED`, không ghi `PASS`.

## 6. Hai chế độ triển khai

### 6.1 LOCAL_MODE — chạy trên thiết bị hiện tại

Được phép đo thật:

- colocated vLLM;
- streaming;
- inference latency;
- agent runtime;
- MCP read-only;
- SQLite state;
- static Kubernetes validation.

Không được kết luận:

- P/D performance;
- NIXL/RDMA/NVLink performance;
- hai-GPU capacity;
- production autoscaling thật.

### 6.2 REFERENCE_MODE — môi trường Linux + 2 GPU

Cho phép kiểm tra thêm:

- prefill process;
- decode process;
- LMCache MP;
- NIXL connector;
- KV handoff;
- failure injection giữa các worker;
- so sánh colocated/P/D.

Mọi version-sensitive command phải được kiểm tra lại trước khi chạy.

## 7. Cấu trúc thư mục Final Lab

```text
final-lab-production-llm-platform/
├── README.md
├── contracts/
│   ├── api_contract.yaml
│   ├── metrics_schema.yaml
│   └── error_policy.md
├── inference/
├── router/
├── agent/
├── mcp-server/
├── kubernetes/
├── benchmarks/
├── chaos/
├── datasets/
├── results/
└── report/
```

Final Lab là artifact mới, không sửa ngược nội dung Lab 1–3.

## 8. Acceptance criteria

Final Lab chỉ được xem là đạt khi:

- local inference chạy được trên RTX 3050;
- agent gọi được MCP read-only;
- session state khôi phục được sau restart;
- request có correlation ID đầy đủ;
- Kubernetes manifests parse được;
- RBAC không cấp write, Secrets hoặc `pods/exec`;
- benchmark có raw data;
- lỗi backend không tạo số liệu giả;
- P/D được đánh dấu `NOT_RUN` khi thiếu hai GPU;
- report phân biệt fact, inference và limitation.

## 9. Phạm vi không làm trong Final Lab

Để tránh scope creep, chưa đưa vào:

- VLM;
- RAG;
- multi-agent;
- fine-tuning;
- KServe CRD;
- production database;
- write tool;
- multi-node deployment;
- RDMA/NVLink claim;
- autoscaling thật nếu cluster chưa có GPU Operator.

## 10. Kết luận thiết kế

Final Lab phải chứng minh một chuỗi có thể kiểm chứng:

```text
Inference
  → Observability
  → Routing
  → Agent State
  → MCP Security
  → Failure Handling
  → Production Decision
```

Không đánh giá thành công bằng số lượng công nghệ được bật. Thành công là đưa
ra được quyết định kiến trúc dựa trên workload, evidence, giới hạn phần cứng,
overhead và khả năng rollback.

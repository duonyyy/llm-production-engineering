# Final Lab Plan — Single-Node Production LLM + RAG Copilot

## 1. Mục tiêu tổng thể

Xây dựng một nền tảng LLM production-style single-node cho trợ lý vận hành nội
bộ có câu trả lời grounded bằng RAG (Operations Copilot).

Hệ thống phải giải quyết một bài toán xuyên suốt:

> Người dùng hỏi về tình trạng inference service, vấn đề hiệu năng hoặc nội
> dung thuộc knowledge base đã được phê duyệt; hệ thống chỉ trả lời grounded
> khi có evidence RAG hợp lệ, có thể đọc health/metrics qua MCP read-only, lưu
> state của phiên làm việc và cung cấp evidence có thể truy vết.

Final Lab không phải là phép cộng cơ học của ba lab. Ba lab phải dùng chung
request contract, RAG contract, metric contract, error policy và correlation
ID. Single-node có cấu trúc production-oriented nhưng không chứng minh HA,
autoscaling hay vận hành cluster.

## 2. Kiến trúc mục tiêu

Thiết kế canonical chi tiết nằm ở
[`final-lab-production-llm-platform/ARCHITECTURE.md`](final-lab-production-llm-platform/ARCHITECTURE.md).
Plan này quyết định scope/gate; architecture document quyết định ownership và
luồng dữ liệu khi hai tài liệu cần được đọc cùng nhau.

```text
User
  ↓
Nginx
  ↓
FastAPI / Request Orchestrator
  ├── RAG path (when rag.mode=required)
  │     └── CPU embedding → local FAISS index → context with citations
  ├── Agent Runtime (when a read-only observation is needed)
  │     ├── Session State / Policy / Authorization
  │     └── MCP Client → allowlisted read-only tools
  └── Inference Router
        ├── Colocated vLLM Worker → GTX 3050 4 GB
        └── P/D Reference Path (Advanced Track only; not runnable locally)

Nginx / FastAPI / RAG / Agent-MCP / vLLM
  ├── Prometheus → Grafana
  └── structured logs → local rotated storage or configured log viewer
```

Correlation bắt buộc:

```text
task_id
  ├── retrieval_id (khi dùng RAG)
  ├── llm_request_id → router_request_id
  └── tool_call_id (khi gọi MCP)
```

## 3. Vai trò của ba lab con

| Lab | Thành phần được tích hợp |
|---|---|
| Lab 1 | vLLM serving, OpenAI-compatible API, streaming, TTFT/TPOT/E2E, GPU metrics |
| Lab 2 | monitoring, health/failure-recovery và resource-boundary lessons; Kubernetes artifacts giữ riêng tại Lab 2 |
| Lab 3 | Core agent/MCP contract; Advanced P/D, LMCache/KV reference và distributed failure boundary |

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

Với grounded request, thêm `rag.mode=required`, `knowledge_base_id`, `top_k`
và metadata filter do server cưỡng chế. Không có evidence được phép truy xuất
thì trả về insufficient-evidence, không fallback âm thầm sang LLM thuần.

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

RAG:

- embedding latency;
- retrieval latency;
- số chunk được truy xuất;
- context tokens;
- knowledge-base/index version;
- citation count;
- empty/insufficient-evidence rate.

Không có số liệu thật thì ghi `NA`, `NOT_RUN` hoặc `DESIGN_ONLY`; không tự suy
đoán.

## 5. Lộ trình thực hiện

### Giai đoạn 0 — Chốt baseline và environment

1. Ghi model, image, driver, CUDA, Python, Node và hardware.
2. Chạy preflight của Lab 1; chỉ tham khảo Lab 2 như nguồn hợp đồng monitoring
   và failure recovery, không chạy Kubernetes trong Final Lab.
3. Xác định mode thực thi:
   - `LOCAL_MODE`;
   - `REFERENCE_MODE` chỉ cho Advanced Track.
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

### Giai đoạn 2 — Single-node gateway và observability

Tích hợp trên một máy:

- Nginx reverse proxy;
- FastAPI request orchestrator;
- health/readiness endpoint;
- Prometheus target contract;
- Grafana dashboard specification;
- structured logs có rotation và không chứa prompt/document/token/secret.

**Gate:** health, metric và log boundary có contract rõ ràng; không gọi là HA,
autoscaling hay cluster deployment.

### Giai đoạn 3 — Tích hợp RAG local

RAG flow:

```text
approved documents → provenance/access check → chunk → CPU embedding
  → FAISS + metadata index → authorized retrieval → cited context → vLLM
```

GPU được dành cho vLLM; embedding, FAISS và ingestion dùng CPU/RAM mặc định.
Chưa chọn embedding model hoặc chunk size khi chưa có corpus language, license
và evaluation set. Reranker chỉ được bật sau so sánh retrieval có evidence.

**Gate:** index/version/ACL contract, insufficient-evidence path và evaluation
design tồn tại; metric retrieval chưa có raw run thì là `NOT_RUN` hoặc `NA`.

### Giai đoạn 4 — Tích hợp Agent và MCP

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

- `get_model_health`;
- `get_recent_metrics`.

Không triển khai shell, generic command execution, filesystem write hoặc
Secrets reader.

Kiểm thử:

1. MCP server down;
2. tool timeout;
3. invalid argument;
4. authorization denial;
5. duplicate retry;
6. restart agent rồi khôi phục session state.

**Gate:** agent fail closed, giữ được state và không fallback sang hành động
nguy hiểm.

### Giai đoạn 5 — Benchmark workload

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
| Grounded answer / known source | retrieval + context + generation |
| Grounded answer / no evidence | correct insufficient-evidence abstention |

Với RAG giữ cố định knowledge-base/index version, embedding model, `top_k`,
metadata filter và citation policy. Output cần có raw CSV, summary, environment
snapshot, RAG manifest và log.

### Giai đoạn 6 — Advanced Track (optional): Optimization reference

So sánh:

```text
Mode A: Colocated
Mode B: P/D + KV transfer
```

P/D thật chỉ được chạy khi có Linux và hai GPU tương thích. Đây là Advanced
Track, không phải core Final Lab gate. Với máy hiện tại:

```text
P/D = architecture/reference only
KV transfer = NA
RDMA/NVLink = not assessed
```

Không dùng single-GPU hoặc localhost TCP để kết luận production P/D topology.

### Giai đoạn 7 — Failure và graceful degradation

Kiểm thử:

- inference worker down;
- router timeout;
- MCP unavailable;
- LMCache unavailable;
- decode failure;
- Advanced P/D transfer failure.
- RAG index unavailable;
- RAG không có authorized evidence.

Fallback hợp lệ:

```text
Advanced P/D unavailable → colocated inference
MCP unavailable → trả lời với trạng thái thiếu evidence
Cache unavailable → recompute
RAG required nhưng index/evidence unavailable → insufficient-evidence, không bịa citation
```

Phải phân biệt:

- availability degradation: request vẫn phục vụ được;
- performance degradation: request vẫn chạy nhưng chậm hơn.

Không retry mù đối với action có side effect.

### Giai đoạn 8 — Báo cáo và production gate

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
| Advanced P/D | transfer overhead và failure path đã đo chưa? Không chặn core completion. |
| Cache | hit ratio, eviction và compatibility đã biết chưa? |
| RAG | retrieval, evidence, citation và abstention có được đo riêng không? |
| Security | AuthN, AuthZ, least privilege và secret boundary đã rõ chưa? |
| Agent | state, retry, idempotency, audit và approval đã có chưa? |
| Cost | GPU-hours, CPU RAM, disk và local observability cost là bao nhiêu? |

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
- CPU embedding và FAISS local index;
- Nginx/FastAPI boundary;
- Prometheus/logging contract.

Không được kết luận:

- P/D performance;
- NIXL/RDMA/NVLink performance;
- hai-GPU capacity;
- HA, cluster deployment hoặc production autoscaling thật.

### 6.2 ADVANCED_REFERENCE_MODE — môi trường Linux + 2 GPU

Chỉ dành cho Advanced Track; không phải prerequisite của Final Lab core. Cho
phép kiểm tra thêm:

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
├── rag/
├── agent/
├── mcp-server/
├── observability/
├── benchmarks/
├── chaos/
├── datasets/
├── results/
└── report/
```

Final Lab là artifact mới, không sửa ngược nội dung Lab 1–3.

**Trạng thái scaffold hiện tại:** thư mục `final-lab-production-llm-platform/`
và các contract/boundary document đã được khởi tạo. Đây là `DESIGN_ONLY`, không
phải bằng chứng rằng các thành phần đã được tích hợp hoặc chạy runtime.

## 8. Acceptance criteria

Final Lab chỉ được xem là đạt khi:

- local inference chạy được trên RTX 3050;
- agent gọi được MCP read-only;
- session state khôi phục được sau restart;
- request có correlation ID đầy đủ;
- RAG grounded request có citation từ index version hợp lệ hoặc trả về
  insufficient-evidence;
- RAG không đưa document/chunk trái access scope vào context;
- Prometheus/logging boundary không chứa raw prompt, document, token hoặc secret;
- benchmark có raw data;
- lỗi backend không tạo số liệu giả;
- Advanced P/D được đánh dấu `NOT_RUN` khi thiếu hai GPU và không chặn core completion;
- report phân biệt fact, inference và limitation.

## 9. Phạm vi không làm trong Final Lab

Để tránh scope creep, chưa đưa vào:

- VLM;
- multi-agent;
- fine-tuning;
- Kubernetes/KServe;
- production database;
- write tool;
- multi-node deployment;
- RDMA/NVLink claim;
- autoscaling thật.

## 10. Kết luận thiết kế

Final Lab phải chứng minh một chuỗi có thể kiểm chứng:

```text
Inference
  → RAG Evidence
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

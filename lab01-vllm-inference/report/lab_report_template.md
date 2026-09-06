# BÁO CÁO THỰC NGHIỆM — LAB 01
## LLM Serving với vLLM: Prefill, Decode, KV Cache và Inference Optimization

**Họ và tên học viên / kỹ sư:** _______________________________________  
**Đơn vị / Lớp / Nhóm:** _______________________________________  
**Ngày thực hiện:** ____________________  
**Version vLLM sử dụng:** ____________________ (Ví dụ: `v0.8.3`)  
**Mô hình sử dụng:** ____________________ (Profile RTX 3050 4GB: `Qwen/Qwen2.5-0.5B-Instruct`)  
**Trạng thái báo cáo:** [ ] Measured/validated  [ ] Partial  [ ] Unvalidated  

---

> ⚠️ **NGUYÊN TẮC BẮT BUỘC KHI VIẾT BÁO CÁO:**
> 1. Toàn bộ số liệu phải lấy từ các file CSV/JSON sinh ra bởi các script benchmark thực tế trong thư mục `results/`.
> 2. Tuyệt đối không tự bịa đặt số liệu (Fake data). Mọi nhận xét phải tuân theo cấu trúc nhân - quả:  
>    `Configuration change → Observed metric change → Likely physical mechanism → Trade-off → Recommendation`.

### 0. Provenance bắt buộc

| Artifact | Đường dẫn thực tế | Có tồn tại? | Ghi chú/checksum |
|---|---|---:|---|
| Raw streaming CSV/JSON | | [ ] | |
| Concurrency summary/raw CSV/JSON | | [ ] | |
| Prefix Cache OFF raw CSV/JSON | | [ ] | |
| Prefix Cache ON raw CSV/JSON | | [ ] | |
| Prompt-length raw/summary CSV/JSON | | [ ] | |
| Server log + `/v1/models` | `results/run_metadata/<timestamp>/server.log` + `v1_models.json` | [ ] | |
| `/metrics` snapshot | `results/run_metadata/<timestamp>/metrics.txt` | [ ] | |

Nếu thiếu raw artifact hoặc không xác định được nguồn số liệu, không đánh dấu
báo cáo là `Measured/validated`.

---

## 1. Thông Tin Phần Cứng Máy Chủ (Hardware Environment)

| Thông số | Giá trị thực tế ghi nhận | Lệnh kiểm tra |
|---|---|---|
| **GPU Model** | | `nvidia-smi --query-gpu=name --format=csv,noheader` |
| **Dung lượng VRAM vật lý** | | `nvidia-smi --query-gpu=memory.total --format=csv,noheader` |
| **CPU Model & Số Cores** | | `lscpu \| grep "Model name"` hoặc `nproc` |
| **Dung lượng Host RAM** | | `free -h \| grep Mem` |
| **Hệ Điều Hành (OS)** | | `uname -a` hoặc `cat /etc/os-release` |
| **NVIDIA Driver Version** | | `nvidia-smi` |
| **CUDA Version** | | `nvcc --version` hoặc `nvidia-smi` |
| **Docker Version** | | `docker --version` |

---

## 2. Thông Tin Phiên Bản Phần Mềm (Software Stack)

| Thành phần | Phiên bản (Version) | Nguồn / Image ID |
|---|---|---|
| **vLLM Docker Image** | | Ví dụ: `vllm/vllm-openai:v0.8.3` |
| **Python** | | `python3 --version` |
| **httpx** | | `pip show httpx \| grep Version` |
| **pandas** | | `pip show pandas \| grep Version` |
| **matplotlib** | | `pip show matplotlib \| grep Version` |

---

## 3. Cấu Hình Mô Hình & Phân Bổ VRAM (Model & Memory Profile)

| Thuộc tính | Giá trị đo đạc / Khảo sát | Ghi chú kỹ thuật |
|---|---|---|
| **Model Hugging Face ID** | | Ghi model thực tế; profile RTX 3050 4GB dùng `Qwen/Qwen2.5-0.5B-Instruct` |
| **Kiến trúc Attention** | | MHA / GQA / MQA (Số KV heads = ?) |
| **Số lớp (Layers) & Head Dim** | | Ví dụ: 28 layers, head dim 128 |
| **Precision (Kiểu dữ liệu)** | | FP16 / BF16 / AWQ / GPTQ / FP8 |
| **Max Model Length (`--max-model-len`)** | | Ghi giá trị thực tế; không mặc định nếu chưa kiểm tra |
| **GPU Memory Utilization** | | Ghi giá trị thực tế từ server command; profile RTX 3050 4GB mặc định 0.80 nhưng không xem là kết quả đo |
| **VRAM chiếm dụng bởi Model Weights** | | Ghi nhận từ log khởi động (GB) |
| **VRAM dành cho Paged KV Cache** | | Ghi nhận từ log khởi động (GB) |
| **Số lượng GPU KV Blocks khả dụng** | | Lấy từ log/version; không tự suy ra block size |

---

## 4. Dữ Liệu Thực Nghiệm Chi Tiết (Raw Experimental Metrics)

### 4.1 Thí nghiệm 1: Concurrency Sweep (Khảo sát Concurrency)
*(Nguồn dữ liệu: `results/concurrency_sweep.csv`)*

| Concurrency | Tổng số Reqs | Thành công | Lỗi (%) | TTFT p50 (ms) | TTFT p95 (ms) | E2E p50 (s) | E2E p95 (s) | Throughput (req/s) | Throughput (tokens/s) | Token source |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | | | | | | | | | | |
| **2** | | | | | | | | | | |
| **4** | | | | | | | | | | |

Không điền sẵn số request nếu lần chạy dùng `--requests-per-level` khác mặc định.
Nếu `token_metrics_complete = False`, ghi `NA` cho throughput tokens/s và nêu rõ
nguyên nhân trong phần giới hạn.

---

### 4.2 Thí nghiệm 2: Automatic Prefix Caching (A/B Test)
*(Nguồn dữ liệu: `results/prefix_cache_off.csv` và `results/prefix_cache_on.csv`)*

| Cấu hình | Loại Workload | Số Reqs | TTFT p50 (ms) | TTFT p95 (ms) | TTFT Cold Req #1 (ms) | TTFT Warm Reqs (ms) | E2E p50 (s) | Throughput (req/s) | Token source |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **Prefix Cache OFF** | Shared Prefix | | | | | | | | |
| **Prefix Cache OFF** | Control (Không shared) | | | | | | | | |
| **Prefix Cache ON** | Shared Prefix | | | | | | | | |
| **Prefix Cache ON** | Control (Không shared) | | | | | | | | |

Ghi đúng số request thành công và tổng số request từ raw CSV; không mặc định là
30. `TTFT Cold Req #1` phải chỉ rõ cách xác định request đầu tiên và trạng thái
cache lúc bắt đầu.

---

### 4.3 Thí nghiệm 3: Khảo sát Nâng Cao (Offload / Quantization / Memory Pressure)
*(Nếu thực hiện — điền số liệu đo đạc thực tế)*

| Cấu hình thử nghiệm | Tham số thay đổi | TTFT p50 (ms) | E2E p50 (s) | Throughput (req/s) | VRAM Peak (GB) | Ghi chú hiện tượng |
|---|---|:---:|:---:|:---:|:---:|---|
| **Baseline FP16** | Mặc định | | | | | |
| **CPU Weight Offload** | `--cpu-offload-gb 4` | | | | | |
| **Quantized (Int4/FP8)**| Mô hình quantized | | | | | |

---

## 5. Phân Tích Đồ Thị & Trực Quan Hóa (Visualizations & Analysis)

Dán hình ảnh đồ thị xuất ra từ `benchmark/analyze_results.py` và trả lời đầy đủ 4 câu hỏi phân tích cho từng đồ thị.

### 5.1 Đồ thị 1: Concurrency vs TTFT p50 & p95
*(Dán ảnh `results/charts/01_concurrency_vs_ttft_p50.png` và `02_concurrency_vs_ttft_p95.png`)*

- **Quan sát thấy gì?** (Mô tả đường biểu diễn độ trễ khi concurrency tăng từ 1 lên 4 trong profile 4GB):  
  _________________________________________________________________________________________________
- **Giải thích cơ chế vật lý:** (Tại sao P95 TTFT lại tăng vọt khi nhiều request gửi vào cùng lúc? Liên hệ với hàng đợi Queue và năng lực tính toán GEMM của Tensor Cores):  
  _________________________________________________________________________________________________
- **Kết luận có thể rút ra:**  
  _________________________________________________________________________________________________
- **Điều chưa thể khẳng định:**  
  _________________________________________________________________________________________________

---

### 5.2 Đồ thị 2: Concurrency vs Throughput (Requests/s & Tokens/s)
*(Dán ảnh `results/charts/04_concurrency_vs_req_per_sec.png` và `05_concurrency_vs_tok_per_sec.png`)*

- **Quan sát thấy gì?** (Throughput có tiếp tục tăng tuyến tính không hay bão hòa? Điểm uốn xảy ra ở concurrency nào?):  
  _________________________________________________________________________________________________
- **Giải thích cơ chế vật lý:** (Liên hệ với nguyên lý Continuous Batching và sự bão hòa băng thông bộ nhớ VRAM):  
  _________________________________________________________________________________________________
- **Kết luận có thể rút ra:**  
  _________________________________________________________________________________________________
- **Điều chưa thể khẳng định:** (Không suy ra điểm bão hòa production từ một sweep ngắn hoặc một workload duy nhất):  
  _________________________________________________________________________________________________

---

### 5.3 Đồ thị 3: Automatic Prefix Caching A/B Comparison
*(Dán ảnh `results/charts/06_prefix_cache_ttft_p50.png` và `07_prefix_cache_ttft_p95.png`)*

- **Quan sát thấy gì?** (So sánh tỷ lệ giảm TTFT giữa nhóm Shared Prefix và nhóm Control khi bật Cache):  
  _________________________________________________________________________________________________
- **Giải thích cơ chế vật lý:** (Cấu trúc Radix Tree và cơ chế PagedAttention Block Table đã can thiệp như thế nào ở pha Prefill để tạo ra sự khác biệt này?):  
  _________________________________________________________________________________________________
- **Tại sao nhóm Control không được hưởng lợi?**  
  _________________________________________________________________________________________________
- **Điều chưa thể khẳng định:** (Không khái quát lợi ích sang workload khác nếu chưa đo prefix length, hit rate, eviction và routing):  
  _________________________________________________________________________________________________

### 5.4 Đồ thị 4: Prompt Length vs TTFT
*(Dán ảnh `results/charts/08_prompt_length_vs_ttft.png`)*

- **Quan sát thấy gì?** (So sánh TTFT giữa các bucket; trục x là token p50 hoặc ký tự p50 nếu chưa có token count):  
  _________________________________________________________________________________________________
- **Giải thích cơ chế vật lý:** (Prompt dài hơn làm tăng công việc Prefill; kết quả còn phụ thuộc batching, cache state và scheduler):  
  _________________________________________________________________________________________________
- **Kết luận có thể rút ra:**  
  _________________________________________________________________________________________________
- **Điều chưa thể khẳng định:** (Không suy ra quan hệ token–TTFT tuyến tính nếu chưa lặp lại trên nhiều kích thước và workload):  
  _________________________________________________________________________________________________

---

## 6. Phân Tích Điểm Nghẽn Hệ Thống (Bottleneck Analysis)

Dựa trên phần cứng và workload của bạn, thành phần nào là điểm nghẽn chính giới hạn hiệu năng?

- [ ] **Compute-Bound (Pha Prefill):** Prompt đầu vào quá dài, Tensor Cores hoạt động 100% công suất khiến TTFT tăng cao.
- [ ] **Memory-Bandwidth-Bound (Pha Decode):** Quá trình đọc weights và KV Cache chạm trần băng thông VRAM; ghi bandwidth thực tế nếu có, không dùng số minh họa làm bằng chứng.
- [ ] **VRAM Capacity Bound:** Dung lượng VRAM bị đầy khiến không thể tăng thêm Concurrency, vLLM phải đưa request vào hàng đợi chờ hoặc Preemption.
- [ ] **PCIe / Interconnect Bound:** Tốc độ truyền tải dữ liệu giữa CPU và GPU (đặc biệt khi bật Offloading) là rào cản chính.

**Dẫn chứng từ số liệu đo đạc:**  
_________________________________________________________________________________________________
_________________________________________________________________________________________________

---

## 7. Ma Trận Đánh Đổi Kỹ Thuật (Production Trade-off Matrix)

*Điền đánh giá: Thấp / Trung bình / Cao / Rất cao kèm phân tích ngắn gọn.*

| Kỹ thuật tối ưu | Tác động Latency | Tác động Throughput | Tiêu thụ VRAM | Độ phức tạp vận hành | Đánh giá tổng quan |
|---|---|---|---|---|---|
| **Prefix Caching** | | | | | |
| **High Concurrency** | | | | | |
| **CPU Weight Offloading** | | | | | |
| **Quantization** | | | | | |

---

## 8. Đánh Giá SLO & Tối Ưu Hóa Goodput

Ví dụ ngưỡng SLO có thể cấu hình cho bài lab (không tự xem là SLO production phổ quát):
- **SLO TTFT:** P95 TTFT $\le 500 \text{ ms}$
- **SLO TPOT:** P95 TPOT $\le 40 \text{ ms/token}$ ($\approx 25 \text{ tokens/s}$)

### Bảng tính toán Goodput:

| Concurrency | Raw Throughput (req/s) | P95 TTFT (ms) | Đạt SLO TTFT? | P95 TPOT (ms) | Đạt SLO TPOT? | **Goodput (req/s)** | Token source |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| 1 | | | [ ] Có / [ ] Không | | [ ] Có / [ ] Không | | |
| 2 | | | [ ] Có / [ ] Không | | [ ] Có / [ ] Không | | |
| 4 | | | [ ] Có / [ ] Không | | [ ] Có / [ ] Không | | |

> **Nhận xét then chốt:** Mức Concurrency nào mang lại **Goodput cao nhất**? Giải thích tại sao mức Concurrency có Raw Throughput cao nhất chưa chắc đã là mức cấu hình được chọn trong production:  
> _________________________________________________________________________________________________
> _________________________________________________________________________________________________

Nếu token metric không hợp lệ, điền P95 TPOT và Goodput là `NA`; chỉ điền
Goodput `0` khi token metric hợp lệ nhưng level vi phạm ít nhất một cổng SLO.

---

## 9. Khuyến Nghị Vận Hành Cho Hệ Thống Production (Recommendations)

Dựa trên toàn bộ kết quả thực nghiệm, hãy đưa ra khuyến nghị kỹ thuật cụ thể:

1. **Khuyến nghị về Cấu hình vLLM:**
   - `--gpu-memory-utilization`: Nên đặt bao nhiêu và vì sao?
   - `--enable-prefix-caching`: Khi nào bắt buộc phải bật?
   - `--max-model-len`: Cân bằng thế nào giữa nhu cầu context và dung lượng KV Cache?
2. **Khuyến nghị về Thiết Kế Prompt trong Ứng Dụng:**
   - Cấu trúc prompt như thế nào để tối đa hóa Prefix Cache Hit Rate?
3. **Khuyến nghị về Giới Hạn Tải (Admission Control / Rate Limiting):**
   - Đặt ngưỡng Concurrency tối đa ở tầng API Gateway là bao nhiêu để bảo vệ SLO?

---

## 10. Giới Hạn Của Bài Thí Nghiệm (Limitations)

- [ ] Kết quả thực nghiệm phụ thuộc vào phần cứng cụ thể của GPU thử nghiệm.
- [ ] Chưa kiểm thử trên môi trường Multi-GPU phân tán (Tensor Parallelism / Pipeline Parallelism).
- [ ] TPOT phía client là xấp xỉ; cần ghi token source (`api_usage` hoặc `tokenizer_estimate`) và không dùng `output_chunks` làm token.
- [ ] Tập prompt mẫu mang tính giả lập, cần kiểm chứng thêm trên traffic thực tế của người dùng cuối.
- [ ] Cỡ mẫu nhỏ và số lần lặp hạn chế làm P95/P99 không ổn định; chưa có confidence interval hoặc kiểm định giữa nhiều run.

---

## 11. Bảng Tự Đánh Giá Theo Rubric (Self-Assessment)

| Hạng mục | Điểm tối đa | Điểm tự đánh giá | Minh chứng tương ứng |
|---|:---:|:---:|---|
| Setup & API Verification | 15đ | / 15đ | Server chạy chuẩn, endpoint curl hoạt động |
| Benchmark Correctness | 20đ | / 20đ | CSV/JSON đầy đủ, không lỗi timeout |
| TTFT / TPOT Analysis | 15đ | / 15đ | Phân tích rõ bản chất 2 pha phần cứng |
| Prefix Cache Experiment | 15đ | / 15đ | Có đủ số liệu đối chứng A/B OFF vs ON |
| Concurrency Sweep | 10đ | / 10đ | Sweep profile 4GB từ 1 đến 4; mức cao hơn chỉ thử khi không OOM |
| Advanced Experiment (Offload/Quant/Memory) | 10đ | / 10đ | Có số liệu đo đạc thực tế |
| Visualization | 5đ | / 5đ | 8 biểu đồ sắc nét kèm chú thích; biểu đồ token chỉ hợp lệ khi có token metric |
| Production Reasoning & Goodput | 5đ | / 5đ | Tính toán Goodput theo SLO chuẩn xác |
| Report Quality | 5đ | / 5đ | Lập luận logic nhân - quả chặt chẽ |
| **TỔNG ĐIỂM** | **100đ** | **/ 100đ** | |

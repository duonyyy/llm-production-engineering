# TỔNG HỢP SỐ LIỆU THỰC NGHIỆM LAB 01

> **Trạng thái hiện tại: CHƯA CÓ MEASURED RESULT ĐƯỢC XÁC NHẬN.**
>
> File này chỉ được sinh lại sau khi chạy benchmark trên server thật bằng
> `benchmark_streaming.py`, `benchmark_concurrency.py`,
> `benchmark_prefix_cache.py` và `benchmark_prompt_length.py`.
> Không sử dụng các số liệu minh họa cũ trong báo cáo.

## Quy tắc provenance

Mỗi bảng/biểu đồ hợp lệ phải đi kèm:

- raw CSV của từng request;
- summary CSV/JSON được sinh từ raw CSV;
- model ID, vLLM image/version, hardware và cấu hình server;
- log `/v1/models` và snapshot `/metrics`;
- nguồn token count: `api_usage` hoặc `tokenizer_estimate`.

Nếu `completion_tokens` hoặc `prompt_tokens` không có bằng chứng hợp lệ,
các cột `TPOT` và `tokens/s` phải ghi `NA`, không được thay bằng số SSE chunk.

## Cách sinh lại

```bash
python benchmark/analyze_results.py \
  --concurrency-csv results/concurrency_sweep.csv \
  --prefix-off-csv results/prefix_cache_off.csv \
  --prefix-on-csv results/prefix_cache_on.csv \
  --prompt-length-csv results/prompt_length.summary.csv \
  --output-dir results/charts
```

Các PNG đang có trong thư mục này là artifact cũ chưa có raw provenance; chỉ
được đưa vào báo cáo sau khi chạy lại và kiểm tra checksum/nguồn dữ liệu.

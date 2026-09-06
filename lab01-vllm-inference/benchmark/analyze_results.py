#!/usr/bin/env python3
"""
analyze_results.py — Phân tích và trực quan hóa kết quả benchmark Lab 01.

Tạo tối đa 8 biểu đồ chuẩn báo cáo:
    1. 01_concurrency_vs_ttft_p50.png
    2. 02_concurrency_vs_ttft_p95.png
    3. 03_concurrency_vs_e2e_p95.png
    4. 04_concurrency_vs_req_per_sec.png
    5. 05_concurrency_vs_tok_per_sec.png
    6. 06_prefix_cache_ttft_p50.png
    7. 07_prefix_cache_ttft_p95.png
    8. 08_prompt_length_vs_ttft.png

Đồng thời xuất file Markdown tổng kết: results/charts/benchmark_summary.md

Cách dùng:
    python benchmark/analyze_results.py \
        --concurrency-csv results/concurrency_sweep.csv \
        --prefix-off-csv results/prefix_cache_off.csv \
        --prefix-on-csv results/prefix_cache_on.csv \
        --prompt-length-csv results/prompt_length.summary.csv \
        --output-dir results/charts
"""

import argparse
import io
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Thiết lập UTF-8 cho stdout/stderr trên mọi hệ điều hành (tránh UnicodeEncodeError trên Windows cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# Cấu hình thẩm mỹ đồ thị
plt.rcParams.update({
    "figure.figsize": (9, 5.5),
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
    "axes.edgecolor": "#444444",
    "axes.linewidth": 0.8,
})


# ==============================================================================
# Biểu đồ Concurrency Sweep
# ==============================================================================
def plot_concurrency_sweep(df: pd.DataFrame, output_dir: Path) -> None:
    """Tạo 5 biểu đồ Concurrency Sweep với số liệu ghi chú trực quan."""
    if df.empty:
        print("  ⚠ Không có dữ liệu concurrency sweep.")
        return

    x = df["concurrency"].astype(int)

    # 1. Concurrency vs TTFT p50
    fig, ax = plt.subplots()
    ttft_ms_p50 = df["ttft_p50"] * 1000
    ax.plot(x, ttft_ms_p50, "o-", color="#1f77b4", linewidth=2.2, markersize=8, label="TTFT p50")
    for xi, yi in zip(x, ttft_ms_p50):
        ax.annotate(f"{yi:.1f} ms", (xi, yi), textcoords="offset points", xytext=(0, 9), ha="center", fontweight="bold")
    ax.set_xlabel("Concurrency (Số request đồng thời)")
    ax.set_ylabel("TTFT p50 (ms)")
    ax.set_title("Concurrency vs TTFT p50 (Time-to-First-Token)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_ylim(bottom=0, top=max(ttft_ms_p50) * 1.25)
    fig.tight_layout()
    fig.savefig(output_dir / "01_concurrency_vs_ttft_p50.png", dpi=200)
    plt.close(fig)
    print("  ✓ 01_concurrency_vs_ttft_p50.png")

    # 2. Concurrency vs TTFT p95
    fig, ax = plt.subplots()
    ttft_ms_p95 = df["ttft_p95"] * 1000
    ax.plot(x, ttft_ms_p95, "s-", color="#ff7f0e", linewidth=2.2, markersize=8, label="TTFT p95")
    for xi, yi in zip(x, ttft_ms_p95):
        ax.annotate(f"{yi:.1f} ms", (xi, yi), textcoords="offset points", xytext=(0, 9), ha="center", fontweight="bold")
    ax.set_xlabel("Concurrency (Số request đồng thời)")
    ax.set_ylabel("TTFT p95 (ms)")
    ax.set_title("Concurrency vs TTFT p95 (Tail Latency)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_ylim(bottom=0, top=max(ttft_ms_p95) * 1.25)
    fig.tight_layout()
    fig.savefig(output_dir / "02_concurrency_vs_ttft_p95.png", dpi=200)
    plt.close(fig)
    print("  ✓ 02_concurrency_vs_ttft_p95.png")

    # 3. Concurrency vs E2E p95
    fig, ax = plt.subplots()
    e2e_p95 = df["e2e_p95"]
    ax.plot(x, e2e_p95, "^-", color="#9467bd", linewidth=2.2, markersize=8, label="E2E p95")
    for xi, yi in zip(x, e2e_p95):
        ax.annotate(f"{yi:.2f} s", (xi, yi), textcoords="offset points", xytext=(0, 9), ha="center", fontweight="bold")
    ax.set_xlabel("Concurrency (Số request đồng thời)")
    ax.set_ylabel("E2E Latency p95 (giây)")
    ax.set_title("Concurrency vs End-to-End Latency p95", fontweight="bold")
    ax.set_xticks(x)
    ax.set_ylim(bottom=0, top=max(e2e_p95) * 1.25)
    fig.tight_layout()
    fig.savefig(output_dir / "03_concurrency_vs_e2e_p95.png", dpi=200)
    plt.close(fig)
    print("  ✓ 03_concurrency_vs_e2e_p95.png")

    # 4. Concurrency vs Requests/s
    fig, ax = plt.subplots()
    bars = ax.bar(x, df["requests_per_sec"], color="#2ca02c", width=0.45 * np.diff(x).min() if len(x) > 1 else 0.4, edgecolor="#1e701e")
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.05 * max(df["requests_per_sec"]), f"{yval:.2f}", ha='center', va='bottom', fontweight='bold')
    ax.set_xlabel("Concurrency (Số request đồng thời)")
    ax.set_ylabel("Requests/s")
    ax.set_title("Concurrency vs Request Throughput (req/s)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_ylim(bottom=0, top=max(df["requests_per_sec"]) * 1.25 if max(df["requests_per_sec"]) > 0 else 1)
    fig.tight_layout()
    fig.savefig(output_dir / "04_concurrency_vs_req_per_sec.png", dpi=200)
    plt.close(fig)
    print("  ✓ 04_concurrency_vs_req_per_sec.png")

    # 5. Concurrency vs Tokens/s
    token_series = pd.to_numeric(df["tokens_per_sec"], errors="coerce")
    if token_series.notna().sum() == 0:
        print("  ⚠ Không có token throughput hợp lệ; bỏ qua biểu đồ 05.")
        return
    token_df = df.loc[token_series.notna()].copy()
    token_df["tokens_per_sec"] = token_series[token_series.notna()]
    token_x = token_df["concurrency"].astype(int)
    fig, ax = plt.subplots()
    bars = ax.bar(token_x, token_df["tokens_per_sec"], color="#d62728", width=0.45 * np.diff(token_x).min() if len(token_x) > 1 else 0.4, edgecolor="#8b1a1a")
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.05 * max(token_df["tokens_per_sec"]), f"{yval:.1f}", ha='center', va='bottom', fontweight='bold')
    ax.set_xlabel("Concurrency (Số request đồng thời)")
    ax.set_ylabel("Output Tokens/s")
    ax.set_title("Concurrency vs Output Token Throughput (tokens/s)", fontweight="bold")
    ax.set_xticks(token_x)
    ax.set_ylim(bottom=0, top=max(token_df["tokens_per_sec"]) * 1.25 if max(token_df["tokens_per_sec"]) > 0 else 1)
    fig.tight_layout()
    fig.savefig(output_dir / "05_concurrency_vs_tok_per_sec.png", dpi=200)
    plt.close(fig)
    print("  ✓ 05_concurrency_vs_tok_per_sec.png")


# ==============================================================================
# Biểu đồ Prefix Cache ON/OFF
# ==============================================================================
def plot_prefix_cache_comparison(
    df_off: pd.DataFrame | None,
    df_on: pd.DataFrame | None,
    output_dir: Path,
) -> None:
    """So sánh TTFT giữa Prefix Cache OFF và ON."""
    if df_off is None or df_on is None:
        print("  ⚠ Thiếu dữ liệu prefix cache ON hoặc OFF, bỏ qua biểu đồ so sánh.")
        return

    labels = []
    off_p50, on_p50 = [], []
    off_p95, on_p95 = [], []

    for category in ["shared", "control"]:
        sub_off = df_off[df_off["label"].str.contains(category) & (df_off["success"] == True)]
        sub_on = df_on[df_on["label"].str.contains(category) & (df_on["success"] == True)]

        if sub_off.empty or sub_on.empty:
            continue

        cat_title = "Shared Prefix" if category == "shared" else "Control (Diverse)"
        labels.append(cat_title)
        off_p50.append(np.percentile(sub_off["ttft"], 50) * 1000)
        on_p50.append(np.percentile(sub_on["ttft"], 50) * 1000)
        off_p95.append(np.percentile(sub_off["ttft"], 95) * 1000)
        on_p95.append(np.percentile(sub_on["ttft"], 95) * 1000)

    if not labels:
        print("  ⚠ Không tìm thấy nhãn 'shared' hoặc 'control' trong dữ liệu prefix cache.")
        return

    x = np.arange(len(labels))
    width = 0.32

    # TTFT p50 comparison
    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width / 2, off_p50, width, label="Prefix Cache OFF", color="#e74c3c", edgecolor="#c0392b")
    rects2 = ax.bar(x + width / 2, on_p50, width, label="Prefix Cache ON", color="#2ecc71", edgecolor="#27ae60")

    for bar in rects1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for bar in rects2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xlabel("Workload Type")
    ax.set_ylabel("TTFT p50 (ms)")
    ax.set_title("Automatic Prefix Caching: TTFT p50 Comparison (A/B Test)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight="bold")
    ax.set_ylim(bottom=0, top=max(off_p50 + on_p50) * 1.3)
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(output_dir / "06_prefix_cache_ttft_p50.png", dpi=200)
    plt.close(fig)
    print("  ✓ 06_prefix_cache_ttft_p50.png")

    # TTFT p95 comparison
    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width / 2, off_p95, width, label="Prefix Cache OFF", color="#e74c3c", edgecolor="#c0392b")
    rects2 = ax.bar(x + width / 2, on_p95, width, label="Prefix Cache ON", color="#2ecc71", edgecolor="#27ae60")

    for bar in rects1:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for bar in rects2:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f} ms", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xlabel("Workload Type")
    ax.set_ylabel("TTFT p95 (ms)")
    ax.set_title("Automatic Prefix Caching: TTFT p95 Comparison (A/B Test)", fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontweight="bold")
    ax.set_ylim(bottom=0, top=max(off_p95 + on_p95) * 1.3)
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(output_dir / "07_prefix_cache_ttft_p95.png", dpi=200)
    plt.close(fig)
    print("  ✓ 07_prefix_cache_ttft_p95.png")


def plot_prompt_length(df: pd.DataFrame | None, output_dir: Path) -> None:
    """Vẽ TTFT theo prompt length từ summary đã đo.

    Ưu tiên token count. Nếu tokenizer/API usage không có, dùng ký tự nhưng
    ghi rõ trên trục để không đánh đồng ký tự với token.
    """

    if df is None or df.empty:
        print("  ⚠ Thiếu prompt-length summary, bỏ qua biểu đồ.")
        return

    x_column = "prompt_tokens_p50" if df["prompt_tokens_p50"].notna().all() else "prompt_chars_p50"
    x_label = "Prompt tokens (p50)" if x_column == "prompt_tokens_p50" else "Prompt characters (p50; token count unavailable)"
    plot_df = df.sort_values(x_column)
    fig, ax = plt.subplots()
    ax.plot(plot_df[x_column], plot_df["ttft_p50"] * 1000, "o-", label="TTFT p50")
    ax.plot(plot_df[x_column], plot_df["ttft_p95"] * 1000, "s--", label="TTFT p95")
    for _, row in plot_df.iterrows():
        ax.annotate(str(row["bucket"]), (row[x_column], row["ttft_p95"] * 1000), textcoords="offset points", xytext=(5, 5))
    ax.set_xlabel(x_label)
    ax.set_ylabel("TTFT (ms)")
    ax.set_title("Prompt Length vs TTFT")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "08_prompt_length_vs_ttft.png", dpi=200)
    plt.close(fig)
    print("  ✓ 08_prompt_length_vs_ttft.png")


# ==============================================================================
# Xuất Báo Cáo Markdown Tổng Hợp
# ==============================================================================
def export_markdown_summary(
    df_conc: pd.DataFrame | None,
    df_off: pd.DataFrame | None,
    df_on: pd.DataFrame | None,
    df_prompt: pd.DataFrame | None,
    output_dir: Path,
) -> None:
    lines = [
        "# TỔNG HỢP SỐ LIỆU THỰC NGHIỆM LAB 01",
        "",
        "> File tự động sinh bởi `analyze_results.py`. Dùng để dán trực tiếp vào báo cáo thực nghiệm.",
        "> Chỉ xem là measured result khi giữ kèm các CSV nguồn và log/version manifest. Giá trị `NA` nghĩa là metric chưa có bằng chứng hợp lệ.",
        "",
        "## Cổng kiểm tra dữ liệu đã nạp",
        "",
        f"- Concurrency summary: {'có' if df_conc is not None and not df_conc.empty else 'thiếu'}",
        f"- Prefix OFF raw: {'có' if df_off is not None and not df_off.empty else 'thiếu'}",
        f"- Prefix ON raw: {'có' if df_on is not None and not df_on.empty else 'thiếu'}",
        f"- Prompt-length summary: {'có' if df_prompt is not None and not df_prompt.empty else 'thiếu'}",
        "- Version, hardware, server log, `/v1/models`, `/metrics` và checksum phải đối chiếu riêng trong `report/lab_report_template.md`.",
        "",
    ]

    if df_conc is not None and not df_conc.empty:
        lines.extend([
            "## 1. Kết Quả Concurrency Sweep",
            "",
            "| Concurrency | Requests | TTFT p50 (ms) | TTFT p95 (ms) | E2E p50 (s) | E2E p95 (s) | Req/s | Tok/s | Error % |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ])
        for _, row in df_conc.iterrows():
            lines.append(
                f"| {int(row['concurrency'])} | {int(row['requests'])} | "
                f"{row['ttft_p50']*1000:.1f} | {row['ttft_p95']*1000:.1f} | "
                f"{row['e2e_p50']:.3f} | {row['e2e_p95']:.3f} | "
                f"{row['requests_per_sec']:.2f} | "
                f"{row['tokens_per_sec'] if pd.notna(row['tokens_per_sec']) else 'NA'} | "
                f"{row['error_rate']*100:.1f}% |"
            )
        lines.append("")

    if df_off is not None and df_on is not None:
        lines.extend([
            "## 2. Kết Quả So Sánh Prefix Caching (A/B Test)",
            "",
            "| Cấu hình | Workload | Số requests | TTFT p50 (ms) | TTFT p95 (ms) | E2E p50 (s) | Token metric |",
            "|---|---|---:|---:|---:|---:|---|",
        ])
        for name, df_item in [("Prefix Cache OFF", df_off), ("Prefix Cache ON", df_on)]:
            for cat in ["shared", "control"]:
                sub = df_item[df_item["label"].str.contains(cat) & (df_item["success"] == True)]
                if not sub.empty:
                    p50 = np.percentile(sub["ttft"], 50) * 1000
                    p95 = np.percentile(sub["ttft"], 95) * 1000
                    e2e_p50 = np.percentile(sub["e2e_latency"], 50)
                    token_source = ", ".join(sorted(set(sub["token_count_source"].astype(str)))) if "token_count_source" in sub.columns else "unknown"
                    lines.append(f"| {name} | {cat.capitalize()} | {len(sub)} | {p50:.1f} | {p95:.1f} | {e2e_p50:.3f} | {token_source} |")
        lines.append("")

    if df_prompt is not None and not df_prompt.empty:
        lines.extend([
            "## 3. Kết quả Prompt Length",
            "",
            "| Bucket | Target chars | Prompt chars p50 | Prompt tokens p50 | TTFT p50 (ms) | TTFT p95 (ms) | Token metric complete |",
            "|---|---:|---:|---:|---:|---:|---|",
        ])
        for _, row in df_prompt.iterrows():
            lines.append(
                f"| {row['bucket']} | {int(row['target_prompt_chars'])} | "
                f"{row['prompt_chars_p50'] if pd.notna(row['prompt_chars_p50']) else 'NA'} | "
                f"{row['prompt_tokens_p50'] if pd.notna(row['prompt_tokens_p50']) else 'NA'} | "
                f"{row['ttft_p50']*1000 if pd.notna(row['ttft_p50']) else 'NA'} | "
                f"{row['ttft_p95']*1000 if pd.notna(row['ttft_p95']) else 'NA'} | "
                f"{row['token_metrics_complete']} |"
            )
        lines.append("")

    summary_file = output_dir / "benchmark_summary.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  ✓ Markdown summary: {summary_file}")


# ==============================================================================
# Main
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Phân tích kết quả benchmark Lab 01.")
    parser.add_argument(
        "--concurrency-csv",
        default="results/concurrency_sweep.csv",
        help="CSV từ benchmark_concurrency.py",
    )
    parser.add_argument(
        "--prefix-off-csv",
        default="results/prefix_cache_off.csv",
        help="CSV khi Prefix Cache OFF",
    )
    parser.add_argument(
        "--prefix-on-csv",
        default="results/prefix_cache_on.csv",
        help="CSV khi Prefix Cache ON",
    )
    parser.add_argument(
        "--prompt-length-csv",
        default="results/prompt_length.summary.csv",
        help="Summary CSV từ benchmark_prompt_length.py",
    )
    parser.add_argument(
        "--output-dir",
        default="results/charts",
        help="Thư mục lưu biểu đồ PNG và summary",
    )

    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("================================================================")
    print("  LAB 01 — PHÂN TÍCH VÀ TRỰC QUAN HÓA KẾT QUẢ")
    print(f"  Output folder : {output_dir}")
    print("================================================================")

    df_conc = None
    if Path(args.concurrency_csv).exists():
        print(f"Đọc dữ liệu concurrency: {args.concurrency_csv}")
        df_conc = pd.read_csv(args.concurrency_csv)
        plot_concurrency_sweep(df_conc, output_dir)
    else:
        print(f"⚠ Không tìm thấy {args.concurrency_csv}")

    df_off = None
    df_on = None
    if Path(args.prefix_off_csv).exists():
        print(f"Đọc dữ liệu Prefix Cache OFF: {args.prefix_off_csv}")
        df_off = pd.read_csv(args.prefix_off_csv)
    else:
        print(f"⚠ Không tìm thấy {args.prefix_off_csv}")

    if Path(args.prefix_on_csv).exists():
        print(f"Đọc dữ liệu Prefix Cache ON: {args.prefix_on_csv}")
        df_on = pd.read_csv(args.prefix_on_csv)
    else:
        print(f"⚠ Không tìm thấy {args.prefix_on_csv}")

    df_prompt = None
    if Path(args.prompt_length_csv).exists():
        print(f"Đọc dữ liệu prompt length: {args.prompt_length_csv}")
        df_prompt = pd.read_csv(args.prompt_length_csv)
        plot_prompt_length(df_prompt, output_dir)
    else:
        print(f"⚠ Không tìm thấy {args.prompt_length_csv}")

    if df_off is not None or df_on is not None:
        plot_prefix_cache_comparison(df_off, df_on, output_dir)

    # Xuất Markdown summary
    export_markdown_summary(df_conc, df_off, df_on, df_prompt, output_dir)

    print("\n✓ Hoàn tất phân tích dữ liệu!")


if __name__ == "__main__":
    main()

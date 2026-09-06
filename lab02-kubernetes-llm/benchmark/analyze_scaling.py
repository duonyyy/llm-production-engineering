#!/usr/bin/env python3
"""Analyze raw Lab 02 load-generator CSV files without fabricating missing values."""

from __future__ import annotations

import argparse
import csv
import math
import re
from pathlib import Path
from typing import Iterable


NA = "NA"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", required=True, help="label=path.csv, for example c1=results/c1.csv")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--chart", type=Path)
    parser.add_argument("--slo-ttft", type=float, default=None)
    parser.add_argument("--slo-e2e", type=float, default=None)
    parser.add_argument("--max-error-rate", type=float, default=None)
    return parser.parse_args()


def as_float(value: str) -> float | None:
    if not value or value == NA:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def percentile(values: Iterable[float], p: float) -> float | None:
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def format_number(value: float | None) -> str:
    return NA if value is None else f"{value:.6f}"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    return rows


def analyze(label: str, path: Path, args: argparse.Namespace) -> dict[str, str]:
    rows = read_rows(path)
    successful = [row for row in rows if row.get("status") == "ok"]
    ttft = [value for row in successful if (value := as_float(row.get("ttft_s", ""))) is not None]
    e2e = [value for row in successful if (value := as_float(row.get("e2e_latency_s", ""))) is not None]
    starts = [value for row in rows if (value := as_float(row.get("started_at", ""))) is not None]
    ends = [value for row in rows if (value := as_float(row.get("ended_at", ""))) is not None]
    duration = max(ends) - min(starts) if starts and ends and max(ends) >= min(starts) else None
    error_rate = (len(rows) - len(successful)) / len(rows) if rows else None
    p95_ttft = percentile(ttft, 0.95)
    p95_e2e = percentile(e2e, 0.95)
    good = 0
    for row in successful:
        row_ttft = as_float(row.get("ttft_s", ""))
        row_e2e = as_float(row.get("e2e_latency_s", ""))
        ttft_ok = args.slo_ttft is None or (row_ttft is not None and row_ttft <= args.slo_ttft)
        e2e_ok = args.slo_e2e is None or (row_e2e is not None and row_e2e <= args.slo_e2e)
        if ttft_ok and e2e_ok:
            good += 1
    slo_pass = "NOT_EVALUATED"
    if args.slo_ttft is not None or args.slo_e2e is not None or args.max_error_rate is not None:
        checks = []
        if args.slo_ttft is not None:
            checks.append(p95_ttft is not None and p95_ttft <= args.slo_ttft)
        if args.slo_e2e is not None:
            checks.append(p95_e2e is not None and p95_e2e <= args.slo_e2e)
        if args.max_error_rate is not None:
            checks.append(error_rate is not None and error_rate <= args.max_error_rate)
        slo_pass = str(all(checks)).lower()
    match = re.search(r"(?:^|[^0-9])c(\d+)(?:[^0-9]|$)", label, flags=re.IGNORECASE)
    return {
        "label": label,
        "file": str(path),
        "concurrency": match.group(1) if match else NA,
        "total_requests": str(len(rows)),
        "successful_requests": str(len(successful)),
        "error_rate": format_number(error_rate),
        "ttft_p50_s": format_number(percentile(ttft, 0.50)),
        "ttft_p95_s": format_number(p95_ttft),
        "ttft_p99_s": format_number(percentile(ttft, 0.99)),
        "e2e_p95_s": format_number(p95_e2e),
        "requests_per_second": format_number(len(successful) / duration if duration and duration > 0 else None),
        "goodput_per_second": format_number(good / duration if duration and duration > 0 else None),
        "slo_pass": slo_pass,
    }


def maybe_chart(rows: list[dict[str, str]], path: Path | None) -> None:
    if path is None:
        return
    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise SystemExit("--chart needs matplotlib; omit --chart for CSV-only analysis") from exc
    xs, ys = [], []
    for row in rows:
        x = as_float(row["concurrency"])
        y = as_float(row["ttft_p95_s"])
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    fig, ax = plt.subplots(figsize=(7, 4))
    if xs:
        order = sorted(zip(xs, ys))
        ax.plot([item[0] for item in order], [item[1] for item in order], marker="o")
    ax.set_xlabel("Concurrency")
    ax.set_ylabel("TTFT p95 (s)")
    ax.set_title("Lab 02: TTFT p95 vs concurrency")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    results: list[dict[str, str]] = []
    for spec in args.inputs:
        if "=" not in spec:
            raise SystemExit(f"input must be label=path: {spec}")
        label, raw_path = spec.split("=", 1)
        results.append(analyze(label, Path(raw_path), args))
    fields = list(results[0].keys())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    maybe_chart(results, args.chart)
    print(f"wrote {args.output} ({len(results)} conditions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

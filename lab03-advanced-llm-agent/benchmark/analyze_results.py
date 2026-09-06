"""Summarize measured rows only; NA and design rows never become statistics."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path


def number(value: str) -> float | None:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else None
    except (TypeError, ValueError):
        return None


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(Path(__file__).parents[1] / "results"))
    parser.add_argument("--output", default=str(Path(__file__).parents[1] / "results" / "analysis.md"))
    args = parser.parse_args()
    input_path = Path(args.input)
    files = [input_path] if input_path.is_file() else sorted(input_path.glob("*.csv"))
    lines = ["# Lab 03 Results Analysis", "", "Only rows with `status=OK` and numeric values are summarized. Missing endpoints remain `NA`.", ""]
    for file in files:
        with file.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        ok = [row for row in rows if row.get("status") == "OK"]
        lines.extend([f"## {file.name}", "", f"- raw rows: {len(rows)}", f"- measured rows: {len(ok)}", f"- non-measured rows: {len(rows) - len(ok)}"])
        for field in ("ttft_ms", "tpot_ms", "e2e_ms", "cached_tokens", "kv_transfer_ms"):
            values = [parsed for row in ok if (parsed := number(row.get(field, ""))) is not None]
            if values:
                lines.append(f"- {field}: n={len(values)}, p50={percentile(values, 0.50):.3f}, p95={percentile(values, 0.95):.3f}")
            else:
                lines.append(f"- {field}: NA (no measured numeric values)")
        lines.append("")
    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

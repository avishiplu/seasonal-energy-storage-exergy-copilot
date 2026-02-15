# src/simulation/export_timeseries.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List


def rows_to_csv(rows: List[Dict[str, Any]], path: str | Path) -> Path:
    """
    Write a list of dict rows to a CSV file.

    - If rows is empty: write an empty CSV with no rows (and no headers).
      (Caller should ensure at least one row if headers are required.)
    - If rows is non-empty: headers are the union of keys seen in the first row.
      (Assumes consistent schema across rows.)
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        # Write an empty file (0 bytes) to make behavior explicit and testable
        out_path.write_text("", encoding="utf-8")
        return out_path

    # Use keys from the first row as the canonical header order
    fieldnames = list(rows[0].keys())

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return out_path

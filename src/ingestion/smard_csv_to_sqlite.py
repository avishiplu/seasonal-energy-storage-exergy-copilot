# src/ingestion/smard_csv_to_sqlite.py
from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Iterable, Tuple

from src.cache.external_cache import init_cache, upsert_prices


def _to_utc_iso(s: str) -> str:
    s = s.strip()

    fmts = [
        "%b %d, %Y %I:%M %p",  # Jan 1, 2022 12:00 AM
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%d.%m.%Y %H:%M",
    ]

    last = None
    for fmt in fmts:
        try:
            dt = datetime.datetime.strptime(s, fmt)
            dt = dt.replace(minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc)
            return dt.isoformat()
        except Exception as e:
            last = e
    raise ValueError(f"Unrecognized datetime format: {s!r}") from last


def import_smard_csv_to_sqlite(
    csv_path: str | Path,
    market: str = "DE-LU",
    source: str = "SMARD",
) -> int:
    """
    Reads SMARD CSV (download center) and upserts hourly prices into SQLite cache.

    Returns:
        number of inserted rows
    """
    init_cache()

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)

        def find_col(substr: str) -> int | None:
            for i, h in enumerate(header):
                if substr.lower() in h.lower():
                    return i
            return None

        i_start = find_col("Start date")
        i_price = find_col("Germany/Luxembourg")  # your DE-LU column

        if i_start is None or i_price is None:
            raise RuntimeError(f"Required columns not found. Header sample: {header[:10]}")

        rows: list[Tuple[str, str, float, str]] = []

        for r in reader:
            if not r or len(r) <= max(i_start, i_price):
                continue

            ts = r[i_start].strip()
            val = r[i_price].strip().replace(",", ".")

            if not ts or not val:
                continue

            try:
                price = float(val)
            except ValueError:
                continue

            iso = _to_utc_iso(ts)
            rows.append((market, iso, price, source))

    upsert_prices(rows)
    return len(rows)

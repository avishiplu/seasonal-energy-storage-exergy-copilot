# src/ingestion/smard_prefill.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


from src.ingestion.smard_download_manager import download_market_data_csv
from src.ingestion.smard_csv_to_sqlite import import_smard_csv_to_sqlite

from src.cache.external_cache import has_any_price


@dataclass(frozen=True)
class SmardPrefillResult:
    csv_path: str
    bytes_written: int
    rows_imported: int


def smard_prefill_from_downloadcenter(payload, csv_path="data/cache/smard_market_data.csv"):
    if has_any_price(payload["request_form"][0]["region"]):
        return SmardPrefillResult(csv_path=str(csv_path), bytes_written=0, rows_imported=0)

    res = download_market_data_csv(payload=payload, out_path=csv_path)
    n = import_smard_csv_to_sqlite(csv_path=csv_path)
    return SmardPrefillResult(csv_path=str(res.out_path), bytes_written=int(res.bytes_written), rows_imported=int(n))

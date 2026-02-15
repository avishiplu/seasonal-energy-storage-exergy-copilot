# src/ingestion/smard_download_manager.py

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import requests


SMARD_DOWNLOAD_URL = "https://www.smard.de/nip-download-manager/nip/download/market-data"


@dataclass(frozen=True)
class SmardDownloadResult:
    out_path: Path
    bytes_written: int
    status_code: int
    content_type: str | None


def download_market_data_csv(payload: Dict[str, Any], out_path: str | Path, timeout_s: int = 180) -> SmardDownloadResult:
    """
    Downloads SMARD market data via the Download Center (nip-download-manager).
    This is the SAME endpoint you successfully used in the terminal.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    r = requests.post(
        SMARD_DOWNLOAD_URL,
        json=payload,
        headers={
            "Accept": "application/octet-stream,*/*",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
        timeout=timeout_s,
    )
    r.raise_for_status()

    out_path.write_bytes(r.content)

    return SmardDownloadResult(
        out_path=out_path,
        bytes_written=out_path.stat().st_size,
        status_code=r.status_code,
        content_type=r.headers.get("Content-Type"),
    )

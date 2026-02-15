from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import requests

from src.ingestion.dwd_station_select import DwdStation

DWD_TU_HISTORICAL_DIR = (
    "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
    "climate/hourly/air_temperature/historical/"
)


@dataclass(frozen=True)
class TuRow:
    time_utc: str
    temperature_C: float


def _download_bytes(url: str, timeout_s: int = 60) -> bytes:
    r = requests.get(url, timeout=timeout_s)
    r.raise_for_status()
    return r.content


def _find_historical_zip_name_for_station(station_id: int) -> str:
    """
    DWD historical directory contains ZIP names like:
      stundenwerte_TU_01975_19490101_20211231_hist.zip   (example pattern)
    We DO NOT guess FROM/TO from station description.
    Instead we list the directory and pick the matching file.
    """
    html = _download_bytes(DWD_TU_HISTORICAL_DIR).decode("utf-8", errors="ignore")

    sid = f"{station_id:05d}"

    # Find all candidate ZIP names for this station
    pattern = re.compile(rf"(stundenwerte_TU_{sid}_\d{{8}}_\d{{8}}_hist\.zip)")
    matches = pattern.findall(html)

    if not matches:
        raise RuntimeError(
            f"No historical TU ZIP found in directory listing for station {sid}. "
            f"Check station_id or dataset availability."
        )

    # If multiple exist, take the one with the latest TO date (max yyyymmdd)
    def _to_date(zipname: str) -> int:
        # stundenwerte_TU_<sid>_<from>_<to>_hist.zip
        parts = zipname.split("_")
        return int(parts[4])  # <to>

    matches = sorted(set(matches), key=_to_date, reverse=True)
    return matches[0]


def _find_data_file_name(z: zipfile.ZipFile) -> str:
    for name in z.namelist():
        if re.search(r"produkt_.*tu.*stunde.*\.txt$", name, re.IGNORECASE):
            return name
    for name in z.namelist():
        ln = name.lower()
        if ln.endswith(".txt") and "beschreibung" not in ln and "meta" not in ln:
            return name
    raise RuntimeError(f"No TU data file found. ZIP contains: {z.namelist()}")


def _parse_rows(raw_text: str, start_utc: datetime, end_utc: datetime) -> List[TuRow]:
    lines = raw_text.splitlines()
    if not lines:
        return []

    header = lines[0].split(";")
    if "MESS_DATUM" not in header or "TT_TU" not in header:
        raise RuntimeError(f"Unexpected TU header columns: {header}")

    idx_time = header.index("MESS_DATUM")
    idx_temp = header.index("TT_TU")

    out: List[TuRow] = []

    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(";")
        if len(parts) <= max(idx_time, idx_temp):
            continue

        mess = parts[idx_time].strip()
        temp_s = parts[idx_temp].strip()

        try:
            temp = float(temp_s)
        except ValueError:
            continue

        if temp <= -900:
            continue

        dt = datetime.strptime(mess, "%Y%m%d%H").replace(tzinfo=timezone.utc)

        if dt < start_utc or dt >= end_utc:
            continue

        out.append(TuRow(time_utc=dt.isoformat(), temperature_C=temp))

    out.sort(key=lambda r: r.time_utc)
    return out


def fetch_tu_hourly_rows_for_station_historical(
    station: DwdStation,
    start_utc: datetime,
    end_utc: datetime,
) -> List[TuRow]:
    """
    1) Discover correct ZIP filename for station via historical directory listing
    2) Download ZIP
    3) Parse hourly temperature within [start_utc, end_utc)
    """
    zip_name = _find_historical_zip_name_for_station(station.station_id)
    url = DWD_TU_HISTORICAL_DIR + zip_name

    zip_bytes = _download_bytes(url)
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    data_file = _find_data_file_name(z)

    raw = z.read(data_file).decode("latin-1", errors="ignore")
    return _parse_rows(raw, start_utc=start_utc, end_utc=end_utc)

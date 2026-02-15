from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date
from typing import List, Tuple

import requests


# IMPORTANT:
# Use HISTORICAL station description so we can later download historical ZIPs for years like 2021–2023.
# (recent station list is not guaranteed to match historical file coverage)
DWD_TU_STATIONS_URL = (
    "https://opendata.dwd.de/climate_environment/CDC/observations_germany/"
    "climate/hourly/air_temperature/historical/TU_Stundenwerte_Beschreibung_Stationen.txt"
)


@dataclass(frozen=True)
class DwdStation:
    station_id: int
    from_yyyymmdd: int
    to_yyyymmdd: int
    height_m: int
    lat: float
    lon: float
    name: str
    state: str


def _yyyymmdd(d: date) -> int:
    return int(d.strftime("%Y%m%d"))


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def fetch_tu_station_list(timeout_s: int = 30) -> List[DwdStation]:
    """
    Downloads and parses the DWD TU (hourly air temperature) station description list (HISTORICAL).
    """
    r = requests.get(DWD_TU_STATIONS_URL, timeout=timeout_s)
    r.raise_for_status()
    text = r.text

    stations: List[DwdStation] = []

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Station lines start with a 5-digit station ID
        if not re.match(r"^\d{5}\s", line):
            continue

        # Expected columns:
        # STATIONS_ID VON_DATUM BIS_DATUM STATIONSHOEHE GEOGR.BREITE GEOGR.LAENGE STATIONSNAME BUNDESLAND
        parts = line.split()
        if len(parts) < 7:
            continue

        station_id = int(parts[0])
        from_yyyymmdd = int(parts[1])
        to_yyyymmdd = int(parts[2])
        height_m = int(parts[3])
        lat = float(parts[4])
        lon = float(parts[5])

        # Remaining tokens: station name can have spaces; last token is state
        state = parts[-1]
        name_tokens = parts[6:-1]
        name = " ".join(name_tokens) if name_tokens else ""

        stations.append(
            DwdStation(
                station_id=station_id,
                from_yyyymmdd=from_yyyymmdd,
                to_yyyymmdd=to_yyyymmdd,
                height_m=height_m,
                lat=lat,
                lon=lon,
                name=name,
                state=state,
            )
        )

    if not stations:
        raise RuntimeError("No stations parsed from DWD TU historical station list. Check URL/format.")

    return stations


def select_best_station(
    stations: List[DwdStation],
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> Tuple[DwdStation, float]:
    """
    Picks the nearest station that fully covers [start, end] (inclusive).
    Returns: (station, distance_km)
    """
    start_i = _yyyymmdd(start)
    end_i = _yyyymmdd(end)

    candidates: List[Tuple[DwdStation, float]] = []

    for st in stations:
        if st.from_yyyymmdd <= start_i and st.to_yyyymmdd >= end_i:
            dist = _haversine_km(lat, lon, st.lat, st.lon)
            candidates.append((st, dist))

    if not candidates:
        raise RuntimeError(
            "No TU historical station covers the requested date range. "
            "Try a different date range or verify the station list."
        )

    candidates.sort(key=lambda x: x[1])
    return candidates[0]


def pick_station_for_location_and_range(
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> Tuple[DwdStation, float]:
    stations = fetch_tu_station_list()
    return select_best_station(stations, lat, lon, start, end)

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from src.cache.external_cache import init_cache, has_weather, insert_weather
from src.ingestion.dwd_station_select import pick_station_for_location_and_range
from src.ingestion.dwd_fetch_tu_hourly import fetch_tu_hourly_rows_for_station_historical


def _iter_hours(start_utc: datetime, end_utc: datetime):
    t = start_utc
    while t < end_utc:
        yield t
        t += timedelta(hours=1)


def _all_hours_cached(location: str, start_utc: datetime, end_utc: datetime) -> bool:
    for t in _iter_hours(start_utc, end_utc):
        ts = t.isoformat()
        if not has_weather(location, ts):
            return False
    return True


def prefill_weather_dwd_hourly_temperature(
    location: str,
    lat: float,
    lon: float,
    start_utc: datetime,
    end_utc: datetime,
) -> Tuple[int, int]:
    """
    Fetch-missing-only weather prefill.
    Saves to SQLite: weather(location, timestamp, temperature_K, source)

    Returns:
        (inserted_count, skipped_count)
    """
    init_cache()

    start_utc = start_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_utc = end_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)

    # ✅ EARLY RETURN: if the full requested range is already cached,
    # do NOT touch the network at all.
    if _all_hours_cached(location, start_utc, end_utc):
        total = int((end_utc - start_utc).total_seconds() // 3600)
        return 0, total

    # Only now do we touch DWD network
    st, _dist = pick_station_for_location_and_range(
        lat, lon, start_utc.date(), (end_utc - timedelta(hours=1)).date()
    )

    rows = fetch_tu_hourly_rows_for_station_historical(st, start_utc, end_utc)

    inserted = 0
    skipped = 0

    for r in rows:
        ts = r.time_utc  # ISO with +00:00

        if has_weather(location, ts):
            skipped += 1
            continue

        temp_K = float(r.temperature_C) + 273.15
        insert_weather(location, ts, temp_K)
        inserted += 1

    return inserted, skipped

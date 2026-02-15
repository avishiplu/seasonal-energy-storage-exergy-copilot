# src/simulation/demo_hourly_prices.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.cache.external_cache import init_cache
from src.retrieval.external_inputs import price_at_hour_external


def iter_hours(start_utc: datetime, end_utc: datetime):
    t = start_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    while t < end_utc:
        yield t
        t += timedelta(hours=1)


def main():
    init_cache()

    start = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2022, 1, 1, 3, 0, tzinfo=timezone.utc)

    for t in iter_hours(start, end):
        price_vs = price_at_hour_external(market="DE-LU", hour_utc=t)
        print(t.isoformat(), price_vs.value, price_vs.unit, price_vs.source_type.value)


if __name__ == "__main__":
    main()

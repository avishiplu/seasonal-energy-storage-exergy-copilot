from __future__ import annotations

from datetime import datetime, timezone

from src.cache.external_cache import get_price, get_weather
from src.core.values import external_value, ValueSpec


def price_at_hour_external(market: str, hour_utc: datetime) -> ValueSpec:
    """
    Read hourly electricity price from local SQLite cache and return as EXTERNAL ValueSpec.
    hour_utc is rounded to the hour and stored/queried as UTC ISO format.
    """
    hour_utc = hour_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    iso = hour_utc.isoformat()

    p = get_price(market, iso)
    if p is None:
        raise RuntimeError(
            f"Missing cached price for market={market} at {iso}. "
            f"Run SMARD download+cache first (Phase 5 external data step)."
        )

    return external_value(
        value=float(p),
        unit="EUR/MWh",
        meta={
            "source": "SMARD",
            "market": market,
            "time_range": iso,
        },
    )


def ambient_temperature_at_hour_external(
    location: str,
    hour_utc: datetime,
) -> ValueSpec:
    """
    Read hourly ambient temperature from local SQLite cache and return as EXTERNAL ValueSpec.
    Temperature is stored and returned in Kelvin (K).
    """
    hour_utc = hour_utc.replace(minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    iso = hour_utc.isoformat()

    T = get_weather(location, iso)
    if T is None:
        raise RuntimeError(
            f"Missing cached weather for location={location} at {iso}. "
            f"Run DWD weather prefill first (Phase 5 external data step)."
        )

    return external_value(
        value=float(T),
        unit="K",
        meta={
            "source": "DWD",
            "location": location,
            "time_range": iso,
        },
    )

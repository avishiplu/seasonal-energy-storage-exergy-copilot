from datetime import datetime, timezone
import requests

from src.ingestion.dwd_weather_prefill import prefill_weather_dwd_hourly_temperature


def test_weather_no_redownload(monkeypatch):
    # First run: allow network (fills DB)
    ins, sk = prefill_weather_dwd_hourly_temperature(
        location="Hamburg",
        lat=53.5511,
        lon=9.9937,
        start_utc=datetime(2022, 1, 1, tzinfo=timezone.utc),
        end_utc=datetime(2022, 1, 2, tzinfo=timezone.utc),
    )
    assert ins + sk == 24

    # Second run: block ALL network
    def _blocked_get(*args, **kwargs):
        raise RuntimeError("Network call detected on second run (should not happen)")

    monkeypatch.setattr(requests, "get", _blocked_get)

    ins2, sk2 = prefill_weather_dwd_hourly_temperature(
        location="Hamburg",
        lat=53.5511,
        lon=9.9937,
        start_utc=datetime(2022, 1, 1, tzinfo=timezone.utc),
        end_utc=datetime(2022, 1, 2, tzinfo=timezone.utc),
    )

    assert ins2 == 0
    assert sk2 == 24

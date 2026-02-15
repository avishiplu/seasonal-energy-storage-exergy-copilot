from datetime import datetime
from typing import List, Dict
import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_hourly_temperature(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> List[Dict[str, float]]:
    """
    Fetch hourly ambient temperature (°C) from Open-Meteo.

    Returns:
    [
        {"time": "2022-01-01T00:00", "temperature_C": 3.4},
        ...
    ]
    """

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m",
        "start_date": start_date,
        "end_date": end_date,
        "timezone": "UTC",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()

    if "hourly" not in data:
        raise RuntimeError("Open-Meteo response missing 'hourly'")

    hourly = data["hourly"]

    if "time" not in hourly or "temperature_2m" not in hourly:
        raise RuntimeError("Open-Meteo response missing required fields")

    times = hourly["time"]
    temps = hourly["temperature_2m"]

    if len(times) != len(temps):
        raise RuntimeError("Time and temperature length mismatch")

    out: List[Dict[str, float]] = []
    for t, temp in zip(times, temps):
        out.append(
            {
                "time": t,
                "temperature_C": float(temp),
            }
        )

    return out

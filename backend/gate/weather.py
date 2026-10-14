"""
Weather severity for an arrival day, from the Open-Meteo forecast (free, no API key).

The no-show model uses a 0-3 weather severity (0 clear, 1 light rain, 2 heavy rain, 3 storm). This module
turns the forecast for the port (Colombo) into that scale instead of asking the user to type it.

When the forecast cannot be had - offline, beyond the 16-day forecast range, or an API error - the result is
`severity: None`, and the risk model falls back to the seasonal typical weather rather than guessing.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from typing import Callable

PORT_LATITUDE, PORT_LONGITUDE = 6.94, 79.84  # Colombo
FORECAST_DAYS = 16  # Open-Meteo's forecast horizon
TIMEOUT_S = 5
CACHE_OK_S = 3 * 3600
CACHE_FAIL_S = 120  # remember a failure briefly so an offline machine does not wait on every request
LABELS = ["Clear", "Light rain", "Heavy rain", "Storm"]

_cache: dict[str, tuple[float, dict]] = {}


def severity_from_forecast(weather_code: int | None, precipitation_mm: float | None, wind_kmh: float | None) -> int:
    """0 clear, 1 light rain, 2 heavy rain, 3 storm, from the day's WMO weather code, rain total and peak wind."""
    code = weather_code or 0
    rain = precipitation_mm or 0.0
    wind = wind_kmh or 0.0
    if code >= 95 or rain >= 30 or wind >= 60:
        return 3
    if rain >= 10 or code in (65, 67, 82):
        return 2
    if rain >= 1 or code >= 51:
        return 1
    return 0


def _fetch_open_meteo(day: str) -> dict | None:
    query = urllib.parse.urlencode(
        {
            "latitude": PORT_LATITUDE,
            "longitude": PORT_LONGITUDE,
            "daily": "weather_code,precipitation_sum,wind_speed_10m_max",
            "timezone": "Asia/Colombo",
            "start_date": day,
            "end_date": day,
        }
    )
    try:
        with urllib.request.urlopen(f"https://api.open-meteo.com/v1/forecast?{query}", timeout=TIMEOUT_S) as resp:
            daily = json.load(resp)["daily"]
        return {
            "weather_code": daily["weather_code"][0],
            "precipitation_mm": daily["precipitation_sum"][0],
            "wind_kmh": daily["wind_speed_10m_max"][0],
        }
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError, OSError):
        return None


def _result(day: str, severity: int | None, source: str, **extra) -> dict:
    return {
        "date": day,
        "severity": severity,
        "label": LABELS[severity] if severity is not None else None,
        "source": source,
        **extra,
    }


def get_weather(day: str, fetch: Callable[[str], dict | None] | None = None, today: date | None = None) -> dict:
    """Weather severity for `day` (YYYY-MM-DD). `fetch` is injectable for tests."""
    today = today or date.today()
    try:
        target = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return _result(day, None, "invalid-date")
    if target < today:
        return _result(day, None, "past-date")
    if target > today + timedelta(days=FORECAST_DAYS - 1):
        return _result(day, None, "beyond-forecast-range")

    cached = _cache.get(day)
    if cached and time.time() < cached[0]:
        return cached[1]

    raw = (fetch or _fetch_open_meteo)(day)
    if raw is None:
        result = _result(day, None, "unavailable")
        _cache[day] = (time.time() + CACHE_FAIL_S, result)
        return result
    severity = severity_from_forecast(raw.get("weather_code"), raw.get("precipitation_mm"), raw.get("wind_kmh"))
    result = _result(
        day,
        severity,
        "open-meteo",
        precipitation_mm=raw.get("precipitation_mm"),
        wind_kmh=raw.get("wind_kmh"),
        weather_code=raw.get("weather_code"),
    )
    _cache[day] = (time.time() + CACHE_OK_S, result)
    return result


def clear_cache() -> None:
    _cache.clear()

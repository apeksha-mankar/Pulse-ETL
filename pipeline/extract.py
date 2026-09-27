# pipeline/extract.py — calls Open-Meteo API per city

import requests
import datetime
from typing import Any

from config import (
    FORECAST_URL, ARCHIVE_URL, HOURLY_VARS,
    CITIES,
)

TIMEOUT = 30  # seconds


def _build_forecast_params(city: dict) -> dict:
    return {
        "latitude":  city["latitude"],
        "longitude": city["longitude"],
        "hourly":    HOURLY_VARS,
        "timezone":  city["timezone"],
        "forecast_days": 1,
    }


def _build_archive_params(city: dict, start: str, end: str) -> dict:
    return {
        "latitude":   city["latitude"],
        "longitude":  city["longitude"],
        "hourly":     HOURLY_VARS,
        "timezone":   city["timezone"],
        "start_date": start,
        "end_date":   end,
    }


def _parse_response(city: dict, data: dict) -> list[dict[str, Any]]:
    """
    Convert Open-Meteo's columnar hourly response into a list of row dicts.
    Each row maps a single timestamp to its weather values.
    """
    hourly = data.get("hourly", {})
    times  = hourly.get("time", [])
    temps  = hourly.get("temperature_2m", [])
    humids = hourly.get("relative_humidity_2m", [])
    precip = hourly.get("precipitation", [])
    winds  = hourly.get("wind_speed_10m", [])

    rows = []
    for i, ts in enumerate(times):
        rows.append({
            "city_name":      city["name"],
            "city_country":   city["country"],
            "observed_at":    ts,               # local time string from API
            "temperature_c":  temps[i]  if i < len(temps)  else None,
            "humidity_pct":   humids[i] if i < len(humids) else None,
            "precipitation_mm": precip[i] if i < len(precip) else None,
            "wind_speed_kmh": winds[i]  if i < len(winds)  else None,
        })
    return rows


def fetch_forecast(city: dict) -> list[dict[str, Any]]:
    """Pull current + next-24h forecast for one city."""
    resp = requests.get(
        FORECAST_URL,
        params=_build_forecast_params(city),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_response(city, resp.json())


def fetch_archive(city: dict, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Pull historical data for one city between start_date and end_date (YYYY-MM-DD)."""
    resp = requests.get(
        ARCHIVE_URL,
        params=_build_archive_params(city, start_date, end_date),
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return _parse_response(city, resp.json())


def extract_all_cities() -> list[dict[str, Any]]:
    """
    Fetch forecast data for every configured city.
    Returns a flat list of raw row dicts, tagged with city info.
    Logs per-city success/failure but does not raise — a single city
    failure should not abort the whole run.
    """
    all_rows: list[dict[str, Any]] = []
    total_extracted = 0

    for city in CITIES:
        try:
            rows = fetch_forecast(city)
            all_rows.extend(rows)
            total_extracted += len(rows)
            print(f"  extract: {city['name']} — {len(rows)} rows")
        except Exception as exc:
            print(f"  extract ERROR {city['name']}: {exc}")

    print(f"extract complete — {total_extracted} rows from {len(CITIES)} cities")
    return all_rows


def extract_backfill(days: int) -> list[dict[str, Any]]:
    """
    Pull `days` days of historical data for all configured cities.
    Uses the Open-Meteo archive endpoint.
    """
    end   = datetime.date.today() - datetime.timedelta(days=1)  # archive lags 1 day
    start = end - datetime.timedelta(days=days - 1)
    start_str = start.isoformat()
    end_str   = end.isoformat()

    all_rows: list[dict[str, Any]] = []
    for city in CITIES:
        try:
            rows = fetch_archive(city, start_str, end_str)
            all_rows.extend(rows)
            print(f"  backfill: {city['name']} — {len(rows)} rows ({start_str} → {end_str})")
        except Exception as exc:
            print(f"  backfill ERROR {city['name']}: {exc}")

    print(f"backfill complete — {len(all_rows)} total rows")
    return all_rows

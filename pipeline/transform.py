# pipeline/transform.py — validation, cleaning, normalization

import json
import datetime
from typing import Any

from config import (
    TEMP_MIN_C, TEMP_MAX_C,
    HUMIDITY_MIN_PCT, HUMIDITY_MAX_PCT,
    FUTURE_SKEW_HOURS,
)

# ─── Result containers ────────────────────────────────────────────────────────

class ValidRow:
    __slots__ = (
        "city_name", "city_country", "observed_at",
        "temperature_c", "humidity_pct", "precipitation_mm", "wind_speed_kmh",
    )
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

class RejectedRow:
    __slots__ = ("raw_payload", "reason", "city_name", "city_country")
    def __init__(self, raw: dict, reason: str):
        self.raw_payload  = json.dumps(raw)
        self.reason       = reason
        self.city_name    = raw.get("city_name")
        self.city_country = raw.get("city_country")


# ─── Individual validation rules ─────────────────────────────────────────────

def _parse_timestamp(ts_str: Any) -> datetime.datetime | None:
    """
    Parse an ISO 8601 timestamp string.
    Open-Meteo returns 'YYYY-MM-DDTHH:MM' (no seconds, no Z).
    We normalise to UTC-aware datetime.
    """
    if not isinstance(ts_str, str) or not ts_str.strip():
        return None
    try:
        # Handle both 'YYYY-MM-DDTHH:MM' and 'YYYY-MM-DDTHH:MM:SS'
        ts_str = ts_str.strip()
        if len(ts_str) == 16:          # no seconds
            ts_str += ":00"
        dt = datetime.datetime.fromisoformat(ts_str)
        # Treat as UTC if naive (Open-Meteo returns local; we store UTC offset as-is
        # but compare against UTC now for the future-skew check)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except ValueError:
        return None


def _validate(row: dict) -> tuple[bool, str]:
    """
    Run all validation rules. Returns (is_valid, rejection_reason).
    Checks are ordered cheapest-first.
    """
    # 1. Required fields present
    if not row.get("city_name") or not row.get("city_country"):
        return False, "missing city identifier"

    # 2. Timestamp present and parseable
    dt = _parse_timestamp(row.get("observed_at"))
    if dt is None:
        return False, f"missing or malformed observed_at: {row.get('observed_at')!r}"

    # 3. Future-skew guard
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    if dt > now_utc + datetime.timedelta(hours=FUTURE_SKEW_HOURS):
        return False, f"timestamp too far in the future: {row['observed_at']}"

    # 4. Temperature must be present (it's the primary metric)
    temp = row.get("temperature_c")
    if temp is None:
        return False, "null temperature_c"

    # 5. Temperature physically plausible
    if not isinstance(temp, (int, float)):
        return False, f"non-numeric temperature_c: {temp!r}"
    if temp < TEMP_MIN_C or temp > TEMP_MAX_C:
        return False, f"temperature_c out of range: {temp}"

    # 6. Humidity plausible (allow null — not all endpoints return it)
    hum = row.get("humidity_pct")
    if hum is not None:
        if not isinstance(hum, (int, float)):
            return False, f"non-numeric humidity_pct: {hum!r}"
        if hum < HUMIDITY_MIN_PCT or hum > HUMIDITY_MAX_PCT:
            return False, f"humidity_pct out of range: {hum}"

    return True, ""


# ─── Public interface ─────────────────────────────────────────────────────────

def transform(raw_rows: list[dict]) -> tuple[list[ValidRow], list[RejectedRow]]:
    """
    Validate and clean a list of raw row dicts.

    Returns:
        valid    — list of ValidRow (ready for load)
        rejected — list of RejectedRow (to be written to rejected_records)

    Deduplication within the batch is applied after validation: if the same
    (city, observed_at) appears more than once (e.g. from overlapping API
    windows), only the last occurrence is kept.
    """
    valid: list[ValidRow] = []
    rejected: list[RejectedRow] = []

    # Dedup key → last-seen valid row (preserves ordering within batch)
    seen: dict[tuple, ValidRow] = {}

    for row in raw_rows:
        ok, reason = _validate(row)
        if not ok:
            rejected.append(RejectedRow(row, reason))
            continue

        # Normalise the timestamp to a consistent string format for storage
        dt = _parse_timestamp(row["observed_at"])
        observed_iso = dt.strftime("%Y-%m-%dT%H:%M:%S")

        v = ValidRow(
            city_name       = row["city_name"],
            city_country    = row["city_country"],
            observed_at     = observed_iso,
            temperature_c   = float(row["temperature_c"]),
            humidity_pct    = float(row["humidity_pct"])    if row.get("humidity_pct")    is not None else None,
            precipitation_mm= float(row["precipitation_mm"]) if row.get("precipitation_mm") is not None else None,
            wind_speed_kmh  = float(row["wind_speed_kmh"]) if row.get("wind_speed_kmh")  is not None else None,
        )

        dedup_key = (v.city_name, v.city_country, v.observed_at)
        seen[dedup_key] = v

    valid = list(seen.values())

    print(
        f"transform complete — {len(valid)} valid, "
        f"{len(rejected)} rejected, "
        f"{len(raw_rows) - len(valid) - len(rejected)} deduped within batch"
    )
    return valid, rejected

# tests/test_transform.py — validates all rejection rules

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import datetime
import pytest
from pipeline.transform import transform, ValidRow, RejectedRow


def _base_row(**overrides):
    """Return a minimal valid raw row, with optional field overrides."""
    row = {
        "city_name":       "Test City",
        "city_country":    "TC",
        "observed_at":     "2024-06-01T12:00",
        "temperature_c":   20.0,
        "humidity_pct":    60.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh":  10.0,
    }
    row.update(overrides)
    return row


# ── Valid row passes through ───────────────────────────────────────────────────

def test_valid_row_passes():
    valid, rejected = transform([_base_row()])
    assert len(valid) == 1
    assert len(rejected) == 0
    assert isinstance(valid[0], ValidRow)
    assert valid[0].temperature_c == 20.0


# ── Null temperature → rejected ───────────────────────────────────────────────

def test_null_temperature_rejected():
    valid, rejected = transform([_base_row(temperature_c=None)])
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "null temperature" in rejected[0].reason


# ── Missing observed_at → rejected ────────────────────────────────────────────

def test_missing_timestamp_rejected():
    valid, rejected = transform([_base_row(observed_at=None)])
    assert len(valid) == 0
    assert "observed_at" in rejected[0].reason


def test_malformed_timestamp_rejected():
    valid, rejected = transform([_base_row(observed_at="not-a-date")])
    assert len(valid) == 0
    assert "observed_at" in rejected[0].reason


# ── Future timestamp → rejected ───────────────────────────────────────────────

def test_future_timestamp_rejected():
    far_future = (datetime.datetime.utcnow() + datetime.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M")
    valid, rejected = transform([_base_row(observed_at=far_future)])
    assert len(valid) == 0
    assert "future" in rejected[0].reason


def test_near_future_within_skew_passes():
    """Timestamps up to 1h in the future are allowed (clock-skew guard)."""
    near_future = (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M")
    valid, rejected = transform([_base_row(observed_at=near_future)])
    assert len(valid) == 1
    assert len(rejected) == 0


# ── Temperature out of physical range → rejected ──────────────────────────────

def test_temperature_too_cold_rejected():
    valid, rejected = transform([_base_row(temperature_c=-100.0)])
    assert len(valid) == 0
    assert "out of range" in rejected[0].reason

def test_temperature_too_hot_rejected():
    valid, rejected = transform([_base_row(temperature_c=65.0)])
    assert len(valid) == 0
    assert "out of range" in rejected[0].reason

def test_temperature_at_boundary_passes():
    valid, rejected = transform([_base_row(temperature_c=-89.0)])
    assert len(valid) == 1

def test_temperature_non_numeric_rejected():
    valid, rejected = transform([_base_row(temperature_c="warm")])
    assert len(valid) == 0
    assert "non-numeric" in rejected[0].reason


# ── Humidity out of range → rejected ─────────────────────────────────────────

def test_humidity_over_100_rejected():
    valid, rejected = transform([_base_row(humidity_pct=110.0)])
    assert len(valid) == 0
    assert "humidity_pct out of range" in rejected[0].reason

def test_humidity_negative_rejected():
    valid, rejected = transform([_base_row(humidity_pct=-5.0)])
    assert len(valid) == 0

def test_null_humidity_passes():
    """Humidity is optional — null is fine."""
    valid, rejected = transform([_base_row(humidity_pct=None)])
    assert len(valid) == 1
    assert valid[0].humidity_pct is None


# ── Missing city identifier → rejected ───────────────────────────────────────

def test_missing_city_name_rejected():
    valid, rejected = transform([_base_row(city_name=None)])
    assert len(valid) == 0
    assert "city" in rejected[0].reason


# ── Intra-batch deduplication ─────────────────────────────────────────────────

def test_deduplication_within_batch():
    """Same city + timestamp appearing twice: last one wins, count stays 1."""
    row1 = _base_row(temperature_c=20.0)
    row2 = _base_row(temperature_c=21.0)   # same city+ts, different temp
    valid, rejected = transform([row1, row2])
    assert len(valid) == 1
    # Last occurrence wins
    assert valid[0].temperature_c == 21.0

def test_different_timestamps_not_deduped():
    row1 = _base_row(observed_at="2024-06-01T12:00", temperature_c=20.0)
    row2 = _base_row(observed_at="2024-06-01T13:00", temperature_c=22.0)
    valid, rejected = transform([row1, row2])
    assert len(valid) == 2


# ── Mixed batch ───────────────────────────────────────────────────────────────

def test_mixed_batch():
    rows = [
        _base_row(temperature_c=15.0),          # valid
        _base_row(temperature_c=None),           # rejected: null temp
        _base_row(observed_at="bad-date"),       # rejected: bad ts
        _base_row(temperature_c=18.0, observed_at="2024-06-02T10:00"),  # valid, different ts
    ]
    valid, rejected = transform(rows)
    assert len(valid) == 2
    assert len(rejected) == 2

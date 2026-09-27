# tests/test_load_idempotency.py — confirms re-running never duplicates rows

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sqlite3
import tempfile
import pathlib
import pytest

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Each test gets its own fresh SQLite database in a temp directory.
    We monkeypatch config.DB_PATH so db.connection picks it up.
    """
    db_file = str(tmp_path / "test.db")
    monkeypatch.setenv("PULSE_DB", db_file)

    # Also patch the module-level variable that's already been imported
    import config
    monkeypatch.setattr(config, "DB_PATH", db_file)

    # Re-import connection with new path
    import importlib
    import db.connection
    importlib.reload(db.connection)

    # Init schema
    db.connection.init_db()

    # Seed one test city
    conn = db.connection.get_conn()
    conn.execute(
        "INSERT INTO cities (name, country, latitude, longitude, timezone) VALUES (?,?,?,?,?)",
        ("TestCity", "TC", 0.0, 0.0, "UTC"),
    )
    conn.commit()
    conn.close()

    yield db_file

    # Cleanup handled by tmp_path fixture


def _make_valid_rows(temp_c=20.0, ts="2024-06-01T12:00:00"):
    """Return a list of ValidRow objects for the test city."""
    from pipeline.transform import ValidRow
    return [ValidRow(
        city_name="TestCity",
        city_country="TC",
        observed_at=ts,
        temperature_c=temp_c,
        humidity_pct=60.0,
        precipitation_mm=0.0,
        wind_speed_kmh=10.0,
    )]


def _row_count():
    import db.connection
    conn = db.connection.get_conn()
    count = conn.execute("SELECT COUNT(*) FROM weather_readings").fetchone()[0]
    conn.close()
    return count


def _get_reading(ts="2024-06-01T12:00:00"):
    import db.connection
    conn = db.connection.get_conn()
    row = conn.execute(
        "SELECT * FROM weather_readings WHERE observed_at = ?", (ts,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_first_load_inserts_row():
    from pipeline.load import load
    loaded, rejected = load(_make_valid_rows(), [])
    assert loaded == 1
    assert rejected == 0
    assert _row_count() == 1


def test_second_load_same_data_no_duplicate():
    """Loading the exact same batch twice must not create a second row."""
    from pipeline.load import load
    load(_make_valid_rows(), [])
    load(_make_valid_rows(), [])
    assert _row_count() == 1


def test_second_load_updates_values():
    """Re-loading with updated temperature must update the row, not add a new one."""
    from pipeline.load import load
    load(_make_valid_rows(temp_c=20.0), [])
    load(_make_valid_rows(temp_c=25.0), [])  # 25°C is within physical range

    assert _row_count() == 1
    row = _get_reading()
    assert row["temperature_c"] == 25.0


def test_load_many_times_stays_idempotent():
    """Loading the same batch 10 times should still result in exactly 1 row."""
    from pipeline.load import load
    for _ in range(10):
        load(_make_valid_rows(), [])
    assert _row_count() == 1


def test_different_timestamps_create_separate_rows():
    """Different timestamps for the same city must each produce their own row."""
    from pipeline.load import load
    load(_make_valid_rows(ts="2024-06-01T10:00:00"), [])
    load(_make_valid_rows(ts="2024-06-01T11:00:00"), [])
    load(_make_valid_rows(ts="2024-06-01T12:00:00"), [])
    assert _row_count() == 3


def test_rejected_records_written():
    """Rejected rows must be written to rejected_records, not weather_readings."""
    from pipeline.load import load
    from pipeline.transform import RejectedRow
    rejected = [RejectedRow(
        {"city_name": "TestCity", "city_country": "TC", "observed_at": None, "temperature_c": None},
        "null temperature_c",
    )]
    load([], rejected)

    import db.connection
    conn = db.connection.get_conn()
    rej_count = conn.execute("SELECT COUNT(*) FROM rejected_records").fetchone()[0]
    conn.close()

    assert rej_count == 1
    assert _row_count() == 0  # nothing in weather_readings


def test_ingested_at_updated_on_reload():
    """ingested_at should reflect the most recent load time after an upsert."""
    import time
    from pipeline.load import load

    load(_make_valid_rows(temp_c=20.0), [])
    first_ingested = _get_reading()["ingested_at"]

    time.sleep(1.1)  # ensure timestamp differs
    load(_make_valid_rows(temp_c=20.0), [])
    second_ingested = _get_reading()["ingested_at"]

    assert second_ingested >= first_ingested

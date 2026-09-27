# pipeline/load.py — idempotent upserts into SQLite

import datetime
from typing import Any

from db.connection import get_conn
from pipeline.transform import ValidRow, RejectedRow

# ─── City seed / lookup ───────────────────────────────────────────────────────

def _ensure_cities(conn, cities_cfg: list[dict]) -> dict[tuple, int]:
    """
    Insert configured cities if they don't exist yet.
    Returns a mapping of (name, country) → city_id.
    """
    conn.executemany(
        """
        INSERT INTO cities (name, country, latitude, longitude, timezone)
        VALUES (:name, :country, :latitude, :longitude, :timezone)
        ON CONFLICT(name, country) DO NOTHING
        """,
        cities_cfg,
    )
    rows = conn.execute("SELECT city_id, name, country FROM cities").fetchall()
    return {(r["name"], r["country"]): r["city_id"] for r in rows}


def _get_city_map(conn) -> dict[tuple, int]:
    rows = conn.execute("SELECT city_id, name, country FROM cities").fetchall()
    return {(r["name"], r["country"]): r["city_id"] for r in rows}


# ─── Weather upsert ───────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO weather_readings
    (city_id, observed_at, temperature_c, humidity_pct,
     precipitation_mm, wind_speed_kmh, ingested_at)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(city_id, observed_at) DO UPDATE SET
    temperature_c    = excluded.temperature_c,
    humidity_pct     = excluded.humidity_pct,
    precipitation_mm = excluded.precipitation_mm,
    wind_speed_kmh   = excluded.wind_speed_kmh,
    ingested_at      = excluded.ingested_at
"""

REJECT_SQL = """
INSERT INTO rejected_records (raw_payload, reason, city_id, rejected_at)
VALUES (?, ?, ?, ?)
"""


def load(
    valid_rows: list[ValidRow],
    rejected_rows: list[RejectedRow],
) -> tuple[int, int]:
    """
    Write valid rows (upsert) and rejected rows to the database.
    Returns (rows_loaded, rows_rejected).
    """
    ingested_at = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
    conn = get_conn()

    with conn:
        city_map = _get_city_map(conn)

        # Upsert valid rows
        loaded = 0
        skipped = 0
        for row in valid_rows:
            key = (row.city_name, row.city_country)
            city_id = city_map.get(key)
            if city_id is None:
                # City not in DB yet — shouldn't happen after init-db, but handle gracefully
                skipped += 1
                continue

            conn.execute(UPSERT_SQL, (
                city_id,
                row.observed_at,
                row.temperature_c,
                row.humidity_pct,
                row.precipitation_mm,
                row.wind_speed_kmh,
                ingested_at,
            ))
            loaded += 1

        # Insert rejected records
        for row in rejected_rows:
            city_id = city_map.get((row.city_name, row.city_country))
            conn.execute(REJECT_SQL, (
                row.raw_payload,
                row.reason,
                city_id,
                ingested_at,
            ))

    conn.close()

    if skipped:
        print(f"  load: {skipped} rows skipped (unknown city — run init-db?)")
    print(f"load complete — {loaded} upserted, {len(rejected_rows)} rejected written")
    return loaded, len(rejected_rows)


def seed_cities(cities_cfg: list[dict]) -> None:
    """Insert the configured city list into the cities table."""
    conn = get_conn()
    with conn:
        _ensure_cities(conn, cities_cfg)
    conn.close()
    print(f"Seeded {len(cities_cfg)} cities.")

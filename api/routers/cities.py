# api/routers/cities.py

from fastapi import APIRouter, HTTPException, Query
from db.connection import get_conn

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("")
def list_cities():
    """List all configured cities."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT city_id, name, country, latitude, longitude, timezone FROM cities ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{city_id}")
def get_city(city_id: int):
    """Get a single city by ID."""
    conn = get_conn()
    row = conn.execute(
        "SELECT city_id, name, country, latitude, longitude, timezone FROM cities WHERE city_id = ?",
        (city_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="City not found")
    return dict(row)


@router.get("/{city_id}/readings")
def get_readings(city_id: int, limit: int = Query(default=100, le=1000)):
    """Latest weather readings for a city, newest first."""
    conn = get_conn()

    # Confirm city exists
    city = conn.execute("SELECT name FROM cities WHERE city_id = ?", (city_id,)).fetchone()
    if not city:
        conn.close()
        raise HTTPException(status_code=404, detail="City not found")

    rows = conn.execute(
        """
        SELECT reading_id, city_id, observed_at, temperature_c,
               humidity_pct, precipitation_mm, wind_speed_kmh, ingested_at
        FROM weather_readings
        WHERE city_id = ?
        ORDER BY observed_at DESC
        LIMIT ?
        """,
        (city_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

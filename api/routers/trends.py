# api/routers/trends.py

from fastapi import APIRouter, HTTPException, Query
from db.connection import get_conn

router = APIRouter(prefix="/cities", tags=["trends"])


@router.get("/{city_id}/trends")
def get_trends(city_id: int, limit: int = Query(default=168, le=720)):
    """
    7-day rolling average temperature and 24h delta for a city.
    Returns the two view results side by side, newest first.
    """
    conn = get_conn()

    city = conn.execute("SELECT name FROM cities WHERE city_id = ?", (city_id,)).fetchone()
    if not city:
        conn.close()
        raise HTTPException(status_code=404, detail="City not found")

    rolling = conn.execute(
        """
        SELECT observed_at, temperature_c, rolling_7d_avg
        FROM rolling_avg_temp
        WHERE city_id = ?
        ORDER BY observed_at DESC
        LIMIT ?
        """,
        (city_id, limit),
    ).fetchall()

    delta = conn.execute(
        """
        SELECT observed_at, temperature_c, delta_24h
        FROM daily_delta
        WHERE city_id = ?
        ORDER BY observed_at DESC
        LIMIT ?
        """,
        (city_id, limit),
    ).fetchall()

    conn.close()
    return {
        "city_id": city_id,
        "rolling_7d_avg": [dict(r) for r in rolling],
        "daily_delta":    [dict(r) for r in delta],
    }

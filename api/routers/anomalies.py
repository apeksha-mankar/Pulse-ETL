# api/routers/anomalies.py

from fastapi import APIRouter, Query
from db.connection import get_conn

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def get_anomalies(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=100, le=500),
):
    """
    Temperature anomalies across all cities (z-score > 2.5 from city's 30-day mean).
    Sorted by absolute z-score descending — biggest outliers first.
    """
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT a.city_id, c.name AS city_name, c.country,
               a.observed_at, a.temperature_c, a.mean_temp,
               a.std_dev, a.z_score
        FROM anomalies a
        JOIN cities c ON c.city_id = a.city_id
        WHERE a.observed_at >= datetime('now', ? || ' days')
        ORDER BY ABS(a.z_score) DESC
        LIMIT ?
        """,
        (f"-{days}", limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

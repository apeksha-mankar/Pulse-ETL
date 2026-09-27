# api/routers/runs.py

from fastapi import APIRouter, Query
from db.connection import get_conn

router = APIRouter(prefix="/runs", tags=["observability"])


@router.get("")
def get_runs(limit: int = Query(default=20, le=100)):
    """Recent pipeline runs — status, row counts, duration, errors."""
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT run_id, started_at, finished_at, status,
               rows_extracted, rows_loaded, rows_rejected, error_message,
               ROUND(
                 (julianday(COALESCE(finished_at, datetime('now'))) - julianday(started_at)) * 86400,
                 1
               ) AS duration_seconds
        FROM pipeline_runs
        ORDER BY run_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

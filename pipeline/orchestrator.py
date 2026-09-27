# pipeline/orchestrator.py — runs E→T→L, writes to pipeline_runs audit table

import datetime
import traceback

from db.connection import get_conn
from pipeline.extract import extract_all_cities, extract_backfill
from pipeline.transform import transform
from pipeline.load import load

# ─── Audit helpers ────────────────────────────────────────────────────────────

def _start_run(conn) -> int:
    cur = conn.execute(
        "INSERT INTO pipeline_runs (started_at, status) VALUES (?, 'running')",
        (datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),),
    )
    return cur.lastrowid


def _finish_run(conn, run_id: int, rows_extracted: int,
                rows_loaded: int, rows_rejected: int) -> None:
    conn.execute(
        """
        UPDATE pipeline_runs
        SET finished_at = ?, status = 'success',
            rows_extracted = ?, rows_loaded = ?, rows_rejected = ?
        WHERE run_id = ?
        """,
        (
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            rows_extracted, rows_loaded, rows_rejected,
            run_id,
        ),
    )


def _fail_run(conn, run_id: int, error: str) -> None:
    conn.execute(
        """
        UPDATE pipeline_runs
        SET finished_at = ?, status = 'failed', error_message = ?
        WHERE run_id = ?
        """,
        (
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            error[:2000],   # cap to avoid huge blobs
            run_id,
        ),
    )


# ─── Public pipeline entry points ────────────────────────────────────────────

def run_pipeline() -> dict:
    """
    Full extract → transform → load cycle for the current forecast data.
    Every invocation writes a row to pipeline_runs.
    Returns a summary dict.
    """
    conn = get_conn()
    run_id = None
    try:
        with conn:
            run_id = _start_run(conn)

        print(f"\n── PulseETL run #{run_id} ─────────────────────────────")

        # Extract
        raw_rows = extract_all_cities()

        # Transform
        valid_rows, rejected_rows = transform(raw_rows)

        # Load
        rows_loaded, rows_rejected = load(valid_rows, rejected_rows)

        with conn:
            _finish_run(conn, run_id, len(raw_rows), rows_loaded, rows_rejected)

        summary = {
            "run_id":        run_id,
            "status":        "success",
            "rows_extracted": len(raw_rows),
            "rows_loaded":   rows_loaded,
            "rows_rejected": rows_rejected,
        }
        print(f"── run #{run_id} complete: {summary}\n")
        return summary

    except Exception as exc:
        err = traceback.format_exc()
        print(f"── run #{run_id} FAILED:\n{err}")
        if run_id:
            with conn:
                _fail_run(conn, run_id, str(exc))
        return {"run_id": run_id, "status": "failed", "error": str(exc)}
    finally:
        conn.close()


def run_backfill(days: int) -> dict:
    """
    Historical backfill for `days` days via the Open-Meteo archive API.
    Also logged to pipeline_runs.
    """
    conn = get_conn()
    run_id = None
    try:
        with conn:
            run_id = _start_run(conn)

        print(f"\n── PulseETL backfill #{run_id} ({days} days) ──────────")

        raw_rows = extract_backfill(days)
        valid_rows, rejected_rows = transform(raw_rows)
        rows_loaded, rows_rejected = load(valid_rows, rejected_rows)

        with conn:
            _finish_run(conn, run_id, len(raw_rows), rows_loaded, rows_rejected)

        summary = {
            "run_id":        run_id,
            "status":        "success",
            "rows_extracted": len(raw_rows),
            "rows_loaded":   rows_loaded,
            "rows_rejected": rows_rejected,
        }
        print(f"── backfill #{run_id} complete: {summary}\n")
        return summary

    except Exception as exc:
        err = traceback.format_exc()
        print(f"── backfill #{run_id} FAILED:\n{err}")
        if run_id:
            with conn:
                _fail_run(conn, run_id, str(exc))
        return {"run_id": run_id, "status": "failed", "error": str(exc)}
    finally:
        conn.close()

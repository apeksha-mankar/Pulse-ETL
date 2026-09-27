# pipeline/scheduler.py — APScheduler job definitions

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import SCHEDULE_INTERVAL_HOURS
from pipeline.orchestrator import run_pipeline


def build_scheduler() -> BackgroundScheduler:
    """
    Create and return a configured (but not yet started) BackgroundScheduler.
    The pipeline runs every SCHEDULE_INTERVAL_HOURS hours.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=run_pipeline,
        trigger=IntervalTrigger(hours=SCHEDULE_INTERVAL_HOURS),
        id="pulse_etl",
        name="PulseETL hourly extract→transform→load",
        replace_existing=True,
        max_instances=1,        # never run two pipeline cycles concurrently
    )
    return scheduler

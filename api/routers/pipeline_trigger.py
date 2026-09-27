# api/routers/pipeline_trigger.py

from fastapi import APIRouter, BackgroundTasks
from pipeline.orchestrator import run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
def trigger_run(background_tasks: BackgroundTasks):
    """
    Trigger an on-demand extract → transform → load cycle.
    Runs asynchronously in the background; returns immediately with the
    scheduled status. Query GET /runs to see results.
    """
    background_tasks.add_task(run_pipeline)
    return {
        "status": "queued",
        "message": "Pipeline run started in background. Poll GET /runs for results.",
    }

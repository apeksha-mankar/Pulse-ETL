# api/main.py — FastAPI application

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

from api.routers import cities, trends, anomalies, runs, pipeline_trigger

app = FastAPI(
    title="PulseETL",
    description="Weather intelligence pipeline — REST API",
    version="1.0.0",
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(cities.router)
app.include_router(trends.router)
app.include_router(anomalies.router)
app.include_router(runs.router)
app.include_router(pipeline_trigger.router)

# ─── Dashboard static files ───────────────────────────────────────────────────
_dashboard = pathlib.Path(__file__).parent.parent / "dashboard"
app.mount("/static", StaticFiles(directory=str(_dashboard)), name="static")

@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(str(_dashboard / "index.html"))

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(str(_dashboard / "index.html"))

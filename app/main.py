"""FastAPI application entry point with lifespan, health endpoint, and v1 router."""

from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.v1 import router as v1_router
from app.services.job_queue import job_queue


@asynccontextmanager
async def lifespan(application: FastAPI):  # noqa: ARG001
    """Manage application startup and shutdown lifecycle."""
    # Startup: nothing to initialise in Wave 0 (DB engine is lazy)
    yield
    # Shutdown: dispose async engine to close connection pool
    from app.db import engine

    await engine.dispose()


app = FastAPI(
    title="Invasive Trace",
    description="Invasive plant species detection — Southern Grassland Institute.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1")

# Mount static files directory for dashboard assets (if any)
with suppress(RuntimeError):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Dashboard templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse, tags=["dashboard"])
async def root_dashboard() -> HTMLResponse:
    """Render the HITL dashboard at the root path."""
    return templates.TemplateResponse("dashboard.html", {"request": {}})


@app.get("/healthz", tags=["ops"])
async def health_check() -> dict[str, Any]:
    """Liveness probe — returns 200 with status ok when the app is running."""
    return {"status": "ok"}


@app.get("/api/jobs", tags=["jobs"])
async def list_jobs() -> dict[str, Any]:
    """List all background jobs and their statuses."""
    return job_queue.list_jobs()


@app.get("/api/jobs/{job_id}", tags=["jobs"])
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Get the status of a specific background job."""
    job = job_queue.get_status(job_id)
    if job is None:
        return {"error": "Job not found"}
    return job

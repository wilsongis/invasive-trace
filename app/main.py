"""FastAPI application entry point with lifespan, health endpoint, and v1 router."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.api.v1 import router as v1_router


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


@app.get("/healthz", tags=["ops"])
async def health_check() -> dict[str, Any]:
    """Liveness probe — returns 200 with status ok when the app is running."""
    return {"status": "ok"}

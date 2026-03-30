"""Scene ingestion and retrieval endpoints for spectral time series."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.spectral import SpectralTimeSeries
from app.schemas.spectral import SceneIngestRequest, SceneIngestResponse, SpectralRecord
from app.services.scene_ingestion import run_ingestion
from app.services.stac_client import StacQueryUnavailableError

router = APIRouter(prefix="/scenes", tags=["scenes"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/ingest", response_model=SceneIngestResponse)
async def ingest_scenes(payload: SceneIngestRequest, db: DbSession) -> SceneIngestResponse:
    """Run ROI-scoped Sentinel-2 ingestion and return summary counts."""
    try:
        return await run_ingestion(
            roi_id=payload.roi_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            platform=payload.platform,
            session=db,
        )
    except StacQueryUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Planetary Computer STAC query unavailable",
        ) from exc


@router.get("", response_model=list[SpectralRecord])
async def list_scenes(
    db: DbSession,
    roi_id: UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_masked: bool = Query(default=False),
) -> list[SpectralRecord]:
    """List persisted spectral records with optional filters."""
    stmt = select(SpectralTimeSeries)

    if roi_id is not None:
        stmt = stmt.where(SpectralTimeSeries.roi_id == roi_id)
    if start_date is not None:
        stmt = stmt.where(SpectralTimeSeries.scene_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(SpectralTimeSeries.scene_date <= end_date)
    if not include_masked:
        stmt = stmt.where(SpectralTimeSeries.is_masked.is_(False))

    stmt = stmt.order_by(SpectralTimeSeries.scene_date.asc())

    rows = (await db.execute(stmt)).scalars().all()
    return [SpectralRecord.model_validate(row) for row in rows]

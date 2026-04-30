"""API routes for managing project KPIs (SGI Standardized pillar)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.metric import Metric, MetricCreate
from app.services import metrics_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.post("/", response_model=Metric)
async def create_metric(metric: MetricCreate, db: AsyncSession = Depends(get_db)):
    """Manually add a metric record (usually these are auto-generated)."""
    return await metrics_service.create_metric(db, metric)


@router.get("/roi/{roi_id}", response_model=list[Metric])
async def get_roi_metrics(roi_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Fetch all metric records for a specific region of interest."""
    return await metrics_service.get_metrics_by_roi(db, roi_id)


@router.post("/roi/{roi_id}/calculate", response_model=Metric)
async def calculate_kpi(
    roi_id: uuid.UUID, pipeline_run_id: str | None = None, db: AsyncSession = Depends(get_db)
):
    """Trigger the KPI calculation service to compute new stats for an ROI."""
    return await metrics_service.calculate_kpi_for_roi(db, roi_id, pipeline_run_id)

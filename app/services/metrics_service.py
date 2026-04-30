"""Service layer for computing and storing project metrics."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metric import ProjectMetric
from app.schemas.metric import MetricCreate


async def create_metric(db: AsyncSession, payload: MetricCreate) -> ProjectMetric:
    """Create a new metric record for a project/ROI."""
    db_metric = ProjectMetric(
        roi_id=payload.roi_id,
        restored_acres=payload.restored_acres,
        ndvi_improvement=payload.ndvi_improvement,
        confidence_mean=payload.confidence_mean,
        pipeline_run_id=payload.pipeline_run_id,
    )
    db.add(db_metric)
    await db.commit()
    await db.refresh(db_metric)
    return db_metric


async def get_metrics_by_roi(db: AsyncSession, roi_id: uuid.UUID) -> list[ProjectMetric]:
    """Retrieve all metrics for a given ROI."""
    result = await db.execute(
        select(ProjectMetric)
        .where(ProjectMetric.roi_id == roi_id)
        .order_by(ProjectMetric.created_at.desc())
    )
    return list(result.scalars().all())


async def calculate_kpi_for_roi(
    db: AsyncSession, roi_id: uuid.UUID, pipeline_run_id: str | None = None
) -> ProjectMetric:
    """Compute KPI values for an ROI and store them in the metrics table.

    This is a stub for the complex metric computation logic that will measure
    restored acres (based on validated predictions) and NDVI improvement
    (based on SpectralTimeSeries). For now it just returns a mock set of metrics.
    """
    # TODO: Implement actual KPI aggregation from regions_of_interest, invasion_predictions, spectral_time_series
    mock_payload = MetricCreate(
        roi_id=roi_id,
        restored_acres=42.5,
        ndvi_improvement=0.15,
        confidence_mean=0.88,
        pipeline_run_id=pipeline_run_id or f"run-{uuid.uuid4().hex[:8]}",
    )
    return await create_metric(db, mock_payload)

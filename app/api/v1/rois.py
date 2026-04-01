"""ROI endpoints for create/list/fetch/pipeline workflows."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.shape import from_shape, to_shape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.roi import RegionOfInterest
from app.schemas.pipeline import PipelineRunResponse
from app.schemas.roi import ROICreate, ROIResponse, parse_wkt_polygon, to_geojson_mapping
from app.services.pipeline import ROINotFoundError, run_pipeline

router = APIRouter(prefix="/rois", tags=["rois"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("", response_model=ROIResponse, status_code=status.HTTP_201_CREATED)
async def create_roi(payload: ROICreate, db: DbSession) -> ROIResponse:
    """Create a new ROI using a validated polygon WKT geometry."""
    try:
        polygon = parse_wkt_polygon(payload.geom_wkt)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    roi = RegionOfInterest(
        name=payload.name,
        description=payload.description,
        geom=from_shape(polygon, srid=4326),
    )
    db.add(roi)
    await db.commit()
    await db.refresh(roi)

    return ROIResponse(
        id=roi.id,
        name=roi.name,
        description=roi.description,
        geometry=to_geojson_mapping(to_shape(roi.geom)),
        created_at=roi.created_at,
        updated_at=roi.updated_at,
    )


@router.get("/{roi_id}", response_model=ROIResponse)
async def get_roi(roi_id: UUID, db: DbSession) -> ROIResponse:
    """Fetch one ROI by ID."""
    roi = await db.get(RegionOfInterest, roi_id)
    if roi is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ROI not found")

    return ROIResponse(
        id=roi.id,
        name=roi.name,
        description=roi.description,
        geometry=to_geojson_mapping(to_shape(roi.geom)),
        created_at=roi.created_at,
        updated_at=roi.updated_at,
    )


@router.get("", response_model=list[ROIResponse])
async def list_rois(db: DbSession) -> list[ROIResponse]:
    """List all ROIs."""
    rows = (
        await db.execute(
            select(RegionOfInterest).order_by(RegionOfInterest.created_at.desc()),
        )
    ).scalars()
    return [
        ROIResponse(
            id=roi.id,
            name=roi.name,
            description=roi.description,
            geometry=to_geojson_mapping(to_shape(roi.geom)),
            created_at=roi.created_at,
            updated_at=roi.updated_at,
        )
        for roi in rows
    ]


@router.post("/{roi_id}/pipeline/run", response_model=PipelineRunResponse)
async def trigger_pipeline(roi_id: UUID, db: DbSession) -> PipelineRunResponse:
    """Trigger the three-stage AI pipeline for a given ROI.

    Returns a 200 with predictions_created=0 when the ROI exists but has
    no usable spectral data or no anomalous scenes are detected.
    Returns 404 when the ROI does not exist (FR-024).
    """
    try:
        return await run_pipeline(roi_id=roi_id, db=db)
    except ROINotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

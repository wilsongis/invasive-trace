"""GET /api/v1/predictions — GeoJSON FeatureCollection of invasion predictions."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas.prediction import PredictionFeatureCollection
from app.services.prediction_query import query_predictions

router = APIRouter(prefix="/predictions", tags=["predictions"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("", response_model=PredictionFeatureCollection)
async def get_predictions(
    db: DbSession,
    roi_id: Annotated[UUID | None, Query(description="Filter by region of interest")] = None,
    species_label: Annotated[str | None, Query(description="Exact species label match")] = None,
    validated: Annotated[
        bool | None,
        Query(
            description=(
                "true = confirmed, false = rejected; "
                "absent = no validated-state filter, including NULL/pending"
            )
        ),
    ] = None,
    min_hotspot_score: Annotated[
        float | None,
        Query(ge=0.0, le=1.0, description="Minimum hotspot_score threshold"),
    ] = None,
) -> PredictionFeatureCollection:
    """Retrieve invasion predictions as a GeoJSON FeatureCollection.

    Results are ordered by ``hotspot_score DESC``.  The ``validated`` filter
    accepts ``true`` (confirmed) or ``false`` (rejected).  When omitted, all
    rows are returned including those with ``validated=NULL`` (pending).
    """
    # validated is not None when the caller explicitly provided the parameter;
    # None means absent → no validated-state filter (FR-026).
    validated_filter_present = validated is not None

    return await query_predictions(
        db=db,
        roi_id=roi_id,
        species_label=species_label,
        validated=validated,
        validated_filter_present=validated_filter_present,
        min_hotspot_score=min_hotspot_score,
    )

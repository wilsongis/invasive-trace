"""GET /api/v1/predictions — GeoJSON FeatureCollection of invasion predictions."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.prediction import InvasionPrediction
from app.schemas.prediction import (
    PredictionFeatureCollection,
    ValidationRequest,
    ValidationResponse,
)
from app.services.prediction_query import query_predictions
from app.services.retrain_trigger import check_retrain_trigger

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


@router.patch("/{prediction_id}/validate", response_model=ValidationResponse)
async def validate_prediction(
    prediction_id: UUID,
    body: ValidationRequest,
    db: DbSession,
) -> ValidationResponse:
    """Update the validation state of a prediction.

    Args:
        prediction_id: UUID of the prediction to update.
        body: ValidationRequest with validated (bool) and optional validator_notes.
        db: Async SQLAlchemy session.

    Returns:
        ValidationResponse with updated prediction and retraining trigger status.

    Raises:
        HTTPException: 404 if prediction not found.
    """
    stmt = select(InvasionPrediction).where(InvasionPrediction.id == prediction_id)
    result = await db.execute(stmt)
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction {prediction_id} not found",
        )

    prediction.validated = body.validated
    prediction.validator_notes = body.validator_notes
    await db.commit()
    await db.refresh(prediction)

    retraining_triggered = await check_retrain_trigger(db)

    return ValidationResponse(
        id=prediction.id,
        roi_id=prediction.roi_id,
        species_label=prediction.species_label,
        confidence=prediction.confidence,
        hotspot_score=prediction.hotspot_score,
        model_version=prediction.model_version,
        predicted_at=prediction.predicted_at,
        validated=prediction.validated,
        validator_notes=prediction.validator_notes,
        retraining_triggered=retraining_triggered,
    )

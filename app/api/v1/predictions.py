"""GET /api/v1/predictions — GeoJSON FeatureCollection of invasion predictions.
   PATCH /api/v1/predictions/{id}/validate — Update validation state of a prediction."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

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


@router.patch("/{id}/validate")
async def validate_prediction(
    id: UUID,
    payload: ValidationRequest,
    db: DbSession,
) -> ValidationResponse:
    """Update the validation state and notes for a prediction.

    Updates ``invasion_predictions.validated`` to the provided boolean value and
    ``invasion_predictions.validator_notes`` to the provided string (or NULL if omitted).
    Returns the updated prediction record with a flag indicating if retraining was triggered.

    Args:
        id: UUID of the prediction to update
        payload: ValidationRequest with validated (bool) and validator_notes (str | None)
        db: Async SQLAlchemy session

    Returns:
        ValidationResponse with updated prediction data and retraining_triggered flag

    Raises:
        HTTPException 404: If prediction with given ID does not exist
    """
    # Look up the prediction by ID
    stmt = select(InvasionPrediction).where(InvasionPrediction.id == id)
    result = await db.execute(stmt)
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction with ID {id} not found",
        )

    # Update the prediction with the new validation state and notes
    prediction.validated = payload.validated
    prediction.validator_notes = payload.validator_notes

    # Commit the changes to the database
    await db.commit()
    await db.refresh(prediction)

    # Check if retraining should be triggered
    retraining_triggered = await check_retrain_trigger(db)

    # Return the updated prediction with retraining status
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

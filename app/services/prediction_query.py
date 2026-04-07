"""GeoJSON retrieval service for invasion_predictions with optional filtering."""

from __future__ import annotations

import logging
from uuid import UUID

from geoalchemy2.shape import to_shape
from shapely.geometry import mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prediction import InvasionPrediction
from app.schemas.prediction import (
    PredictionFeature,
    PredictionFeatureCollection,
    PredictionProperties,
)

logger = logging.getLogger(__name__)


async def query_predictions(
    db: AsyncSession,
    roi_id: UUID | None = None,
    species_label: str | None = None,
    validated: bool | None = None,
    validated_filter_present: bool = False,
    min_hotspot_score: float | None = None,
) -> PredictionFeatureCollection:
    """Retrieve invasion_predictions as a GeoJSON FeatureCollection.

    Args:
        db: Async SQLAlchemy session.
        roi_id: Filter to a specific ROI (optional).
        species_label: Exact-match filter on species label (optional).
        validated: True = confirmed, False = rejected (optional).
        validated_filter_present: When True, apply the validated filter (including
            False). When False, omit the validated filter to return all rows (FR-026).
        min_hotspot_score: Include only rows where hotspot_score >= value (optional).

    Returns:
        PredictionFeatureCollection ordered by hotspot_score DESC.
    """
    try:
        stmt = select(InvasionPrediction).order_by(
            InvasionPrediction.hotspot_score.desc().nullslast()
        )

        if roi_id is not None:
            stmt = stmt.where(InvasionPrediction.roi_id == roi_id)

        if species_label is not None:
            stmt = stmt.where(InvasionPrediction.species_label == species_label)

        if validated_filter_present:
            stmt = stmt.where(InvasionPrediction.validated == validated)

        if min_hotspot_score is not None:
            stmt = stmt.where(InvasionPrediction.hotspot_score >= min_hotspot_score)

        result = await db.execute(stmt)
        rows = result.scalars().all()

        features: list[PredictionFeature] = []
        for pred in rows:
            point = to_shape(pred.geom)
            features.append(
                PredictionFeature(
                    geometry=dict(mapping(point)),
                    properties=PredictionProperties(
                        id=pred.id,
                        roi_id=pred.roi_id,
                        species_label=pred.species_label,
                        confidence=pred.confidence,
                        hotspot_score=pred.hotspot_score,
                        model_version=pred.model_version,
                        predicted_at=pred.predicted_at,
                        validated=pred.validated,
                    ),
                )
            )

        return PredictionFeatureCollection(features=features)
    except Exception as e:
        logger.error("Failed to query predictions: %s", e, exc_info=True)
        return PredictionFeatureCollection(features=[])

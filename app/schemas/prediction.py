"""Pydantic schemas for GET /api/v1/predictions GeoJSON output and validation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PredictionProperties(BaseModel):
    """Properties block for each GeoJSON prediction Feature."""

    id: UUID
    roi_id: UUID
    species_label: str
    confidence: float
    hotspot_score: float | None
    model_version: str
    predicted_at: datetime
    validated: bool | None


class PredictionFeature(BaseModel):
    """GeoJSON Feature wrapping one invasion_predictions row."""

    type: str = "Feature"
    geometry: dict[str, Any]
    properties: PredictionProperties


class PredictionFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection of invasion predictions."""

    type: str = "FeatureCollection"
    features: list[PredictionFeature]


class ValidationRequest(BaseModel):
    """Request body for PATCH /api/v1/predictions/{id}/validate."""

    model_config = {"strict": True}

    validated: bool
    validator_notes: str | None = Field(default=None, max_length=1000)


class ValidationResponse(BaseModel):
    """Response body for PATCH /api/v1/predictions/{id}/validate."""

    id: UUID
    roi_id: UUID
    species_label: str
    confidence: float
    hotspot_score: float | None
    model_version: str
    predicted_at: datetime
    validated: bool | None
    validator_notes: str | None
    retraining_triggered: bool

"""Pydantic schemas for remote sensing scene ingestion and retrieval."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class SceneDateRange(BaseModel):
    """Date window echoed by ingestion responses."""

    start: date
    end: date


class SceneIngestRequest(BaseModel):
    """Request payload for ROI-scoped scene ingestion."""

    roi_id: UUID
    start_date: date
    end_date: date
    platform: str = Field(default="sentinel-2")

    @model_validator(mode="after")
    def validate_window_and_platform(self) -> SceneIngestRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        if self.platform != "sentinel-2":
            raise ValueError("platform must be 'sentinel-2' for Wave 005")
        return self


class SceneIngestResponse(BaseModel):
    """Summary of one ingestion execution."""

    roi_id: UUID
    scenes_queried: int = Field(ge=0)
    scenes_inserted: int = Field(ge=0)
    scenes_updated: int = Field(ge=0)
    scenes_masked: int = Field(ge=0)
    scenes_skipped: int = Field(ge=0)
    date_range: SceneDateRange


class SpectralRecord(BaseModel):
    """Serialized spectral time-series row."""

    id: UUID
    roi_id: UUID
    scene_date: date
    platform: str
    stac_item: str
    ndvi: float | None
    endvi: float | None
    red_edge: float | None
    cloud_cover: float | None
    is_masked: bool

    model_config = {"from_attributes": True}

"""Pydantic schemas for SGI project metrics."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MetricBase(BaseModel):
    """Common fields for a project metric record."""

    roi_id: uuid.UUID = Field(..., description="Foreign key to regions_of_interest")
    restored_acres: float | None = Field(None, description="Total restored acres")
    ndvi_improvement: float | None = Field(None, description="Average NDVI improvement")
    confidence_mean: float | None = Field(None, description="Mean prediction confidence")
    pipeline_run_id: str | None = Field(None, description="Identifier for the pipeline run")


class MetricCreate(MetricBase):
    """Fields required when creating a new metric record."""

    pass


class Metric(MetricBase):
    """Schema returned from the API, includes database identifiers."""

    id: uuid.UUID = Field(..., description="Primary key of the metric record")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True

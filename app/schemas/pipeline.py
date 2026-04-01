"""Pydantic schemas for the Wave 3 AI pipeline trigger endpoint."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class PipelineRunResponse(BaseModel):
    """Response payload from POST /api/v1/rois/{id}/pipeline/run."""

    roi_id: UUID
    predictions_created: int = Field(ge=0)
    model_version: str
    message: str

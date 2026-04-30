"""SQLAlchemy models for project KPIs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ProjectMetric(Base):
    """Canonical model for SGI Way project metrics (KPIs)."""

    __tablename__ = "project_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    roi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions_of_interest.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    restored_acres: Mapped[float | None] = mapped_column(Float, nullable=True)
    ndvi_improvement: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    # Track the pipeline run that generated these metrics
    pipeline_run_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    
    roi = relationship("RegionOfInterest")

"""Invasion prediction ORM model."""

import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class InvasionPrediction(Base):
    """Canonical model inference output tied to a region of interest."""

    __tablename__ = "invasion_predictions"
    __table_args__ = (
        CheckConstraint(
            "confidence BETWEEN 0.0 AND 1.0",
            name="ck_invasion_predictions_confidence",
        ),
        Index("idx_pred_geom", "geom", postgresql_using="gist"),
        Index("idx_pred_roi", "roi_id"),
        Index("idx_pred_score", text("hotspot_score DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    roi_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions_of_interest.id", ondelete="CASCADE"),
        nullable=False,
    )
    species_label: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    hotspot_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    validated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    validator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    roi = relationship("RegionOfInterest", back_populates="predictions")

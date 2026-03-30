"""Spectral time series ORM model."""

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SpectralTimeSeries(Base):
    """Per-scene spectral features for each region of interest."""

    __tablename__ = "spectral_time_series"
    __table_args__ = (
        CheckConstraint(
            "platform IN ('sentinel-2', 'landsat-hls', 'naip')",
            name="ck_spectral_time_series_platform",
        ),
        Index("idx_sts_roi_date", "roi_id", text("scene_date DESC")),
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
    scene_date: Mapped[date] = mapped_column(Date, nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    stac_item: Mapped[str] = mapped_column(Text, nullable=False)
    ndvi: Mapped[float | None] = mapped_column(Float, nullable=True)
    endvi: Mapped[float | None] = mapped_column(Float, nullable=True)
    red_edge: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_masked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))

    roi = relationship("RegionOfInterest", back_populates="spectral_rows")

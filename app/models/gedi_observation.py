"""SQLAlchemy models for NASA GEDI observations."""

import uuid
from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GediObservation(Base):
    """Canonical table for GEDI Level-2A footprint observations."""

    __tablename__ = "gedi_observations"
    __table_args__ = (
        Index("idx_gedi_geom", "geom", postgresql_using="gist"),
        Index("idx_gedi_date", text("acquisition_date DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    footprint_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    
    canopy_height: Mapped[float] = mapped_column(Float, nullable=False)
    biomass: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flag: Mapped[int] = mapped_column(Integer, nullable=False)
    
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

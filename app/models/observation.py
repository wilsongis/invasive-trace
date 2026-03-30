"""Ground truth observation ORM model."""

import uuid
from datetime import date
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Date, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GroundTruthObservation(Base):
    """Canonical external observation records from iNaturalist/EDDMapS/field surveys."""

    __tablename__ = "ground_truth_observations"
    __table_args__ = (
        CheckConstraint(
            "source IN ('iNaturalist', 'EDDMapS', 'field_survey')",
            name="ck_ground_truth_observations_source",
        ),
        Index("idx_gto_geom", "geom", postgresql_using="gist"),
        Index("idx_gto_source", "source"),
        # Deterministic duplicate identity for external source payloads with external IDs.
        Index(
            "uq_gto_source_external_id_not_null",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    species_label: Mapped[str] = mapped_column(Text, nullable=False)
    observer: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    geom = mapped_column(Geometry("POINT", srid=4326), nullable=False)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

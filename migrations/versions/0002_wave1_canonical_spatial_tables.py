"""Create canonical Wave 1 spatial tables.

Revision ID: 0002_wave1_spatial_tables
Revises: 0001_baseline
Create Date: 2026-03-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_wave1_spatial_tables"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "regions_of_interest",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("geom", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_roi_geom",
        "regions_of_interest",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )

    op.create_table(
        "ground_truth_observations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column("species_label", sa.Text(), nullable=False),
        sa.Column("observer", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.Date(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("is_confirmed", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "source IN ('iNaturalist', 'EDDMapS', 'field_survey')",
            name="ck_ground_truth_observations_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_gto_geom",
        "ground_truth_observations",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index("idx_gto_source", "ground_truth_observations", ["source"], unique=False)
    op.create_index(
        "uq_gto_source_external_id_not_null",
        "ground_truth_observations",
        ["source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    op.create_table(
        "spectral_time_series",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("roi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scene_date", sa.Date(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("stac_item", sa.Text(), nullable=False),
        sa.Column("ndvi", sa.Float(), nullable=True),
        sa.Column("endvi", sa.Float(), nullable=True),
        sa.Column("red_edge", sa.Float(), nullable=True),
        sa.Column("cloud_cover", sa.Float(), nullable=True),
        sa.Column("is_masked", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.CheckConstraint(
            "platform IN ('sentinel-2', 'landsat-hls', 'naip')",
            name="ck_spectral_time_series_platform",
        ),
        sa.ForeignKeyConstraint(["roi_id"], ["regions_of_interest.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sts_roi_date",
        "spectral_time_series",
        ["roi_id", sa.text("scene_date DESC")],
        unique=False,
    )

    op.create_table(
        "invasion_predictions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("roi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("species_label", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("hotspot_score", sa.Float(), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column(
            "predicted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("validated", sa.Boolean(), nullable=True),
        sa.Column("validator_notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "confidence BETWEEN 0.0 AND 1.0",
            name="ck_invasion_predictions_confidence",
        ),
        sa.ForeignKeyConstraint(["roi_id"], ["regions_of_interest.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_pred_geom",
        "invasion_predictions",
        ["geom"],
        unique=False,
        postgresql_using="gist",
    )
    op.create_index("idx_pred_roi", "invasion_predictions", ["roi_id"], unique=False)
    op.create_index(
        "idx_pred_score",
        "invasion_predictions",
        [sa.text("hotspot_score DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_pred_score", table_name="invasion_predictions")
    op.drop_index("idx_pred_roi", table_name="invasion_predictions")
    op.drop_index("idx_pred_geom", table_name="invasion_predictions")
    op.drop_table("invasion_predictions")

    op.drop_index("idx_sts_roi_date", table_name="spectral_time_series")
    op.drop_table("spectral_time_series")

    op.drop_index("uq_gto_source_external_id_not_null", table_name="ground_truth_observations")
    op.drop_index("idx_gto_source", table_name="ground_truth_observations")
    op.drop_index("idx_gto_geom", table_name="ground_truth_observations")
    op.drop_table("ground_truth_observations")

    op.drop_index("idx_roi_geom", table_name="regions_of_interest")
    op.drop_table("regions_of_interest")

"""Add SGI enhancement tables.

Revision ID: 0005_sgi_enhancement_tables
Revises: 0004_ground_truth_roi_fk
Create Date: 2026-04-30 06:00:00.000000

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005_sgi_enhancement_tables"
down_revision = "0004_ground_truth_roi_fk"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # restoration_protocols
    op.create_table(
        "restoration_protocols",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # project_metrics
    op.create_table(
        "project_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("roi_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("restored_acres", sa.Float(), nullable=True),
        sa.Column("ndvi_improvement", sa.Float(), nullable=True),
        sa.Column("confidence_mean", sa.Float(), nullable=True),
        sa.Column("pipeline_run_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["roi_id"], ["regions_of_interest.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # gedi_observations
    op.create_table(
        "gedi_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("footprint_id", sa.Text(), nullable=False),
        sa.Column("acquisition_date", sa.Date(), nullable=False),
        sa.Column("canopy_height", sa.Float(), nullable=False),
        sa.Column("biomass", sa.Float(), nullable=True),
        sa.Column("quality_flag", sa.Integer(), nullable=False),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, from_text="ST_GeomFromEWKT", name="geometry"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("footprint_id"),
    )
    op.create_index("idx_gedi_date", "gedi_observations", [sa.text("acquisition_date DESC")], unique=False)
    op.create_index("idx_gedi_geom", "gedi_observations", ["geom"], unique=False, postgresql_using="gist")

def downgrade() -> None:
    op.drop_index("idx_gedi_geom", table_name="gedi_observations", postgresql_using="gist")
    op.drop_index("idx_gedi_date", table_name="gedi_observations")
    op.drop_table("gedi_observations")
    op.drop_table("project_metrics")
    op.drop_table("restoration_protocols")

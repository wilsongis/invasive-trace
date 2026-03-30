"""Add unique upsert constraint for spectral scene ingestion.

Revision ID: 0003_spectral_upsert_constraint
Revises: 0002_wave1_spatial_tables
Create Date: 2026-03-30
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_spectral_upsert_constraint"
down_revision: str | None = "0002_wave1_spatial_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_spectral_roi_item",
        "spectral_time_series",
        ["roi_id", "stac_item"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_spectral_roi_item", "spectral_time_series", type_="unique")

"""Add roi_id foreign key to ground_truth_observations.

Revision ID: 0004_ground_truth_roi_fk
Revises: 0003_spectral_upsert_constraint
Create Date: 2026-04-30 05:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_ground_truth_roi_fk"
down_revision = "0003_spectral_upsert_constraint"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Disable ROI enforcement temporarily for legacy ground truth seeding
    op.add_column("ground_truth_observations", sa.Column("roi_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_ground_truth_observations_roi_id",
        "ground_truth_observations",
        "regions_of_interest",
        ["roi_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ground_truth_observations_roi_id", "ground_truth_observations", type_="foreignkey")
    op.drop_column("ground_truth_observations", "roi_id")

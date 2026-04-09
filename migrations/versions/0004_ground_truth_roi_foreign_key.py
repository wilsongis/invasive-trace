"""Add roi_id foreign key to ground_truth_observations.

Revision ID: 0004_ground_truth_roi_foreign_key
Revises: 0003_spectral_upsert_constraint
Create Date: 2026-04-09
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_ground_truth_roi_foreign_key"
down_revision: str | None = "0003_spectral_upsert_constraint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ground_truth_observations",
        op.column("roi_id", op.types.Uuid()),
    )
    op.create_foreign_key(
        "fk_gto_roi_id",
        "ground_truth_observations",
        "regions_of_interest",
        ["roi_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("idx_gto_roi", "ground_truth_observations", ["roi_id"])


def downgrade() -> None:
    op.drop_index("idx_gto_roi", table_name="ground_truth_observations")
    op.drop_constraint("fk_gto_roi_id", "ground_truth_observations", type_="foreignkey")
    op.drop_column("ground_truth_observations", "roi_id")

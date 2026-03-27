"""Wave 0 baseline migration scaffold — no domain tables yet.

Revision ID: 0001_baseline
Revises: (none)
Create Date: 2026-03-27
"""

import sqlalchemy as sa  # noqa: F401
from alembic import op  # noqa: F401

# Revision identifiers, used by Alembic.
revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Wave 0 baseline — migration plumbing only, no tables created."""
    pass


def downgrade() -> None:
    """Wave 0 baseline — nothing to roll back."""
    pass

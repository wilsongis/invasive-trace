"""Alembic migration script template."""

# ${message}

# Revision identifiers, used by Alembic.
# revision: ${up_revision}
# down_revision: ${down_revision | comma,n}
# branch_labels: ${branch_labels | comma,n}
# depends_on: ${depends_on | comma,n}

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401
${imports if imports else ""}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}

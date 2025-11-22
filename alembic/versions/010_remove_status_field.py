"""Remove status field from game_participants

Revision ID: 010_remove_status_field
Revises: 009_add_pre_filled_position
Create Date: 2025-11-22

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_remove_status_field"
down_revision: str | None = "009_add_pre_filled_position"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove status column from game_participants table."""
    op.drop_column("game_participants", "status")


def downgrade() -> None:
    """Restore status column to game_participants table."""
    op.add_column(
        "game_participants",
        sa.Column("status", sa.String(20), nullable=False, server_default="JOINED"),
    )

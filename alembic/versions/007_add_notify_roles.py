"""Add notify_role_ids field to game_sessions

Revision ID: 007_notify_roles
Revises: 006_bot_mgr_roles
Create Date: 2025-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_notify_roles"
down_revision: str | None = "006_bot_mgr_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add notify_role_ids field to game_sessions."""
    op.add_column(
        "game_sessions",
        sa.Column("notify_role_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove notify_role_ids field from game_sessions."""
    op.drop_column("game_sessions", "notify_role_ids")

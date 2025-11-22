"""add_min_players_field

Revision ID: 004_add_min_players_field
Revises: 003_remove_host_participant
Create Date: 2025-11-21 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_add_min_players_field"
down_revision: str | None = "003_remove_host_participant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add min_players field to game_sessions table.

    This migration adds a min_players column with NOT NULL constraint
    and default value of 1 to specify the minimum number of participants
    required for a game to proceed.
    """
    op.add_column(
        "game_sessions",
        sa.Column("min_players", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    """Remove min_players field from game_sessions table.

    This restores the previous schema without minimum player tracking.
    """
    op.drop_column("game_sessions", "min_players")

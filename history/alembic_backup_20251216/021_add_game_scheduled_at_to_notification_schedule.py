# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Add game_scheduled_at column to notification_schedule table

Revision ID: 021_add_game_scheduled_at
Revises: 020_add_game_status_schedule
Create Date: 2025-12-05

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "021_add_game_scheduled_at"
down_revision: str | None = "020_add_game_status_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Add game_scheduled_at column to notification_schedule table.

    Denormalizes game.scheduled_at to enable per-message TTL calculation
    without requiring JOIN or relationship loading in the daemon.
    """
    # Add column as nullable first
    op.add_column(
        "notification_schedule",
        sa.Column("game_scheduled_at", sa.DateTime(), nullable=True),
    )

    # Backfill existing rows from game_sessions table
    op.execute(
        """
        UPDATE notification_schedule ns
        SET game_scheduled_at = gs.scheduled_at
        FROM game_sessions gs
        WHERE ns.game_id = gs.id
        """
    )

    # Set column to NOT NULL after backfill
    op.alter_column("notification_schedule", "game_scheduled_at", nullable=False)


def downgrade() -> None:
    """Remove game_scheduled_at column from notification_schedule table."""
    op.drop_column("notification_schedule", "game_scheduled_at")

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


"""Remove min_players field from game_sessions

Revision ID: 015_remove_min_players_field
Revises: 014_add_where_field
Create Date: 2025-11-30

Removes the min_players field as it is no longer used.
Participant counts now display as "X/max" instead of "X/min-max".
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015_remove_min_players_field"
down_revision: str | None = "014_add_where_field"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove min_players field from game_sessions table."""
    op.drop_column("game_sessions", "min_players")


def downgrade() -> None:
    """Restore min_players field to game_sessions table."""
    op.add_column(
        "game_sessions",
        sa.Column("min_players", sa.Integer(), nullable=False, server_default="1"),
    )

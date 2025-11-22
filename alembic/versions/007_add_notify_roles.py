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

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


"""replace_prefilled_position_with_position_fields

Revision ID: 8438728f8184
Revises: 3aeec3d09d7c
Create Date: 2025-12-24 14:20:24.629827

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8438728f8184"
down_revision: str | None = "3aeec3d09d7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace pre_filled_position with position_type and position fields."""

    # Add new columns with temporary defaults
    op.add_column("game_participants", sa.Column("position_type", sa.SmallInteger(), nullable=True))
    op.add_column("game_participants", sa.Column("position", sa.SmallInteger(), nullable=True))

    # Data migration: Transform existing values
    op.execute(
        """
        UPDATE game_participants
        SET
            position_type = CASE
                WHEN pre_filled_position IS NOT NULL THEN 8000  -- HOST_ADDED
                ELSE 24000  -- SELF_ADDED
            END,
            position = CASE
                WHEN pre_filled_position IS NOT NULL THEN pre_filled_position
                ELSE 0
            END
    """
    )

    # Make columns non-nullable now that data is migrated
    op.alter_column("game_participants", "position_type", nullable=False)
    op.alter_column("game_participants", "position", nullable=False)

    # Remove old column
    op.drop_column("game_participants", "pre_filled_position")


def downgrade() -> None:
    """Restore pre_filled_position from position_type and position."""

    # Add back old column
    op.add_column(
        "game_participants", sa.Column("pre_filled_position", sa.Integer(), nullable=True)
    )

    # Reverse data migration: Only restore host-added positions
    op.execute(
        """
        UPDATE game_participants
        SET pre_filled_position = CASE
            WHEN position_type = 8000 THEN position  -- HOST_ADDED
            ELSE NULL  -- SELF_ADDED
        END
    """
    )

    # Remove new columns
    op.drop_column("game_participants", "position")
    op.drop_column("game_participants", "position_type")

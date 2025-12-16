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


"""change_timestamps_to_timezone_naive

Revision ID: 9eb33bf3186b
Revises: 001_initial_schema
Create Date: 2025-11-17 16:49:56.303137

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9eb33bf3186b"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Change all datetime columns from TIMESTAMP WITH TIME ZONE to TIMESTAMP WITHOUT TIME ZONE."""
    # Users table
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # Guild configurations table
    op.execute(
        "ALTER TABLE guild_configurations ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE guild_configurations ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # Channel configurations table
    op.execute(
        "ALTER TABLE channel_configurations "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute(
        "ALTER TABLE channel_configurations "
        "ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )

    # Game sessions table
    op.execute(
        "ALTER TABLE game_sessions ALTER COLUMN scheduled_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )
    op.execute("ALTER TABLE game_sessions ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE")
    op.execute("ALTER TABLE game_sessions ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE")

    # Game participants table
    op.execute(
        "ALTER TABLE game_participants ALTER COLUMN joined_at TYPE TIMESTAMP WITHOUT TIME ZONE"
    )


def downgrade() -> None:
    """Revert all datetime columns back to TIMESTAMP WITH TIME ZONE."""
    # Game participants table
    op.execute("ALTER TABLE game_participants ALTER COLUMN joined_at TYPE TIMESTAMP WITH TIME ZONE")

    # Game sessions table
    op.execute("ALTER TABLE game_sessions ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE game_sessions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE game_sessions ALTER COLUMN scheduled_at TYPE TIMESTAMP WITH TIME ZONE")

    # Channel configurations table
    op.execute(
        "ALTER TABLE channel_configurations ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE channel_configurations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # Guild configurations table
    op.execute(
        "ALTER TABLE guild_configurations ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE"
    )
    op.execute(
        "ALTER TABLE guild_configurations ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE"
    )

    # Users table
    op.execute("ALTER TABLE users ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE users ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE")

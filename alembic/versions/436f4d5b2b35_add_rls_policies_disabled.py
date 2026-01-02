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


"""Add RLS policies (disabled initially).

Revision ID: 436f4d5b2b35
Revises: b49eb343d5a6
Create Date: 2026-01-02

"""

from collections.abc import Sequence

from alembic import op

revision: str = "436f4d5b2b35"
down_revision: str | None = "b49eb343d5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create RLS policies for guild isolation (disabled).

    Policies will be enabled in future migration after service migration complete.
    """
    op.create_index(
        "idx_game_sessions_guild_id",
        "game_sessions",
        ["guild_id"],
        if_not_exists=True,
    )
    op.create_index(
        "idx_game_templates_guild_id",
        "game_templates",
        ["guild_id"],
        if_not_exists=True,
    )

    # Game sessions policy
    op.execute(
        """
        CREATE POLICY guild_isolation_games ON game_sessions
        FOR ALL
        USING (
            guild_id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
        )
    """
    )

    # Game templates policy
    op.execute(
        """
        CREATE POLICY guild_isolation_templates ON game_templates
        FOR ALL
        USING (
            guild_id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
        )
    """
    )

    # Game participants policy (via join to game_sessions)
    op.execute(
        """
        CREATE POLICY guild_isolation_participants ON game_participants
        FOR ALL
        USING (
            game_session_id IN (
                SELECT id FROM game_sessions
                WHERE guild_id::text = ANY(
                    string_to_array(
                        current_setting('app.current_guild_ids', true),
                        ','
                    )
                )
            )
        )
    """
    )


def downgrade() -> None:
    """Remove RLS policies."""
    op.execute("DROP POLICY IF EXISTS guild_isolation_games ON game_sessions")
    op.execute("DROP POLICY IF EXISTS guild_isolation_templates ON game_templates")
    op.execute("DROP POLICY IF EXISTS guild_isolation_participants ON game_participants")

    op.drop_index("idx_game_templates_guild_id", "game_templates", if_exists=True)
    op.drop_index("idx_game_sessions_guild_id", "game_sessions", if_exists=True)

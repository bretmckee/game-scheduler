# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


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

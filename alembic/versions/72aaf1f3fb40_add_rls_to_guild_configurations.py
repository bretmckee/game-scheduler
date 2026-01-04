# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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


"""Add RLS policy and enable on guild_configurations table.

This migration creates and enables row-level security for guild_configurations,
enforcing guild-level data isolation at the database layer. The policy ensures
users can only access guild configurations for guilds they are members of.

Revision ID: 72aaf1f3fb40
Revises: 13625652ab09
Create Date: 2026-01-03 15:56:43.030403

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "72aaf1f3fb40"
down_revision: str | None = "13625652ab09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """
    Create RLS policy for guild_configurations and enable RLS.

    The policy enforces guild isolation by checking if the guild_id exists in
    the current_guild_ids session variable set by the application middleware.
    """
    # Create index for policy performance (if not already exists)
    op.create_index(
        "idx_guild_configurations_guild_id",
        "guild_configurations",
        ["guild_id"],
        if_not_exists=True,
    )

    # Create RLS policy for guild isolation
    op.execute(
        """
        CREATE POLICY guild_isolation_configurations ON guild_configurations
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

    # Enable RLS on guild_configurations table
    op.execute("ALTER TABLE guild_configurations ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable RLS and remove policy from guild_configurations table."""
    # Disable RLS first
    op.execute("ALTER TABLE guild_configurations DISABLE ROW LEVEL SECURITY")

    # Drop policy
    op.execute("DROP POLICY IF EXISTS guild_isolation_configurations ON guild_configurations")

    # Drop index
    op.drop_index("idx_guild_configurations_guild_id", "guild_configurations", if_exists=True)

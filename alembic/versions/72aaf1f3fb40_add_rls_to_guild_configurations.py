# Copyright 2026 Bret McKee
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

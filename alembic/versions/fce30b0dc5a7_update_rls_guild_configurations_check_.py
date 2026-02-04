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


"""Update RLS policy on guild_configurations to check both id and guild_id.

This allows the table to be queried using either database UUIDs (id) or Discord
snowflakes (guild_id) in the RLS context. This solves the chicken-and-egg problem
where we need to query guild_configurations to convert Discord IDs to UUIDs, but
the table is RLS-protected and requires context to be set first.

With this policy, the flow becomes:
1. Set app.current_guild_ids to Discord snowflakes (from cache/OAuth)
2. Query guild_configurations (allowed via guild_id match)
3. Get database UUIDs
4. Update app.current_guild_ids to database UUIDs for other tables

Revision ID: fce30b0dc5a7
Revises: 72aaf1f3fb40
Create Date: 2026-01-04 19:07:48.188874

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fce30b0dc5a7"
down_revision: str | None = "72aaf1f3fb40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update RLS policy to check both id and guild_id fields."""
    # Drop existing policy
    op.execute("DROP POLICY IF EXISTS guild_isolation_configurations ON guild_configurations")

    # Create updated policy that checks both fields
    op.execute(
        """
        CREATE POLICY guild_isolation_configurations ON guild_configurations
        FOR ALL
        USING (
            -- Match by database UUID (for queries after conversion)
            id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
            OR
            -- Match by Discord snowflake (for initial lookup before conversion)
            guild_id::text = ANY(
                string_to_array(
                    current_setting('app.current_guild_ids', true),
                    ','
                )
            )
        )
    """
    )


def downgrade() -> None:
    """Revert to original policy that only checks guild_id."""
    # Drop the updated policy
    op.execute("DROP POLICY IF EXISTS guild_isolation_configurations ON guild_configurations")

    # Restore original policy (guild_id only)
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

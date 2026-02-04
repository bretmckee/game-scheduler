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


"""add_cascade_delete_guild_channel_template

Revision ID: cc016b875896
Revises: fce30b0dc5a7
Create Date: 2026-02-02 05:17:06.042133

Add CASCADE delete to foreign keys in the guild→channel→template→game hierarchy.

This ensures that when a guild is deleted, all associated channels, templates, and games
are automatically removed, preventing orphaned records and simplifying cleanup logic.

Foreign keys updated:
- channel_configurations.guild_id → guild_configurations.id (add CASCADE)
- game_templates.guild_id → guild_configurations.id (add CASCADE)
- game_templates.channel_id → channel_configurations.id (add CASCADE)
- game_sessions.guild_id → guild_configurations.id (add CASCADE)
- game_sessions.channel_id → channel_configurations.id (add CASCADE)

Note: game_sessions already has CASCADE on game_participants and notifications,
so the full cascade chain is: guild → channels/templates/games → participants/notifications
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cc016b875896"
down_revision: str | None = "fce30b0dc5a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop existing foreign keys
    op.drop_constraint(
        "channel_configurations_guild_id_fkey",
        "channel_configurations",
        type_="foreignkey",
    )
    op.drop_constraint("game_templates_guild_id_fkey", "game_templates", type_="foreignkey")
    op.drop_constraint("game_templates_channel_id_fkey", "game_templates", type_="foreignkey")
    op.drop_constraint("game_sessions_guild_id_fkey", "game_sessions", type_="foreignkey")
    op.drop_constraint("game_sessions_channel_id_fkey", "game_sessions", type_="foreignkey")

    # Recreate foreign keys with CASCADE
    op.create_foreign_key(
        "channel_configurations_guild_id_fkey",
        "channel_configurations",
        "guild_configurations",
        ["guild_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "game_templates_guild_id_fkey",
        "game_templates",
        "guild_configurations",
        ["guild_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "game_templates_channel_id_fkey",
        "game_templates",
        "channel_configurations",
        ["channel_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "game_sessions_guild_id_fkey",
        "game_sessions",
        "guild_configurations",
        ["guild_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "game_sessions_channel_id_fkey",
        "game_sessions",
        "channel_configurations",
        ["channel_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop CASCADE foreign keys
    op.drop_constraint(
        "channel_configurations_guild_id_fkey",
        "channel_configurations",
        type_="foreignkey",
    )
    op.drop_constraint("game_templates_guild_id_fkey", "game_templates", type_="foreignkey")
    op.drop_constraint("game_templates_channel_id_fkey", "game_templates", type_="foreignkey")
    op.drop_constraint("game_sessions_guild_id_fkey", "game_sessions", type_="foreignkey")
    op.drop_constraint("game_sessions_channel_id_fkey", "game_sessions", type_="foreignkey")

    # Recreate original foreign keys without CASCADE
    op.create_foreign_key(
        "channel_configurations_guild_id_fkey",
        "channel_configurations",
        "guild_configurations",
        ["guild_id"],
        ["id"],
    )
    op.create_foreign_key(
        "game_templates_guild_id_fkey",
        "game_templates",
        "guild_configurations",
        ["guild_id"],
        ["id"],
    )
    op.create_foreign_key(
        "game_templates_channel_id_fkey",
        "game_templates",
        "channel_configurations",
        ["channel_id"],
        ["id"],
    )
    op.create_foreign_key(
        "game_sessions_guild_id_fkey",
        "game_sessions",
        "guild_configurations",
        ["guild_id"],
        ["id"],
    )
    op.create_foreign_key(
        "game_sessions_channel_id_fkey",
        "game_sessions",
        "channel_configurations",
        ["channel_id"],
        ["id"],
    )

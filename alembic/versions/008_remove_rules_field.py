"""Remove rules field from all tables

Revision ID: 008_remove_rules_field
Revises: 007_notify_roles
Create Date: 2025-11-21 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "008_remove_rules_field"
down_revision = "007_notify_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove rules fields from game_sessions, guild_configurations, and channel_configurations."""
    op.drop_column("game_sessions", "rules")
    op.drop_column("guild_configurations", "default_rules")
    op.drop_column("channel_configurations", "default_rules")


def downgrade() -> None:
    """Restore rules fields to game_sessions, guild_configurations, and channel_configurations."""
    op.add_column(
        "game_sessions",
        sa.Column("rules", sa.Text(), nullable=True),
    )
    op.add_column(
        "guild_configurations",
        sa.Column("default_rules", sa.Text(), nullable=True),
    )
    op.add_column(
        "channel_configurations",
        sa.Column("default_rules", sa.Text(), nullable=True),
    )

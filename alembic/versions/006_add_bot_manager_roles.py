"""Add bot_manager_role_ids field to guild_configurations

Revision ID: 006_bot_mgr_roles
Revises: 005_desc_signup_instr
Create Date: 2025-11-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_bot_mgr_roles"
down_revision: str | None = "005_desc_signup_instr"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add bot_manager_role_ids field to guild_configurations."""
    op.add_column(
        "guild_configurations",
        sa.Column("bot_manager_role_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove bot_manager_role_ids field from guild_configurations."""
    op.drop_column("guild_configurations", "bot_manager_role_ids")

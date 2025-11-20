"""add_unique_game_participant_constraint

Revision ID: 002_add_unique_game_participant
Revises: 9eb33bf3186b
Create Date: 2025-11-20 05:35:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_unique_game_participant"
down_revision: str | None = "9eb33bf3186b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add unique constraint on game_session_id and user_id."""
    op.create_unique_constraint(
        "unique_game_participant",
        "game_participants",
        ["game_session_id", "user_id"],
    )


def downgrade() -> None:
    """Remove unique constraint."""
    op.drop_constraint("unique_game_participant", "game_participants", type_="unique")

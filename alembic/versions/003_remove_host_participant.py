"""remove_host_from_participants

Revision ID: 003_remove_host_participant
Revises: 002_add_unique_game_participant
Create Date: 2025-11-20 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "003_remove_host_participant"
down_revision: str | None = "002_add_unique_game_participant"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Remove GameParticipant records where user_id matches GameSession.host_id.

    This migration ensures hosts are stored only in GameSession.host_id
    and not duplicated in the game_participants table.
    """
    conn = op.get_bind()

    # Delete participant records where the user is the game host
    conn.execute(
        text(
            """
            DELETE FROM game_participants
            WHERE (game_session_id, user_id) IN (
                SELECT id, host_id
                FROM game_sessions
                WHERE host_id IS NOT NULL
            )
            """
        )
    )


def downgrade() -> None:
    """Re-add host as participant for all games.

    This restores the previous behavior where hosts were also participants.
    Note: This uses the earliest joined_at timestamp from existing participants
    or the game's created_at if no participants exist.
    """
    conn = op.get_bind()

    # Re-insert hosts as participants
    # Use game's created_at as joined_at timestamp
    conn.execute(
        text(
            """
            INSERT INTO game_participants (
                game_session_id, user_id, joined_at, status, is_pre_populated
            )
            SELECT
                gs.id,
                gs.host_id,
                gs.created_at,
                'JOINED',
                false
            FROM game_sessions gs
            WHERE gs.host_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM game_participants gp
                WHERE gp.game_session_id = gs.id
                AND gp.user_id = gs.host_id
            )
            """
        )
    )

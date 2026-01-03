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


"""enable_rls_game_participants

Enable Row-Level Security on game_participants table. This activates the
guild_isolation_participants policy created in migration 436f4d5b2b35,
enforcing guild-level data isolation for all participant queries.

Participants are isolated via their parent game_session's guild_id.

Revision ID: 13625652ab09
Revises: d7f8e3a1b9c4
Create Date: 2026-01-02 21:19:00.483198

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "13625652ab09"
down_revision: str | None = "d7f8e3a1b9c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable row-level security on game_participants."""
    op.execute("ALTER TABLE game_participants ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    """Disable row-level security on game_participants."""
    op.execute("ALTER TABLE game_participants DISABLE ROW LEVEL SECURITY")

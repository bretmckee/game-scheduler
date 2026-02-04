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

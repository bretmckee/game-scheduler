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


"""rewards_to_json_list

Revision ID: 310018d6a131
Revises: 07db1045a251
Create Date: 2026-11-14 21:48:53.223168

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.utils.rewards_migration import (
    REWARDS_JSON_TO_TEXT_EXPR,
    REWARDS_TEXT_TO_JSON_EXPR,
)

# revision identifiers, used by Alembic.
revision: str = "310018d6a131"
down_revision: str | None = "07db1045a251"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert game_sessions.rewards from free text to a JSON list of entries."""
    op.execute(
        "ALTER TABLE game_sessions ALTER COLUMN rewards TYPE json "
        f"USING {REWARDS_TEXT_TO_JSON_EXPR}"
    )


def downgrade() -> None:
    """Collapse the rewards JSON list back into a single text value."""
    op.add_column("game_sessions", sa.Column("rewards_text", sa.Text(), nullable=True))
    game_sessions = sa.table("game_sessions", sa.column("rewards_text"))
    op.execute(
        game_sessions.update().values(rewards_text=sa.literal_column(REWARDS_JSON_TO_TEXT_EXPR))
    )
    op.drop_column("game_sessions", "rewards")
    op.alter_column("game_sessions", "rewards_text", new_column_name="rewards")

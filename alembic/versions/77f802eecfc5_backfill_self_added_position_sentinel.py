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


"""backfill_self_added_position_sentinel

Revision ID: 77f802eecfc5
Revises: 20260704_add_bot_action_queue
Create Date: 2026-07-16 16:26:12.919643

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "77f802eecfc5"
down_revision: str | None = "20260704_add_bot_action_queue"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill non-HOST_ADDED rows still at the old default (0) to the new sentinel (32767)."""
    op.execute(
        "UPDATE game_participants SET position = 32767 WHERE position_type != 8000 AND position = 0"
    )


def downgrade() -> None:
    """Restore the old default (0) for non-HOST_ADDED rows at the sentinel (32767)."""
    op.execute(
        "UPDATE game_participants SET position = 0 WHERE position_type != 8000 AND position = 32767"
    )

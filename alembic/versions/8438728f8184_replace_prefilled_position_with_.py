# Copyright 2025-2026 Bret McKee
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


"""replace_prefilled_position_with_position_fields

Revision ID: 8438728f8184
Revises: 3aeec3d09d7c
Create Date: 2025-12-24 14:20:24.629827

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8438728f8184"
down_revision: str | None = "3aeec3d09d7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Replace pre_filled_position with position_type and position fields."""

    # Add new columns with temporary defaults
    op.add_column("game_participants", sa.Column("position_type", sa.SmallInteger(), nullable=True))
    op.add_column("game_participants", sa.Column("position", sa.SmallInteger(), nullable=True))

    # Data migration: Transform existing values
    op.execute(
        """
        UPDATE game_participants
        SET
            position_type = CASE
                WHEN pre_filled_position IS NOT NULL THEN 8000  -- HOST_ADDED
                ELSE 24000  -- SELF_ADDED
            END,
            position = CASE
                WHEN pre_filled_position IS NOT NULL THEN pre_filled_position
                ELSE 0
            END
    """
    )

    # Make columns non-nullable now that data is migrated
    op.alter_column("game_participants", "position_type", nullable=False)
    op.alter_column("game_participants", "position", nullable=False)

    # Remove old column
    op.drop_column("game_participants", "pre_filled_position")


def downgrade() -> None:
    """Restore pre_filled_position from position_type and position."""

    # Add back old column
    op.add_column(
        "game_participants", sa.Column("pre_filled_position", sa.Integer(), nullable=True)
    )

    # Reverse data migration: Only restore host-added positions
    op.execute(
        """
        UPDATE game_participants
        SET pre_filled_position = CASE
            WHEN position_type = 8000 THEN position  -- HOST_ADDED
            ELSE NULL  -- SELF_ADDED
        END
    """
    )

    # Remove new columns
    op.drop_column("game_participants", "position")
    op.drop_column("game_participants", "position_type")

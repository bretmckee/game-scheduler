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


"""add_game_image_storage

Revision ID: 3aeec3d09d7c
Revises: 790845a2735f
Create Date: 2025-12-20 16:07:39.565834

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3aeec3d09d7c"
down_revision: str | None = "790845a2735f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "game_sessions",
        sa.Column("thumbnail_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("thumbnail_mime_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("image_mime_type", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("game_sessions", "image_mime_type")
    op.drop_column("game_sessions", "image_data")
    op.drop_column("game_sessions", "thumbnail_mime_type")
    op.drop_column("game_sessions", "thumbnail_data")

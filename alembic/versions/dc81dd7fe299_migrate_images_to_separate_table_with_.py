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


"""migrate_images_to_separate_table_with_deduplication

Migrate game images from game_sessions table to separate game_images table
with hash-based deduplication and reference counting.

⚠️ WARNING: This migration drops existing image data.
   All images must be re-uploaded after migration.

Revision ID: dc81dd7fe299
Revises: cc016b875896
Create Date: 2026-02-08 03:01:43.689102

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc81dd7fe299"
down_revision: str | None = "cc016b875896"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate to separate game_images table with deduplication."""
    # Drop old image columns from game_sessions (data loss acceptable for non-prod)
    op.drop_column("game_sessions", "thumbnail_data")
    op.drop_column("game_sessions", "thumbnail_mime_type")
    op.drop_column("game_sessions", "image_data")
    op.drop_column("game_sessions", "image_mime_type")

    # Create new game_images table (no RLS policies)
    op.create_table(
        "game_images",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("content_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=False),
        sa.Column("mime_type", sa.String(50), nullable=False),
        sa.Column("reference_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Create index on content_hash for O(1) deduplication lookups
    op.create_index("idx_game_images_content_hash", "game_images", ["content_hash"])

    # Add new FK columns to game_sessions
    op.add_column(
        "game_sessions",
        sa.Column("thumbnail_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "game_sessions",
        sa.Column("banner_image_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Create foreign key constraints with ON DELETE SET NULL
    op.create_foreign_key(
        "fk_game_sessions_thumbnail_id",
        "game_sessions",
        "game_images",
        ["thumbnail_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_game_sessions_banner_image_id",
        "game_sessions",
        "game_images",
        ["banner_image_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert to embedded image columns (data not recoverable)."""
    # Remove FK constraints
    op.drop_constraint("fk_game_sessions_banner_image_id", "game_sessions")
    op.drop_constraint("fk_game_sessions_thumbnail_id", "game_sessions")

    # Remove FK columns
    op.drop_column("game_sessions", "banner_image_id")
    op.drop_column("game_sessions", "thumbnail_id")

    # Drop game_images table
    op.drop_index("idx_game_images_content_hash")
    op.drop_table("game_images")

    # Restore old columns (empty - data not recoverable)
    op.add_column("game_sessions", sa.Column("thumbnail_data", sa.LargeBinary(), nullable=True))
    op.add_column("game_sessions", sa.Column("thumbnail_mime_type", sa.String(50), nullable=True))
    op.add_column("game_sessions", sa.Column("image_data", sa.LargeBinary(), nullable=True))
    op.add_column("game_sessions", sa.Column("image_mime_type", sa.String(50), nullable=True))

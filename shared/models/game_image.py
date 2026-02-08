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


"""Game image model for deduplicated image storage."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base, utc_now


class GameImage(Base):
    """
    Deduplicated image storage with reference counting.

    Images are identified by SHA256 content hash. Multiple games can reference
    the same image, with automatic cleanup when reference count reaches zero.

    No RLS policies - designed for public access via image ID only.
    """

    __tablename__ = "game_images"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    image_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now, onupdate=utc_now, server_default=func.now()
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<GameImage(id={self.id}, hash={self.content_hash[:16]}..., "
            f"mime={self.mime_type}, refs={self.reference_count})>"
        )

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


"""Game participant model."""

from datetime import datetime
from enum import IntEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .user import User


class ParticipantType(IntEnum):
    """Participant type enumeration with sparse values for future expansion.

    NOTE: Changes to these values must be mirrored in the TypeScript enum
    located at frontend/src/types/index.ts
    """

    HOST_ADDED = 8000  # High priority (sorts first)
    SELF_ADDED = 24000  # Low priority (sorts last)


class GameParticipant(Base):
    """
    Game session participant with support for placeholders.

    When userId is NULL, displayName must be set (placeholder entry).
    When userId is set, displayName should be NULL (resolved at render).
    """

    __tablename__ = "game_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    game_session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(default=utc_now, server_default=func.now())
    position_type: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("24000")
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))

    # Relationships
    game: Mapped["GameSession"] = relationship("GameSession", back_populates="participants")
    user: Mapped["User | None"] = relationship("User", back_populates="participations")

    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND display_name IS NULL) OR "
            "(user_id IS NULL AND display_name IS NOT NULL)",
            name="participant_identity_check",
        ),
        UniqueConstraint(
            "game_session_id",
            "user_id",
            name="unique_game_participant",
        ),
    )

    def __repr__(self) -> str:
        identity = f"user_id={self.user_id}" if self.user_id else f"placeholder={self.display_name}"
        return f"<GameParticipant(id={self.id}, {identity})>"

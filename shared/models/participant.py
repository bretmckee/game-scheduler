"""Game participant model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .user import User


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
    joined_at: Mapped[datetime] = mapped_column(default=utc_now)
    pre_filled_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

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

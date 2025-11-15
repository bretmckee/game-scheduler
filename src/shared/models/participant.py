"""
Game participant model.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ParticipantStatus(Enum):
    """Participant status enumeration"""
    JOINED = "JOINED"
    DROPPED = "DROPPED"
    WAITLIST = "WAITLIST"
    PLACEHOLDER = "PLACEHOLDER"


class GameParticipant(Base):
    """
    Game participant model.
    
    Represents a participant in a game session. Supports both Discord users and placeholder entries.
    For Discord users: user_id is set, display_name is None (resolved at render time)
    For placeholders: user_id is None, display_name is set with placeholder text
    """
    __tablename__ = "game_participants"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Foreign keys
    game_session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Nullable for placeholder entries
    user_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Only used for placeholder entries - Discord users have display names resolved at render time
    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # When the participant joined
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    # Participant status
    status: Mapped[ParticipantStatus] = mapped_column(
        SQLEnum(ParticipantStatus),
        nullable=False,
        default=ParticipantStatus.JOINED,
        index=True
    )

    # Whether this participant was pre-populated at game creation
    is_pre_populated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Relationships
    game: Mapped["GameSession"] = relationship(
        "GameSession",
        back_populates="participants"
    )

    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="participations"
    )

    # Database constraints
    __table_args__ = (
        # Ensure either user_id or display_name is set, but not both
        CheckConstraint(
            "(user_id IS NOT NULL AND display_name IS NULL) OR (user_id IS NULL AND display_name IS NOT NULL)",
            name="user_or_placeholder_constraint"
        ),
        # Ensure placeholder status matches null user_id
        CheckConstraint(
            "(status = 'PLACEHOLDER' AND user_id IS NULL) OR (status != 'PLACEHOLDER' AND user_id IS NOT NULL)",
            name="placeholder_status_constraint"
        ),
    )

    def __repr__(self) -> str:
        if self.user_id:
            return f"<GameParticipant(id={self.id}, user_id={self.user_id}, status={self.status.value})>"
        else:
            return f"<GameParticipant(id={self.id}, placeholder={self.display_name}, status={self.status.value})>"

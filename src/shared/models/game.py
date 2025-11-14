"""
Game session model.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4
from enum import Enum
from sqlalchemy import String, DateTime, JSON, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class GameStatus(Enum):
    """Game session status enumeration"""
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GameSession(Base):
    """
    Game session model.
    
    Represents a scheduled game with participants and settings that inherit from channel/guild.
    """
    __tablename__ = "game_sessions"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Game details
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True
    )
    
    # Game scheduled time in UTC
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # Foreign keys
    guild_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guild_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    channel_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("channel_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    host_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Discord message ID for tracking posted announcements
    message_id: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )
    
    # Game-specific overrides (nullable to inherit from channel/guild)
    max_players: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    reminder_minutes: Mapped[Optional[List[int]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    rules: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True
    )
    
    # Game status
    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(GameStatus),
        nullable=False,
        default=GameStatus.SCHEDULED,
        index=True
    )
    
    # Timestamps in UTC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship(
        "GuildConfiguration",
        back_populates="games"
    )
    
    channel: Mapped["ChannelConfiguration"] = relationship(
        "ChannelConfiguration",
        back_populates="games"
    )
    
    host: Mapped["User"] = relationship(
        "User",
        back_populates="hosted_games",
        foreign_keys=[host_id]
    )
    
    participants: Mapped[List["GameParticipant"]] = relationship(
        "GameParticipant",
        back_populates="game",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<GameSession(id={self.id}, title={self.title}, scheduled_at={self.scheduled_at})>"
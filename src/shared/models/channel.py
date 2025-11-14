"""
Channel configuration model.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import String, DateTime, JSON, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class ChannelConfiguration(Base):
    """
    Discord channel configuration.
    
    Channel-specific settings that can override guild defaults.
    """
    __tablename__ = "channel_configurations"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # Foreign key to guild
    guild_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("guild_configurations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Discord channel ID - unique identifier
    channel_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )
    
    # Channel name for display purposes
    channel_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    # Channel active status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # Override settings (nullable to inherit from guild)
    max_players: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    
    # Override reminder times
    reminder_minutes: Mapped[Optional[List[int]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Override default rules
    default_rules: Mapped[Optional[str]] = mapped_column(
        String(2000),
        nullable=True
    )
    
    # Override allowed host roles
    allowed_host_role_ids: Mapped[Optional[List[str]]] = mapped_column(
        JSON,
        nullable=True
    )
    
    # Game category for this channel
    game_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True
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
        back_populates="channels"
    )
    
    games: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="channel"
    )
    
    def __repr__(self) -> str:
        return f"<ChannelConfiguration(id={self.id}, channel_id={self.channel_id}, name={self.channel_name})>"
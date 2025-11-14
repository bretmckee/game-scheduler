"""
User model for Discord users.
"""

from datetime import datetime, timezone
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import String, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from .base import Base


class User(Base):
    """
    Discord user model.
    
    Stores only essential user data with discordId as primary identifier.
    Never stores display names, usernames, or avatars - these are resolved at render time.
    """
    __tablename__ = "users"
    
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Discord snowflake ID - permanent identifier
    discord_id: Mapped[str] = mapped_column(
        String(20), 
        unique=True, 
        nullable=False,
        index=True
    )
    
    # User notification preferences
    notification_preferences: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        default=None
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
    hosted_games: Mapped[List["GameSession"]] = relationship(
        "GameSession",
        back_populates="host",
        foreign_keys="GameSession.host_id"
    )
    
    participations: Mapped[List["GameParticipant"]] = relationship(
        "GameParticipant",
        back_populates="user"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, discord_id={self.discord_id})>"
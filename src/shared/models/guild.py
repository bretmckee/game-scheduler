"""
Guild configuration model.
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class GuildConfiguration(Base):
    """
    Discord guild (server) configuration.
    
    Stores guild-level defaults that are inherited by channels and games.
    """
    __tablename__ = "guild_configurations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # Discord guild ID - unique identifier
    guild_id: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True
    )

    # Guild name for display purposes
    guild_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    # Default settings inherited by channels and games
    default_max_players: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=10
    )

    # Default reminder times in minutes before game start
    default_reminder_minutes: Mapped[list[int] | None] = mapped_column(
        JSON,
        nullable=True,
        default=lambda: [60, 15]  # 1 hour and 15 minutes
    )

    # Default game rules/guidelines
    default_rules: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True
    )

    # Discord role IDs that can create games
    allowed_host_role_ids: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True
    )

    # Whether host role is required to create games
    require_host_role: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    # Timestamps in UTC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    channels: Mapped[list["ChannelConfiguration"]] = relationship(
        "ChannelConfiguration",
        back_populates="guild",
        cascade="all, delete-orphan"
    )

    games: Mapped[list["GameSession"]] = relationship(
        "GameSession",
        back_populates="guild"
    )

    def __repr__(self) -> str:
        return f"<GuildConfiguration(id={self.id}, guild_id={self.guild_id}, name={self.guild_name})>"

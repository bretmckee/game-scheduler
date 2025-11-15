"""Guild configuration model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .channel import ChannelConfiguration
    from .game import GameSession


class GuildConfiguration(Base):
    """
    Discord guild (server) configuration with default settings.

    Settings cascade to channels and games via inheritance hierarchy.
    """

    __tablename__ = "guild_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    guild_name: Mapped[str] = mapped_column(String(100))
    default_max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_reminder_minutes: Mapped[list[int]] = mapped_column(JSON, default=lambda: [60, 15])
    default_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_host_role_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    require_host_role: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    channels: Mapped[list["ChannelConfiguration"]] = relationship(
        "ChannelConfiguration", back_populates="guild"
    )
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="guild")

    def __repr__(self) -> str:
        return f"<GuildConfiguration(id={self.id}, guild_name={self.guild_name})>"

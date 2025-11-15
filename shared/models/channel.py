"""Channel configuration model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from .game import GameSession
    from .guild import GuildConfiguration


class ChannelConfiguration(Base):
    """
    Discord channel configuration with optional overrides.

    Settings override guild defaults and cascade to games.
    """

    __tablename__ = "channel_configurations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    guild_id: Mapped[str] = mapped_column(ForeignKey("guild_configurations.id"))
    channel_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    channel_name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    default_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_host_role_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    game_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    # Relationships
    guild: Mapped["GuildConfiguration"] = relationship(
        "GuildConfiguration", back_populates="channels"
    )
    games: Mapped[list["GameSession"]] = relationship("GameSession", back_populates="channel")

    def __repr__(self) -> str:
        return f"<ChannelConfiguration(id={self.id}, channel_name={self.channel_name})>"

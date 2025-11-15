"""Event schema definitions for inter-service communication."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Standard event types for the game scheduling system."""

    # Game events
    GAME_CREATED = "game.created"
    GAME_UPDATED = "game.updated"
    GAME_CANCELLED = "game.cancelled"
    GAME_STARTED = "game.started"
    GAME_COMPLETED = "game.completed"

    # Participant events
    PLAYER_JOINED = "game.player_joined"
    PLAYER_LEFT = "game.player_left"
    WAITLIST_ADDED = "game.waitlist_added"
    WAITLIST_PROMOTED = "game.waitlist_promoted"

    # Notification events
    NOTIFICATION_SEND_DM = "notification.send_dm"
    NOTIFICATION_SENT = "notification.sent"
    NOTIFICATION_FAILED = "notification.failed"

    # Discord events
    DISCORD_MESSAGE_POST = "discord.message_post"
    DISCORD_MESSAGE_UPDATE = "discord.message_update"
    DISCORD_INTERACTION = "discord.interaction"

    # Configuration events
    GUILD_CONFIG_UPDATED = "guild.config_updated"
    CHANNEL_CONFIG_UPDATED = "channel.config_updated"


class BaseEvent(BaseModel):
    """Base event structure for all system events."""

    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    source_service: str | None = None
    data: dict[str, Any]

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            UUID: str
        }


class GameEventData(BaseModel):
    """Data structure for game-related events."""

    game_id: UUID
    title: str
    guild_id: str
    channel_id: str
    host_id: str
    scheduled_at: datetime
    scheduled_at_unix: int
    max_players: int | None = None
    current_players: int = 0
    status: str = "SCHEDULED"


class PlayerEventData(BaseModel):
    """Data structure for player participation events."""

    game_id: UUID
    player_id: str  # Discord user ID
    game_title: str
    guild_id: str
    channel_id: str
    current_players: int
    max_players: int | None = None
    is_waitlist: bool = False


class NotificationEventData(BaseModel):
    """Data structure for notification events."""

    user_id: str  # Discord user ID
    game_id: UUID
    game_title: str
    game_time_unix: int
    notification_type: str  # e.g., "1_hour_before", "15_minutes_before"
    channel_name: str | None = None
    guild_name: str | None = None


class DiscordMessageEventData(BaseModel):
    """Data structure for Discord message events."""

    game_id: UUID
    channel_id: str
    message_content: str
    embed_data: dict[str, Any] | None = None
    buttons: list[dict[str, Any]] | None = None
    message_id: str | None = None  # For updates


class DiscordInteractionEventData(BaseModel):
    """Data structure for Discord interaction events."""

    interaction_id: str
    user_id: str
    guild_id: str
    channel_id: str
    custom_id: str
    interaction_type: str  # "button", "select_menu", "slash_command"
    game_id: UUID | None = None


class ConfigUpdateEventData(BaseModel):
    """Data structure for configuration update events."""

    guild_id: str
    channel_id: str | None = None  # None for guild-level updates
    updated_by: str  # Discord user ID
    settings: dict[str, Any]
    previous_settings: dict[str, Any] | None = None


# Event factory functions for common events

def create_game_created_event(
    game_id: UUID,
    title: str,
    guild_id: str,
    channel_id: str,
    host_id: str,
    scheduled_at: datetime,
    max_players: int | None = None,
    source_service: str = "api"
) -> BaseEvent:
    """Create a game.created event."""
    return BaseEvent(
        event_type=EventType.GAME_CREATED,
        source_service=source_service,
        data=GameEventData(
            game_id=game_id,
            title=title,
            guild_id=guild_id,
            channel_id=channel_id,
            host_id=host_id,
            scheduled_at=scheduled_at,
            scheduled_at_unix=int(scheduled_at.timestamp()),
            max_players=max_players,
            current_players=1  # Host is first participant
        ).dict()
    )


def create_player_joined_event(
    game_id: UUID,
    player_id: str,
    game_title: str,
    guild_id: str,
    channel_id: str,
    current_players: int,
    max_players: int | None = None,
    source_service: str = "bot"
) -> BaseEvent:
    """Create a game.player_joined event."""
    return BaseEvent(
        event_type=EventType.PLAYER_JOINED,
        source_service=source_service,
        data=PlayerEventData(
            game_id=game_id,
            player_id=player_id,
            game_title=game_title,
            guild_id=guild_id,
            channel_id=channel_id,
            current_players=current_players,
            max_players=max_players,
            is_waitlist=False
        ).dict()
    )


def create_notification_event(
    user_id: str,
    game_id: UUID,
    game_title: str,
    game_time_unix: int,
    notification_type: str,
    channel_name: str | None = None,
    guild_name: str | None = None,
    source_service: str = "scheduler"
) -> BaseEvent:
    """Create a notification.send_dm event."""
    return BaseEvent(
        event_type=EventType.NOTIFICATION_SEND_DM,
        source_service=source_service,
        data=NotificationEventData(
            user_id=user_id,
            game_id=game_id,
            game_title=game_title,
            game_time_unix=game_time_unix,
            notification_type=notification_type,
            channel_name=channel_name,
            guild_name=guild_name
        ).dict()
    )


def create_discord_message_event(
    game_id: UUID,
    channel_id: str,
    message_content: str,
    embed_data: dict[str, Any] | None = None,
    buttons: list[dict[str, Any]] | None = None,
    message_id: str | None = None,
    source_service: str = "api"
) -> BaseEvent:
    """Create a discord.message_post or discord.message_update event."""
    event_type = EventType.DISCORD_MESSAGE_UPDATE if message_id else EventType.DISCORD_MESSAGE_POST

    return BaseEvent(
        event_type=event_type,
        source_service=source_service,
        data=DiscordMessageEventData(
            game_id=game_id,
            channel_id=channel_id,
            message_content=message_content,
            embed_data=embed_data,
            buttons=buttons,
            message_id=message_id
        ).dict()
    )


# Routing key helpers

def get_routing_key(event_type: EventType, guild_id: str | None = None) -> str:
    """Generate routing key for event based on type and guild."""
    base_key = event_type.value

    if guild_id:
        return f"{base_key}.{guild_id}"

    return base_key


def get_queue_name(service_name: str, event_type: EventType | None = None) -> str:
    """Generate standardized queue name for service and event type."""
    if event_type:
        return f"{service_name}.{event_type.value}"

    return f"{service_name}.events"

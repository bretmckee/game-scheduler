"""Shared messaging package for RabbitMQ communication."""

from .config import RabbitMQConfig, RabbitMQConnection, close_connection, get_connection
from .consumer import (
    EventConsumer,
    ServiceEventConsumer,
    event_handler,
    get_consumer,
    register_handlers,
    start_consumer,
    stop_all_consumers,
)
from .events import (
    BaseEvent,
    ConfigUpdateEventData,
    DiscordInteractionEventData,
    DiscordMessageEventData,
    EventType,
    GameEventData,
    NotificationEventData,
    PlayerEventData,
    create_discord_message_event,
    create_game_created_event,
    create_notification_event,
    create_player_joined_event,
    get_queue_name,
    get_routing_key,
)
from .publisher import EventPublisher, get_publisher, publish_dict, publish_event

__all__ = [
    # Configuration
    "RabbitMQConfig",
    "RabbitMQConnection",
    "get_connection",
    "close_connection",

    # Events
    "EventType",
    "BaseEvent",
    "GameEventData",
    "PlayerEventData",
    "NotificationEventData",
    "DiscordMessageEventData",
    "DiscordInteractionEventData",
    "ConfigUpdateEventData",
    "create_game_created_event",
    "create_player_joined_event",
    "create_notification_event",
    "create_discord_message_event",
    "get_routing_key",
    "get_queue_name",

    # Publisher
    "EventPublisher",
    "get_publisher",
    "publish_event",
    "publish_dict",

    # Consumer
    "EventConsumer",
    "ServiceEventConsumer",
    "event_handler",
    "register_handlers",
    "get_consumer",
    "start_consumer",
    "stop_all_consumers"
]

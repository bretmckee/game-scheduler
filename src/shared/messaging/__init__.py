"""Shared messaging package for RabbitMQ communication."""

from .config import RabbitMQConfig, RabbitMQConnection, get_connection, close_connection
from .events import (
    EventType,
    BaseEvent,
    GameEventData,
    PlayerEventData,
    NotificationEventData,
    DiscordMessageEventData,
    DiscordInteractionEventData,
    ConfigUpdateEventData,
    create_game_created_event,
    create_player_joined_event,
    create_notification_event,
    create_discord_message_event,
    get_routing_key,
    get_queue_name
)
from .publisher import EventPublisher, get_publisher, publish_event, publish_dict
from .consumer import (
    EventConsumer,
    ServiceEventConsumer,
    event_handler,
    register_handlers,
    get_consumer,
    start_consumer,
    stop_all_consumers
)

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
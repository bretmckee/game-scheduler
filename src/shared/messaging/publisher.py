"""Event publisher for sending messages to RabbitMQ."""

import json
import logging
from typing import Optional
from uuid import uuid4

import aio_pika
from aio_pika import Message, DeliveryMode

from .config import get_connection, RabbitMQConnection
from .events import BaseEvent, EventType, get_routing_key

logger = logging.getLogger(__name__)


class EventPublisher:
    """Publishes events to RabbitMQ exchange."""
    
    def __init__(self, connection: Optional[RabbitMQConnection] = None):
        self._connection = connection
    
    async def _get_connection(self) -> RabbitMQConnection:
        """Get or create RabbitMQ connection."""
        if self._connection is None:
            self._connection = await get_connection()
        return self._connection
    
    async def publish_event(
        self,
        event: BaseEvent,
        guild_id: Optional[str] = None,
        persistent: bool = True
    ) -> bool:
        """
        Publish an event to the exchange.
        
        Args:
            event: The event to publish
            guild_id: Optional guild ID for routing
            persistent: Whether message should survive broker restart
            
        Returns:
            True if published successfully, False otherwise
        """
        try:
            connection = await self._get_connection()
            
            # Generate correlation ID if not provided
            if not event.correlation_id:
                event.correlation_id = str(uuid4())
            
            # Serialize event
            message_body = event.json().encode('utf-8')
            
            # Create message with proper delivery mode
            delivery_mode = DeliveryMode.PERSISTENT if persistent else DeliveryMode.NOT_PERSISTENT
            
            message = Message(
                message_body,
                delivery_mode=delivery_mode,
                correlation_id=event.correlation_id,
                message_id=str(uuid4()),
                timestamp=event.timestamp,
                headers={
                    'event_type': event.event_type.value,
                    'source_service': event.source_service or 'unknown',
                    'guild_id': guild_id
                }
            )
            
            # Determine routing key
            routing_key = get_routing_key(event.event_type, guild_id)
            
            # Publish to exchange
            await connection.exchange.publish(
                message,
                routing_key=routing_key
            )
            
            logger.debug(
                f"Published event {event.event_type.value} "
                f"with routing key '{routing_key}' "
                f"(correlation_id: {event.correlation_id})"
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to publish event {event.event_type.value}: {e}",
                exc_info=True
            )
            return False
    
    async def publish_dict(
        self,
        event_type: EventType,
        data: dict,
        guild_id: Optional[str] = None,
        source_service: Optional[str] = None,
        correlation_id: Optional[str] = None,
        persistent: bool = True
    ) -> bool:
        """
        Publish an event from dictionary data.
        
        Args:
            event_type: Type of event
            data: Event data dictionary
            guild_id: Optional guild ID for routing
            source_service: Service that generated the event
            correlation_id: Optional correlation ID for tracking
            persistent: Whether message should survive broker restart
            
        Returns:
            True if published successfully, False otherwise
        """
        event = BaseEvent(
            event_type=event_type,
            data=data,
            source_service=source_service,
            correlation_id=correlation_id
        )
        
        return await self.publish_event(event, guild_id, persistent)
    
    async def publish_game_created(
        self,
        game_id: str,
        title: str,
        guild_id: str,
        channel_id: str,
        host_id: str,
        scheduled_at_unix: int,
        max_players: Optional[int] = None,
        source_service: str = "api"
    ) -> bool:
        """Convenience method to publish game.created event."""
        return await self.publish_dict(
            event_type=EventType.GAME_CREATED,
            data={
                'game_id': game_id,
                'title': title,
                'guild_id': guild_id,
                'channel_id': channel_id,
                'host_id': host_id,
                'scheduled_at_unix': scheduled_at_unix,
                'max_players': max_players,
                'current_players': 1
            },
            guild_id=guild_id,
            source_service=source_service
        )
    
    async def publish_player_joined(
        self,
        game_id: str,
        player_id: str,
        game_title: str,
        guild_id: str,
        channel_id: str,
        current_players: int,
        max_players: Optional[int] = None,
        source_service: str = "bot"
    ) -> bool:
        """Convenience method to publish game.player_joined event."""
        return await self.publish_dict(
            event_type=EventType.PLAYER_JOINED,
            data={
                'game_id': game_id,
                'player_id': player_id,
                'game_title': game_title,
                'guild_id': guild_id,
                'channel_id': channel_id,
                'current_players': current_players,
                'max_players': max_players,
                'is_waitlist': False
            },
            guild_id=guild_id,
            source_service=source_service
        )
    
    async def publish_notification_request(
        self,
        user_id: str,
        game_id: str,
        game_title: str,
        game_time_unix: int,
        notification_type: str,
        channel_name: Optional[str] = None,
        guild_name: Optional[str] = None,
        source_service: str = "scheduler"
    ) -> bool:
        """Convenience method to publish notification.send_dm event."""
        return await self.publish_dict(
            event_type=EventType.NOTIFICATION_SEND_DM,
            data={
                'user_id': user_id,
                'game_id': game_id,
                'game_title': game_title,
                'game_time_unix': game_time_unix,
                'notification_type': notification_type,
                'channel_name': channel_name,
                'guild_name': guild_name
            },
            source_service=source_service
        )


# Global publisher instance
_publisher: Optional[EventPublisher] = None


async def get_publisher() -> EventPublisher:
    """Get or create global event publisher."""
    global _publisher
    if _publisher is None:
        _publisher = EventPublisher()
    return _publisher


async def publish_event(
    event: BaseEvent,
    guild_id: Optional[str] = None,
    persistent: bool = True
) -> bool:
    """Convenience function to publish an event."""
    publisher = await get_publisher()
    return await publisher.publish_event(event, guild_id, persistent)


async def publish_dict(
    event_type: EventType,
    data: dict,
    guild_id: Optional[str] = None,
    source_service: Optional[str] = None,
    correlation_id: Optional[str] = None,
    persistent: bool = True
) -> bool:
    """Convenience function to publish event from dictionary."""
    publisher = await get_publisher()
    return await publisher.publish_dict(
        event_type, data, guild_id, source_service, correlation_id, persistent
    )
"""Event consumer framework for receiving messages from RabbitMQ."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Any
from uuid import uuid4

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from .config import get_connection, RabbitMQConnection
from .events import BaseEvent, EventType

logger = logging.getLogger(__name__)

EventHandler = Callable[[BaseEvent], Any]


class EventConsumer:
    """Base event consumer for processing RabbitMQ messages."""
    
    def __init__(
        self,
        service_name: str,
        connection: Optional[RabbitMQConnection] = None
    ):
        self.service_name = service_name
        self._connection = connection
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def _get_connection(self) -> RabbitMQConnection:
        """Get or create RabbitMQ connection."""
        if self._connection is None:
            self._connection = await get_connection()
        return self._connection
    
    def add_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value} in {self.service_name}")
    
    def remove_handler(self, event_type: EventType, handler: EventHandler) -> None:
        """Remove a handler for specific event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
                logger.info(f"Removed handler for {event_type.value} in {self.service_name}")
            except ValueError:
                pass
    
    async def _process_message(self, message: AbstractIncomingMessage) -> None:
        """Process incoming RabbitMQ message."""
        try:
            # Parse message body as JSON
            event_data = json.loads(message.body.decode('utf-8'))
            event = BaseEvent.parse_obj(event_data)
            
            logger.debug(
                f"Received event {event.event_type.value} "
                f"(correlation_id: {event.correlation_id})"
            )
            
            # Find handlers for this event type
            handlers = self._handlers.get(event.event_type, [])
            
            if not handlers:
                logger.warning(
                    f"No handlers registered for event type {event.event_type.value} "
                    f"in service {self.service_name}"
                )
                await message.ack()
                return
            
            # Process event with all registered handlers
            for handler in handlers:
                try:
                    result = handler(event)
                    if asyncio.iscoroutine(result):
                        await result
                    
                    logger.debug(
                        f"Successfully processed {event.event_type.value} "
                        f"with handler {handler.__name__}"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Handler {handler.__name__} failed for event "
                        f"{event.event_type.value}: {e}",
                        exc_info=True
                    )
                    # Continue with other handlers even if one fails
            
            # Acknowledge message after successful processing
            await message.ack()
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            await message.nack(requeue=False)  # Don't requeue invalid messages
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await message.nack(requeue=True)  # Requeue for retry
    
    async def start_consuming(
        self,
        queue_patterns: List[str],
        prefetch_count: int = 10
    ) -> None:
        """
        Start consuming events from specified queue patterns.
        
        Args:
            queue_patterns: List of routing key patterns to consume
            prefetch_count: Number of messages to prefetch
        """
        if self._running:
            logger.warning(f"Consumer {self.service_name} is already running")
            return
        
        try:
            connection = await self._get_connection()
            
            # Set QoS for fair dispatch
            await connection.channel.set_qos(prefetch_count=prefetch_count)
            
            # Declare and bind queues for each pattern
            for pattern in queue_patterns:
                queue_name = f"{self.service_name}.{pattern}"
                
                # Declare queue with dead letter exchange for failed messages
                queue = await connection.declare_queue(
                    queue_name,
                    pattern,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": f"{connection.config.exchange_name}.dlx",
                        "x-dead-letter-routing-key": f"dead.{pattern}"
                    }
                )
                
                # Start consuming from queue
                async def message_callback(message: AbstractIncomingMessage) -> None:
                    await self._process_message(message)
                
                await queue.consume(message_callback)
                logger.info(f"Started consuming from queue '{queue_name}' with pattern '{pattern}'")
            
            self._running = True
            logger.info(f"Event consumer {self.service_name} started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start consumer {self.service_name}: {e}")
            raise
    
    async def stop_consuming(self) -> None:
        """Stop consuming events and clean up resources."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel all running tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks.clear()
        logger.info(f"Event consumer {self.service_name} stopped")
    
    async def health_check(self) -> bool:
        """Check consumer health."""
        try:
            if not self._running:
                return False
            
            connection = await self._get_connection()
            return await connection.health_check()
            
        except Exception as e:
            logger.warning(f"Consumer health check failed: {e}")
            return False


class ServiceEventConsumer(EventConsumer):
    """Specialized consumer for service-specific event patterns."""
    
    def __init__(self, service_name: str, connection: Optional[RabbitMQConnection] = None):
        super().__init__(service_name, connection)
        self._setup_service_patterns()
    
    def _setup_service_patterns(self) -> None:
        """Setup default queue patterns based on service name."""
        # Each service gets its own queue patterns
        if self.service_name == "bot":
            self.queue_patterns = [
                "game.*",           # All game events
                "notification.*",   # All notification events
                "discord.*"         # All Discord events
            ]
        elif self.service_name == "api":
            self.queue_patterns = [
                "game.player_*",    # Player join/leave events
                "discord.interaction"  # Interaction events from bot
            ]
        elif self.service_name == "scheduler":
            self.queue_patterns = [
                "game.created",     # New games to schedule
                "game.updated",     # Game updates that might affect scheduling
                "game.cancelled"    # Cancelled games to unschedule
            ]
        else:
            # Default pattern for unknown services
            self.queue_patterns = ["*"]
    
    async def start(self) -> None:
        """Start consuming with service-specific patterns."""
        await self.start_consuming(self.queue_patterns)


# Decorator for event handlers

def event_handler(event_type: EventType):
    """Decorator to mark functions as event handlers."""
    def decorator(func: EventHandler) -> EventHandler:
        func._event_type = event_type
        func._is_event_handler = True
        return func
    return decorator


def register_handlers(consumer: EventConsumer, handler_module: Any) -> None:
    """Auto-register all decorated event handlers from a module."""
    for attr_name in dir(handler_module):
        attr = getattr(handler_module, attr_name)
        if callable(attr) and hasattr(attr, '_is_event_handler'):
            event_type = attr._event_type
            consumer.add_handler(event_type, attr)
            logger.info(f"Auto-registered handler {attr_name} for {event_type.value}")


# Global consumer instances
_consumers: Dict[str, EventConsumer] = {}


def get_consumer(service_name: str) -> EventConsumer:
    """Get or create consumer for service."""
    if service_name not in _consumers:
        _consumers[service_name] = ServiceEventConsumer(service_name)
    return _consumers[service_name]


async def start_consumer(service_name: str) -> EventConsumer:
    """Start consumer for service."""
    consumer = get_consumer(service_name)
    if isinstance(consumer, ServiceEventConsumer):
        await consumer.start()
    return consumer


async def stop_all_consumers() -> None:
    """Stop all running consumers."""
    for consumer in _consumers.values():
        await consumer.stop_consuming()
    _consumers.clear()
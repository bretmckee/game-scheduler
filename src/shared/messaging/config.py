"""RabbitMQ messaging configuration and connection management."""

import logging
from urllib.parse import urlparse

import aio_pika
from aio_pika import Queue
from aio_pika.abc import AbstractChannel, AbstractConnection, AbstractExchange

logger = logging.getLogger(__name__)


class RabbitMQConfig:
    """RabbitMQ connection configuration."""

    def __init__(
        self,
        url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "game_scheduler",
        exchange_type: str = "topic"
    ):
        self.url = url
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type

        # Parse connection details for logging
        parsed = urlparse(url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 5672
        self.username = parsed.username or "guest"


class RabbitMQConnection:
    """Manages RabbitMQ connection and channel lifecycle."""

    def __init__(self, config: RabbitMQConfig):
        self.config = config
        self._connection: AbstractConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to RabbitMQ."""
        if self._is_connected:
            return

        try:
            logger.info(f"Connecting to RabbitMQ at {self.config.host}:{self.config.port}")
            self._connection = await aio_pika.connect_robust(
                self.config.url,
                client_properties={"connection_name": "game-scheduler"}
            )

            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            # Declare main exchange
            self._exchange = await self._channel.declare_exchange(
                self.config.exchange_name,
                self.config.exchange_type,
                durable=True
            )

            self._is_connected = True
            logger.info("Successfully connected to RabbitMQ")

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """Close RabbitMQ connection."""
        self._is_connected = False

        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Disconnected from RabbitMQ")

        self._connection = None
        self._channel = None
        self._exchange = None

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        return self._is_connected and self._connection and not self._connection.is_closed

    @property
    def channel(self) -> AbstractChannel:
        """Get the current channel."""
        if not self._channel:
            raise RuntimeError("RabbitMQ channel not available. Call connect() first.")
        return self._channel

    @property
    def exchange(self) -> AbstractExchange:
        """Get the main exchange."""
        if not self._exchange:
            raise RuntimeError("RabbitMQ exchange not available. Call connect() first.")
        return self._exchange

    async def declare_queue(
        self,
        name: str,
        routing_key: str,
        durable: bool = True,
        arguments: dict | None = None
    ) -> Queue:
        """Declare a queue and bind it to the main exchange."""
        if not self.is_connected:
            await self.connect()

        queue = await self.channel.declare_queue(
            name,
            durable=durable,
            arguments=arguments or {}
        )

        await queue.bind(self.exchange, routing_key)
        logger.info(f"Declared queue '{name}' with routing key '{routing_key}'")

        return queue

    async def health_check(self) -> bool:
        """Check RabbitMQ connection health."""
        try:
            if not self.is_connected:
                return False

            # Try to declare a temporary queue to test connection
            temp_queue = await self.channel.declare_queue(
                exclusive=True,
                auto_delete=True
            )
            await temp_queue.delete()
            return True

        except Exception as e:
            logger.warning(f"RabbitMQ health check failed: {e}")
            return False


# Global connection instance
_connection: RabbitMQConnection | None = None


async def get_connection(config: RabbitMQConfig | None = None) -> RabbitMQConnection:
    """Get or create global RabbitMQ connection."""
    global _connection

    if _connection is None:
        if config is None:
            import os
            config = RabbitMQConfig(
                url=os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
            )
        _connection = RabbitMQConnection(config)

    if not _connection.is_connected:
        await _connection.connect()

    return _connection


async def close_connection() -> None:
    """Close global RabbitMQ connection."""
    global _connection
    if _connection:
        await _connection.disconnect()
        _connection = None

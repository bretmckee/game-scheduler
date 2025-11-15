"""
RabbitMQ connection configuration and management.

Provides async connection handling with automatic reconnection
and connection pooling for RabbitMQ.
"""

import asyncio
import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection

logger = logging.getLogger(__name__)


class RabbitMQConfig:
    """RabbitMQ connection configuration."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/",
        connection_timeout: int = 60,
        heartbeat: int = 60,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.connection_timeout = connection_timeout
        self.heartbeat = heartbeat

    @property
    def url(self) -> str:
        """Build RabbitMQ connection URL."""
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}{self.virtual_host}"


_connection: AbstractRobustConnection | None = None
_connection_lock = asyncio.Lock()


async def get_rabbitmq_connection(
    config: RabbitMQConfig | None = None,
) -> AbstractRobustConnection:
    """
    Get or create RabbitMQ connection with automatic reconnection.

    Args:
        config: RabbitMQ configuration. Uses defaults if not provided.

    Returns:
        Robust connection that automatically reconnects on failure.
    """
    global _connection

    async with _connection_lock:
        if _connection is None or _connection.is_closed:
            if config is None:
                config = RabbitMQConfig()

            logger.info(f"Connecting to RabbitMQ at {config.host}:{config.port}")

            _connection = await aio_pika.connect_robust(
                config.url,
                timeout=config.connection_timeout,
                heartbeat=config.heartbeat,
            )

            logger.info("Successfully connected to RabbitMQ")

        return _connection


async def close_rabbitmq_connection() -> None:
    """Close RabbitMQ connection gracefully."""
    global _connection

    if _connection and not _connection.is_closed:
        logger.info("Closing RabbitMQ connection")
        await _connection.close()
        _connection = None

"""Shared cache module for Redis operations across all services."""

from .client import RedisClient, get_redis_client, redis_client
from .keys import CacheKeys
from .ttl import (
    DISPLAY_NAME_TTL,
    GUILD_CONFIG_TTL,
    NOTIFICATION_TTL,
    OAUTH_TOKEN_TTL,
    TTL,
    USER_ROLES_TTL,
    CacheTier,
)

__all__ = [
    # Client
    "RedisClient",
    "get_redis_client",
    "redis_client",

    # Key patterns
    "CacheKeys",

    # TTL configuration
    "TTL",
    "CacheTier",
    "DISPLAY_NAME_TTL",
    "USER_ROLES_TTL",
    "GUILD_CONFIG_TTL",
    "OAUTH_TOKEN_TTL",
    "NOTIFICATION_TTL",
]

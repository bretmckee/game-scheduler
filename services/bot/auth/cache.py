"""Role caching wrapper for Redis storage."""

import json
import logging

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL

logger = logging.getLogger(__name__)


class RoleCache:
    """Cache wrapper for Discord role data with automatic expiration."""

    def __init__(self, redis_client: RedisClient):
        """
        Initialize role cache with Redis client.

        Args:
            redis_client: Initialized Redis client instance
        """
        self.redis = redis_client

    async def get_user_roles(self, user_id: str, guild_id: str) -> list[str] | None:
        """
        Get cached user role IDs for a guild.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            List of role IDs if cached, None if not found or expired
        """
        try:
            cache_key = CacheKeys.user_roles(user_id, guild_id)
            cached_data = await self.redis.get(cache_key)

            if cached_data is None:
                logger.debug(f"Role cache miss for user {user_id} in guild {guild_id}")
                return None

            role_ids = json.loads(cached_data)
            logger.debug(
                f"Role cache hit for user {user_id} in guild {guild_id}: {len(role_ids)} roles"
            )
            return role_ids

        except Exception as e:
            logger.error(f"Error getting cached roles: {e}")
            return None

    async def set_user_roles(self, user_id: str, guild_id: str, role_ids: list[str]) -> bool:
        """
        Cache user role IDs for a guild with TTL.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            role_ids: List of Discord role IDs

        Returns:
            True if successfully cached, False on error
        """
        try:
            cache_key = CacheKeys.user_roles(user_id, guild_id)
            cache_value = json.dumps(role_ids)

            await self.redis.set(cache_key, cache_value, ttl=CacheTTL.USER_ROLES)

            logger.debug(
                f"Cached {len(role_ids)} roles for user {user_id} in guild {guild_id} "
                f"(TTL: {CacheTTL.USER_ROLES}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error caching roles: {e}")
            return False

    async def invalidate_user_roles(self, user_id: str, guild_id: str) -> bool:
        """
        Invalidate cached role data for a user in a guild.

        Used when role changes are detected or critical operations require fresh data.

        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID

        Returns:
            True if successfully invalidated, False on error
        """
        try:
            cache_key = CacheKeys.user_roles(user_id, guild_id)
            await self.redis.delete(cache_key)

            logger.debug(f"Invalidated role cache for user {user_id} in guild {guild_id}")
            return True

        except Exception as e:
            logger.error(f"Error invalidating role cache: {e}")
            return False

    async def get_guild_roles(self, guild_id: str) -> dict | None:
        """
        Get cached guild role definitions.

        Args:
            guild_id: Discord guild ID

        Returns:
            Dictionary mapping role IDs to role data if cached, None otherwise
        """
        try:
            cache_key = CacheKeys.guild_config(guild_id)
            cached_data = await self.redis.get(cache_key)

            if cached_data is None:
                logger.debug(f"Guild roles cache miss for guild {guild_id}")
                return None

            roles = json.loads(cached_data)
            logger.debug(f"Guild roles cache hit for guild {guild_id}: {len(roles)} roles")
            return roles

        except Exception as e:
            logger.error(f"Error getting cached guild roles: {e}")
            return None

    async def set_guild_roles(self, guild_id: str, roles: dict) -> bool:
        """
        Cache guild role definitions with TTL.

        Args:
            guild_id: Discord guild ID
            roles: Dictionary mapping role IDs to role data

        Returns:
            True if successfully cached, False on error
        """
        try:
            cache_key = CacheKeys.guild_config(guild_id)
            cache_value = json.dumps(roles)

            await self.redis.set(cache_key, cache_value, ttl=CacheTTL.GUILD_CONFIG)

            logger.debug(
                f"Cached {len(roles)} guild roles for {guild_id} (TTL: {CacheTTL.GUILD_CONFIG}s)"
            )
            return True

        except Exception as e:
            logger.error(f"Error caching guild roles: {e}")
            return False


# Global role cache instance
_role_cache: RoleCache | None = None


async def get_role_cache() -> RoleCache:
    """
    Get global role cache instance.

    Returns:
        Singleton RoleCache instance
    """
    from shared.cache.client import get_redis_client

    global _role_cache
    if _role_cache is None:
        redis_client = await get_redis_client()
        _role_cache = RoleCache(redis_client)
    return _role_cache

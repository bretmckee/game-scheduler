"""Redis client wrapper with connection pooling and async support."""

import asyncio
import logging
from typing import Any, Optional, Union
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .keys import CacheKeys
from .ttl import TTL

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client wrapper with connection pooling."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """Initialize Redis client with connection pool.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        if self._client is not None:
            return
            
        try:
            # Parse Redis URL
            parsed = urlparse(self.redis_url)
            
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            await self._client.ping()
            logger.info(f"Connected to Redis at {parsed.hostname}:{parsed.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection pool."""
        if self._client:
            await self._client.close()
            self._client = None
            
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
            
        logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self._client:
            await self.connect()
            
        try:
            value = await self._client.get(key)
            return value.decode('utf-8') if value else None
        except Exception as e:
            logger.error(f"Redis GET failed for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None
    ) -> bool:
        """Set key-value pair with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            await self.connect()
            
        try:
            if ttl:
                result = await self._client.setex(key, ttl, value)
            else:
                result = await self._client.set(key, value)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis SET failed for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False otherwise
        """
        if not self._client:
            await self.connect()
            
        try:
            result = await self._client.delete(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis DELETE failed for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        if not self._client:
            await self.connect()
            
        try:
            result = await self._client.exists(key)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXISTS failed for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for existing key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            True if TTL was set, False otherwise
        """
        if not self._client:
            await self.connect()
            
        try:
            result = await self._client.expire(key, ttl)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis EXPIRE failed for key {key}: {e}")
            return False
    
    async def mget(self, keys: list[str]) -> list[Optional[str]]:
        """Get multiple values by keys.
        
        Args:
            keys: List of cache keys
            
        Returns:
            List of values (None for missing keys)
        """
        if not self._client:
            await self.connect()
            
        if not keys:
            return []
            
        try:
            values = await self._client.mget(keys)
            return [
                value.decode('utf-8') if value else None
                for value in values
            ]
        except Exception as e:
            logger.error(f"Redis MGET failed for keys {keys}: {e}")
            return [None] * len(keys)
    
    async def mset(self, mapping: dict[str, str]) -> bool:
        """Set multiple key-value pairs.
        
        Args:
            mapping: Dictionary of key-value pairs
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            await self.connect()
            
        if not mapping:
            return True
            
        try:
            result = await self._client.mset(mapping)
            return bool(result)
        except Exception as e:
            logger.error(f"Redis MSET failed: {e}")
            return False
    
    async def ping(self) -> bool:
        """Test Redis connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        if not self._client:
            try:
                await self.connect()
            except Exception:
                return False
                
        try:
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis PING failed: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    """Get Redis client instance (dependency injection helper).
    
    Returns:
        Configured Redis client
    """
    if not redis_client._client:
        await redis_client.connect()
    return redis_client
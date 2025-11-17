"""Tests for role caching functionality."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from services.bot.auth.cache import RoleCache, get_role_cache
from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def role_cache(mock_redis):
    """Create RoleCache instance with mock Redis."""
    return RoleCache(mock_redis)


class TestRoleCache:
    """Test suite for RoleCache."""

    @pytest.mark.asyncio
    async def test_get_user_roles_cache_miss(self, role_cache, mock_redis):
        """Test getting user roles when not cached."""
        mock_redis.get.return_value = None

        result = await role_cache.get_user_roles("123", "456")

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_roles_cache_hit(self, role_cache, mock_redis):
        """Test getting user roles when cached."""
        role_ids = ["111", "222", "333"]
        mock_redis.get.return_value = json.dumps(role_ids)

        result = await role_cache.get_user_roles("123", "456")

        assert result == role_ids
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_roles_handles_errors(self, role_cache, mock_redis):
        """Test error handling when getting cached roles."""
        mock_redis.get.side_effect = Exception("Redis error")

        result = await role_cache.get_user_roles("123", "456")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_user_roles_success(self, role_cache, mock_redis):
        """Test caching user roles successfully."""
        role_ids = ["111", "222", "333"]

        result = await role_cache.set_user_roles("123", "456", role_ids)

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert CacheKeys.user_roles("123", "456") in call_args[0]
        assert call_args[1]["ttl"] == CacheTTL.USER_ROLES

    @pytest.mark.asyncio
    async def test_set_user_roles_handles_errors(self, role_cache, mock_redis):
        """Test error handling when setting cached roles."""
        mock_redis.set.side_effect = Exception("Redis error")
        role_ids = ["111", "222"]

        result = await role_cache.set_user_roles("123", "456", role_ids)

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_user_roles_success(self, role_cache, mock_redis):
        """Test invalidating cached roles successfully."""
        result = await role_cache.invalidate_user_roles("123", "456")

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalidate_user_roles_handles_errors(self, role_cache, mock_redis):
        """Test error handling when invalidating roles."""
        mock_redis.delete.side_effect = Exception("Redis error")

        result = await role_cache.invalidate_user_roles("123", "456")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_guild_roles_cache_miss(self, role_cache, mock_redis):
        """Test getting guild roles when not cached."""
        mock_redis.get.return_value = None

        result = await role_cache.get_guild_roles("789")

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_guild_roles_cache_hit(self, role_cache, mock_redis):
        """Test getting guild roles when cached."""
        roles = {"111": {"name": "Admin"}, "222": {"name": "Member"}}
        mock_redis.get.return_value = json.dumps(roles)

        result = await role_cache.get_guild_roles("789")

        assert result == roles
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_guild_roles_success(self, role_cache, mock_redis):
        """Test caching guild roles successfully."""
        roles = {"111": {"name": "Admin"}}

        result = await role_cache.set_guild_roles("789", roles)

        assert result is True
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[1]["ttl"] == CacheTTL.GUILD_CONFIG


@pytest.mark.asyncio
async def test_get_role_cache_singleton():
    """Test that get_role_cache returns singleton instance."""
    with patch("shared.cache.client.get_redis_client") as mock_get_redis:
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        cache1 = await get_role_cache()
        cache2 = await get_role_cache()

        assert cache1 is cache2
        assert mock_get_redis.call_count == 1

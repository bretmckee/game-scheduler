# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for token management."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth.tokens import (
    decrypt_token,
    delete_user_tokens,
    encrypt_token,
    get_encryption_key,
    get_user_tokens,
    is_token_expired,
    refresh_user_tokens,
    store_user_tokens,
)


class TestTokenEncryption:
    """Test token encryption and decryption."""

    def test_encrypt_decrypt_token(self):
        """Test token encryption and decryption round trip."""
        original_token = "test_access_token_123"

        encrypted = encrypt_token(original_token)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original_token
        assert encrypted != original_token

    def test_encryption_key_generation(self):
        """Test encryption key is properly generated."""
        key = get_encryption_key()

        assert isinstance(key, bytes)
        assert len(key) == 44


class TestTokenStorage:
    """Test token storage and retrieval."""

    @pytest.mark.asyncio
    async def test_store_user_tokens(self):
        """Test storing user tokens in Redis."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            session_key = await store_user_tokens(
                user_id="123456789",
                access_token="test_access",
                refresh_token="test_refresh",
                expires_in=3600,
            )

            assert session_key == "session:123456789"
            mock_redis_instance.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_tokens_success(self):
        """Test retrieving user tokens from Redis."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
            encrypted_access = encrypt_token("test_access")
            encrypted_refresh = encrypt_token("test_refresh")

            mock_redis_instance.get_json.return_value = {
                "user_id": "123456789",
                "access_token": encrypted_access,
                "refresh_token": encrypted_refresh,
                "expires_at": expires_at.isoformat(),
            }

            result = await get_user_tokens("123456789")

            assert result is not None
            assert result["access_token"] == "test_access"
            assert result["refresh_token"] == "test_refresh"
            assert result["user_id"] == "123456789"

    @pytest.mark.asyncio
    async def test_get_user_tokens_not_found(self):
        """Test retrieving non-existent user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get_json.return_value = None

            result = await get_user_tokens("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_user_tokens(self):
        """Test refreshing user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            await refresh_user_tokens(
                user_id="123456789",
                new_access_token="new_access",
                new_refresh_token="new_refresh",
                expires_in=3600,
            )

            mock_redis_instance.set_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_tokens(self):
        """Test deleting user tokens."""
        with patch("services.api.auth.tokens.cache_client.get_redis_client") as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance

            await delete_user_tokens("123456789")

            mock_redis_instance.delete.assert_called_once_with("session:123456789")


class TestTokenExpiry:
    """Test token expiry checking."""

    @pytest.mark.asyncio
    async def test_is_token_expired_true(self):
        """Test expired token detection."""
        past_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)

        is_expired = await is_token_expired(past_time)

        assert is_expired is True

    @pytest.mark.asyncio
    async def test_is_token_expired_false(self):
        """Test valid token detection."""
        future_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

        is_expired = await is_token_expired(future_time)

        assert is_expired is False

    @pytest.mark.asyncio
    async def test_is_token_expired_buffer(self):
        """Test token expiry with 5-minute buffer."""
        almost_expired = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=3)

        is_expired = await is_token_expired(almost_expired)

        assert is_expired is True

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


"""
Token management for storing and retrieving OAuth2 tokens.

Uses Redis for session storage with encrypted token data.
"""

import base64
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.fernet import Fernet

from services.api import config
from shared.cache import client as cache_client
from shared.cache import ttl as cache_ttl

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from JWT secret.

    Returns:
        Fernet-compatible encryption key
    """
    api_config = config.get_api_config()
    key = api_config.jwt_secret.encode()
    if len(key) < 32:
        key = key.ljust(32, b"0")
    key = key[:32]
    return base64.urlsafe_b64encode(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt token for secure storage.

    Args:
        token: Plain text token

    Returns:
        Encrypted token string
    """
    fernet = Fernet(get_encryption_key())
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt token from storage.

    Args:
        encrypted_token: Encrypted token string

    Returns:
        Decrypted plain text token
    """
    fernet = Fernet(get_encryption_key())
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()


async def store_user_tokens(
    user_id: str, access_token: str, refresh_token: str, expires_in: int
) -> str:
    """
    Store user OAuth2 tokens in Redis session.

    Args:
        user_id: Discord user ID
        access_token: OAuth2 access token
        refresh_token: OAuth2 refresh token
        expires_in: Seconds until access token expires

    Returns:
        Session ID for retrieving tokens later
    """
    redis = await cache_client.get_redis_client()

    encrypted_access = encrypt_token(access_token)
    encrypted_refresh = encrypt_token(refresh_token)

    expiry = datetime.now(UTC).replace(tzinfo=None) + timedelta(seconds=expires_in)

    session_data = {
        "user_id": user_id,
        "access_token": encrypted_access,
        "refresh_token": encrypted_refresh,
        "expires_at": expiry.isoformat(),
    }

    session_key = f"session:{user_id}"
    await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)

    logger.info(f"Stored tokens for user {user_id}")
    return session_key


async def get_user_tokens(user_id: str) -> dict[str, Any] | None:
    """
    Retrieve user OAuth2 tokens from Redis session.

    Args:
        user_id: Discord user ID

    Returns:
        Token data with access_token, refresh_token, expires_at or None if not found
    """
    redis = await cache_client.get_redis_client()

    session_key = f"session:{user_id}"
    session_data = await redis.get_json(session_key)

    if session_data is None:
        logger.warning(f"No session found for user {user_id}")
        return None

    decrypted_access = decrypt_token(session_data["access_token"])
    decrypted_refresh = decrypt_token(session_data["refresh_token"])

    return {
        "user_id": session_data["user_id"],
        "access_token": decrypted_access,
        "refresh_token": decrypted_refresh,
        "expires_at": datetime.fromisoformat(session_data["expires_at"]),
    }


async def refresh_user_tokens(
    user_id: str, new_access_token: str, new_refresh_token: str, expires_in: int
) -> None:
    """
    Update stored tokens after refresh.

    Args:
        user_id: Discord user ID
        new_access_token: New OAuth2 access token
        new_refresh_token: New OAuth2 refresh token
        expires_in: Seconds until new access token expires
    """
    await store_user_tokens(user_id, new_access_token, new_refresh_token, expires_in)
    logger.info(f"Refreshed tokens for user {user_id}")


async def delete_user_tokens(user_id: str) -> None:
    """
    Delete user session and tokens.

    Args:
        user_id: Discord user ID
    """
    redis = await cache_client.get_redis_client()

    session_key = f"session:{user_id}"
    await redis.delete(session_key)

    logger.info(f"Deleted tokens for user {user_id}")


async def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if access token is expired or expiring soon.

    Args:
        expires_at: Token expiration datetime

    Returns:
        True if token is expired or expires within 5 minutes
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    buffer = timedelta(minutes=5)
    return now >= (expires_at - buffer)

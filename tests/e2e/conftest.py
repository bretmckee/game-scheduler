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
pytest configuration for E2E tests.

Provides fixtures for Discord credentials, database sessions,
and HTTP clients needed by E2E tests.
"""

import os
from collections.abc import Callable
from typing import Any, TypeVar

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.conftest import TimeoutType  # Re-export for backward compatibility
from tests.e2e.helpers.discord import DiscordTestHelper
from tests.shared.auth_helpers import cleanup_test_session, create_test_session
from tests.shared.polling import wait_for_db_condition_async

# Export TimeoutType so e2e tests can import it from here
__all__ = ["TimeoutType"]

T = TypeVar("T")


async def wait_for_db_condition(
    db_session: AsyncSession,
    query: str,
    params: dict,
    predicate: Callable[[Any], bool],
    timeout: int = 10,
    interval: float = 0.5,
    description: str = "database condition",
) -> Any:
    """
    Poll database query until predicate satisfied.

    This is a convenience wrapper around wait_for_db_condition_async from
    tests.shared.polling that maintains backward compatibility with existing
    e2e tests.

    Args:
        db_session: SQLAlchemy async session
        query: SQL query string
        params: Query parameters
        predicate: Function returning True when result matches expectation
        timeout: Maximum seconds to wait
        interval: Seconds between queries
        description: Human-readable description

    Returns:
        Query result when predicate satisfied

    Raises:
        AssertionError: If condition not met within timeout
    """
    return await wait_for_db_condition_async(
        db_session, query, params, predicate, timeout, interval, description
    )


async def wait_for_game_message_id(
    db_session: AsyncSession,
    game_id: str,
    timeout: int = 5,
) -> str:
    """
    Poll database until message_id is populated for a game session.

    Game announcement messages are posted asynchronously via RabbitMQ,
    so message_id may not be immediately available after game creation.

    Args:
        db_session: SQLAlchemy async session
        game_id: UUID of the game session
        timeout: Maximum seconds to wait (default: 5)

    Returns:
        Discord message_id string

    Raises:
        AssertionError: If message_id not populated within timeout

    Example:
        game_id = response.json()["id"]
        message_id = await wait_for_game_message_id(db_session, game_id)
    """
    row = await wait_for_db_condition(
        db_session,
        "SELECT message_id FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] is not None,
        timeout=timeout,
        interval=0.5,
        description=f"message_id population for game {game_id}",
    )
    return row[0]


@pytest.fixture(scope="session")
def discord_token():
    """Provide Discord admin bot token for E2E tests."""
    return os.environ["DISCORD_ADMIN_BOT_A_TOKEN"]


@pytest.fixture(scope="session")
def discord_main_bot_token():
    """Provide Discord main bot token (sends notifications)."""
    return os.environ["DISCORD_BOT_TOKEN"]


@pytest.fixture(scope="session")
def discord_guild_id():
    """Provide test Discord guild ID from environment."""
    return os.environ["DISCORD_GUILD_A_ID"]


@pytest.fixture(scope="session")
def discord_channel_id():
    """Provide test Discord channel ID from environment."""
    return os.environ["DISCORD_GUILD_A_CHANNEL_ID"]


@pytest.fixture(scope="session")
def discord_user_id():
    """Provide test Discord user ID from environment."""
    return os.environ["DISCORD_USER_ID"]


@pytest.fixture(scope="session")
def discord_guild_b_id():
    """Guild B for cross-guild isolation testing (required)."""
    guild_b_id = os.environ.get("DISCORD_GUILD_B_ID")
    if not guild_b_id:
        pytest.skip(
            "DISCORD_GUILD_B_ID environment variable not set. "
            "Guild B is required for cross-guild isolation testing. "
            "See TESTING_E2E.md section 6 for setup instructions."
        )
    return guild_b_id


@pytest.fixture(scope="session")
def discord_channel_b_id():
    """Channel in Guild B for isolation tests (required)."""
    channel_b_id = os.environ.get("DISCORD_GUILD_B_CHANNEL_ID")
    if not channel_b_id:
        pytest.skip(
            "DISCORD_GUILD_B_CHANNEL_ID environment variable not set. "
            "Guild B is required for cross-guild isolation testing. "
            "See TESTING_E2E.md section 6 for setup instructions."
        )
    return channel_b_id


@pytest.fixture(scope="session")
def discord_user_b_id():
    """User B (member of Guild B only, required)."""
    user_b_id = os.environ.get("DISCORD_ADMIN_BOT_B_CLIENT_ID")
    if not user_b_id:
        pytest.fail(
            "DISCORD_ADMIN_BOT_B_CLIENT_ID environment variable not set. "
            "Guild B is required for cross-guild isolation testing. "
            "See TESTING_E2E.md section 6 for setup instructions."
        )
    return user_b_id


@pytest.fixture(scope="session")
def discord_user_b_token():
    """Bot token for User B (Admin Bot B acting as authenticated user in Guild B)."""
    user_b_token = os.environ.get("DISCORD_ADMIN_BOT_B_TOKEN")
    if not user_b_token:
        pytest.fail(
            "DISCORD_ADMIN_BOT_B_TOKEN environment variable not set. "
            "Guild B is required for cross-guild isolation testing. "
            "See TESTING_E2E.md section 6 for setup instructions."
        )
    return user_b_token


@pytest.fixture
async def discord_helper(discord_token):
    """Create and connect Discord test helper."""

    helper = DiscordTestHelper(discord_token)
    await helper.connect()
    yield helper
    await helper.disconnect()


@pytest.fixture(scope="session")
def bot_discord_id(discord_token):
    """Extract bot Discord ID from token."""

    return extract_bot_discord_id(discord_token)


@pytest.fixture
async def authenticated_admin_client(api_base_url, bot_discord_id, discord_token):
    """HTTP client authenticated as admin bot."""

    client = httpx.AsyncClient(base_url=api_base_url, timeout=10.0)

    session_token, _ = await create_test_session(discord_token, bot_discord_id)
    client.cookies.set("session_token", session_token)

    yield client

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def synced_guild(authenticated_admin_client, discord_guild_id):
    """
    Sync guilds using the API endpoint and return sync results.

    Calls /api/v1/guilds/sync with the admin bot token.
    Returns the sync response containing new_guilds and new_channels counts.
    """
    print("\n[synced_guild fixture] Calling /api/v1/guilds/sync")
    print(f"[synced_guild fixture] Client: {authenticated_admin_client}")
    print(f"[synced_guild fixture] Cookies: {authenticated_admin_client.cookies}")

    response = await authenticated_admin_client.post("/api/v1/guilds/sync")

    print(f"[synced_guild fixture] Response status: {response.status_code}")
    print(f"[synced_guild fixture] Response text: {response.text[:200]}")

    assert response.status_code == 200, (
        f"Guild sync failed: {response.status_code} - {response.text}"
    )

    sync_results = response.json()
    print(f"[synced_guild fixture] Sync results: {sync_results}")
    return sync_results


@pytest.fixture
async def synced_guild_b(authenticated_client_b, discord_guild_b_id):
    """
    Sync Guild B using the API endpoint and return sync results.

    Calls /api/v1/guilds/sync with the User B token.
    Returns the sync response containing new_guilds and new_channels counts.
    """
    response = await authenticated_client_b.post("/api/v1/guilds/sync")

    assert response.status_code == 200, (
        f"Guild B sync failed: {response.status_code} - {response.text}"
    )

    return response.json()


@pytest.fixture
async def authenticated_client_b(api_base_url, discord_user_b_id, discord_user_b_token):
    """HTTP client authenticated as User B (Guild B member)."""

    client = httpx.AsyncClient(base_url=api_base_url, timeout=10.0)

    session_token, _ = await create_test_session(discord_user_b_token, discord_user_b_id)
    client.cookies.set("session_token", session_token)

    yield client

    await cleanup_test_session(session_token)
    await client.aclose()


@pytest.fixture
async def main_bot_helper(discord_main_bot_token):
    """Create Discord helper for main bot (sends notifications)."""
    helper = DiscordTestHelper(discord_main_bot_token)
    await helper.connect()
    yield helper
    await helper.disconnect()

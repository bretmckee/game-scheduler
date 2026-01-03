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


"""Tests for database dependency functions."""

from unittest.mock import AsyncMock, patch

import pytest

from shared.data_access.guild_isolation import get_current_guild_ids
from shared.database import get_db_with_user_guilds
from shared.schemas.auth import CurrentUser


@pytest.fixture
def mock_current_user():
    """Mock CurrentUser for dependency testing."""
    user_mock = AsyncMock()
    user_mock.discord_id = "123456789"
    user_mock.id = "user_uuid_123"

    return CurrentUser(
        user=user_mock,
        access_token="mock_access_token",
        session_token="mock_session_token",
    )


@pytest.fixture
def mock_user_guilds():
    """Mock user guilds from Discord API."""
    return [
        {"id": "guild_1", "name": "Test Guild 1"},
        {"id": "guild_2", "name": "Test Guild 2"},
    ]


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_sets_context(mock_current_user, mock_user_guilds):
    """Enhanced dependency sets guild_ids in ContextVar."""
    with patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        # Call the dependency with mock_current_user
        generator = dependency_func(mock_current_user)
        try:
            async for _session in generator:
                # Inside context, guild_ids should be set
                guild_ids = get_current_guild_ids()
                assert guild_ids == ["guild_1", "guild_2"]
                break  # Only need to test context setting
        finally:
            # Properly close generator
            await generator.aclose()


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exit(mock_current_user, mock_user_guilds):
    """Enhanced dependency clears ContextVar in finally block."""
    with patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        async for _session in dependency_func(mock_current_user):
            pass  # Consume generator

    # After generator exits, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None


@pytest.mark.asyncio
async def test_get_db_with_user_guilds_clears_context_on_exception(
    mock_current_user, mock_user_guilds
):
    """Enhanced dependency clears ContextVar even if exception raised."""
    with patch("services.api.auth.oauth2.get_user_guilds", return_value=mock_user_guilds):
        # Factory function returns the actual dependency
        dependency_func = get_db_with_user_guilds()
        generator = dependency_func(mock_current_user)
        try:
            with pytest.raises(RuntimeError):
                async for _session in generator:
                    raise RuntimeError("Simulated error")
        finally:
            # Properly close the generator to trigger finally block
            await generator.aclose()

    # Even after exception, guild_ids should be cleared
    guild_ids = get_current_guild_ids()
    assert guild_ids is None

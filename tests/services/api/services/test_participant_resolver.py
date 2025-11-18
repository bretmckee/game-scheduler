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


"""Unit tests for participant resolver service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.auth import discord_client as discord_client_module
from services.api.services import participant_resolver as resolver_module
from shared.models import user as user_model


def create_mock_http_response(status, json_data):
    """Helper to create properly mocked HTTP response with async context manager."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data)

    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)

    return mock_context_manager


@pytest.fixture
def mock_discord_client():
    """Create mock Discord API client."""
    client = MagicMock(spec=discord_client_module.DiscordAPIClient)
    client.bot_token = "test_bot_token"
    return client


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def resolver(mock_discord_client):
    """Create participant resolver instance."""
    return resolver_module.ParticipantResolver(mock_discord_client)


@pytest.mark.asyncio
async def test_resolve_placeholder_strings(resolver):
    """Test that placeholder strings (non-@mentions) are always valid."""
    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["Alice", "Bob", "Charlie"],
        access_token="token",
    )

    assert len(valid) == 3
    assert len(errors) == 0
    assert all(p["type"] == "placeholder" for p in valid)
    assert valid[0]["display_name"] == "Alice"
    assert valid[1]["display_name"] == "Bob"
    assert valid[2]["display_name"] == "Charlie"


@pytest.mark.asyncio
async def test_resolve_single_match(resolver, mock_discord_client):
    """Test @mention with single member match."""
    json_data = [
        {
            "user": {
                "id": "987654321",
                "username": "testuser",
                "global_name": "Test User",
            }
        }
    ]

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=create_mock_http_response(200, json_data))
    mock_discord_client._get_session = AsyncMock(return_value=mock_session)

    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["@testuser"],
        access_token="token",
    )

    assert len(valid) == 1
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "987654321"


@pytest.mark.asyncio
async def test_resolve_multiple_matches(resolver, mock_discord_client):
    """Test @mention with multiple member matches returns disambiguation."""
    json_data = [
        {
            "user": {"id": "111", "username": "alice1", "global_name": "Alice One"},
            "nick": None,
        },
        {
            "user": {"id": "222", "username": "alice2", "global_name": "Alice Two"},
            "nick": "Alice",
        },
    ]

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=create_mock_http_response(200, json_data))
    mock_discord_client._get_session = AsyncMock(return_value=mock_session)

    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["@alice"],
        access_token="token",
    )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@alice"
    assert errors[0]["reason"] == "Multiple matches found"
    assert len(errors[0]["suggestions"]) == 2
    assert errors[0]["suggestions"][0]["discordId"] == "111"
    assert errors[0]["suggestions"][1]["displayName"] == "Alice"


@pytest.mark.asyncio
async def test_resolve_no_match(resolver, mock_discord_client):
    """Test @mention with no member matches returns error."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=create_mock_http_response(200, []))
    mock_discord_client._get_session = AsyncMock(return_value=mock_session)

    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["@nonexistent"],
        access_token="token",
    )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@nonexistent"
    assert errors[0]["reason"] == "User not found in guild"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_mixed_participants(resolver, mock_discord_client):
    """Test resolving mix of @mentions and placeholders."""
    json_data = [
        {
            "user": {
                "id": "111",
                "username": "validuser",
                "global_name": "Valid User",
            }
        }
    ]

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=create_mock_http_response(200, json_data))
    mock_discord_client._get_session = AsyncMock(return_value=mock_session)

    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["@validuser", "PlaceholderName"],
        access_token="token",
    )

    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["type"] == "discord"
    assert valid[0]["discord_id"] == "111"
    assert valid[1]["type"] == "placeholder"
    assert valid[1]["display_name"] == "PlaceholderName"


@pytest.mark.asyncio
async def test_resolve_empty_input(resolver):
    """Test that empty strings are filtered out."""
    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["Alice", "", "  ", "Bob"],
        access_token="token",
    )

    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["display_name"] == "Alice"
    assert valid[1]["display_name"] == "Bob"


@pytest.mark.asyncio
async def test_ensure_user_exists_creates_new(resolver, mock_db):
    """Test ensure_user_exists creates new user if not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()

    user = await resolver.ensure_user_exists(mock_db, "999")

    assert isinstance(user, user_model.User)
    assert user.discord_id == "999"
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_user_exists_returns_existing(resolver, mock_db):
    """Test ensure_user_exists returns existing user."""
    existing_user = user_model.User(discord_id="888")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute = AsyncMock(return_value=mock_result)

    user = await resolver.ensure_user_exists(mock_db, "888")

    assert user is existing_user
    mock_db.add.assert_not_called()
    mock_db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_discord_api_error_handling(resolver, mock_discord_client):
    """Test handling of Discord API errors."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(
        return_value=create_mock_http_response(403, {"message": "Missing Access"})
    )
    mock_discord_client._get_session = AsyncMock(return_value=mock_session)

    valid, errors = await resolver.resolve_initial_participants(
        guild_discord_id="123456789",
        participant_inputs=["@testuser"],
        access_token="token",
    )

    assert len(valid) == 0
    assert len(errors) == 1
    assert errors[0]["input"] == "@testuser"
    assert "403" in errors[0]["reason"] or "Missing Access" in errors[0]["reason"]

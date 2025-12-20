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


"""Unit tests for display name resolution service."""

import json
from unittest.mock import AsyncMock

import pytest

from services.api.auth import discord_client
from services.api.services import display_names
from shared.cache import client as cache_client


@pytest.fixture
def mock_discord_api():
    """Mock Discord API client."""
    mock = AsyncMock(spec=discord_client.DiscordAPIClient)
    return mock


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    mock = AsyncMock(spec=cache_client.RedisClient)
    return mock


@pytest.fixture
def resolver(mock_discord_api, mock_cache):
    """Display name resolver with mocked dependencies."""
    return display_names.DisplayNameResolver(mock_discord_api, mock_cache)


@pytest.mark.asyncio
async def test_resolve_display_names_from_cache(resolver, mock_cache):
    """Test resolving display names from cache."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache hits
    mock_cache.get = AsyncMock(side_effect=["CachedName1", "CachedName2"])

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "CachedName1", "user2": "CachedName2"}
    assert mock_cache.get.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_from_api(resolver, mock_discord_api, mock_cache):
    """Test resolving display names from Discord API when not cached."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache misses
    mock_cache.get = AsyncMock(return_value=None)

    # Mock Discord API response
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            },
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": "GlobalName2",
                },
                "nick": None,
            },
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GuildNick1", "user2": "GlobalName2"}
    assert mock_cache.set.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_fallback_to_global_name(
    resolver, mock_discord_api, mock_cache
):
    """Test fallback to global_name when nick is not set."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": None,
            }
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GlobalName1"}


@pytest.mark.asyncio
async def test_resolve_display_names_fallback_to_username(resolver, mock_discord_api, mock_cache):
    """Test fallback to username when nick and global_name are not set."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {"id": "user1", "username": "username1", "global_name": None},
                "nick": None,
            }
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "username1"}


@pytest.mark.asyncio
async def test_resolve_display_names_user_not_found(resolver, mock_discord_api, mock_cache):
    """Test handling of users who left the guild."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    mock_cache.get = AsyncMock(return_value=None)
    # Only user1 is returned (user2 left guild)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                },
                "nick": "GuildNick1",
            }
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {"user1": "GuildNick1", "user2": "Unknown User"}


@pytest.mark.asyncio
async def test_resolve_display_names_api_error(resolver, mock_discord_api, mock_cache):
    """Test fallback on Discord API error."""
    guild_id = "123456789"
    user_ids = ["user1234"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        side_effect=discord_client.DiscordAPIError(500, "API Error")
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    # Should return fallback format: User#1234
    assert result == {"user1234": "User#1234"}


@pytest.mark.asyncio
async def test_resolve_display_names_mixed_cache_and_api(resolver, mock_discord_api, mock_cache):
    """Test resolving with some cached and some uncached names."""
    guild_id = "123456789"
    user_ids = ["user1", "user2", "user3"]

    # Mock cache: user1 cached, user2 and user3 not cached
    async def cache_get(key):
        if "user1" in key:
            return "CachedName1"
        return None

    mock_cache.get = AsyncMock(side_effect=cache_get)

    # Mock API response for uncached users
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user2",
                    "username": "username2",
                    "global_name": "GlobalName2",
                },
                "nick": None,
            },
            {
                "user": {"id": "user3", "username": "username3", "global_name": None},
                "nick": None,
            },
        ]
    )

    result = await resolver.resolve_display_names(guild_id, user_ids)

    assert result == {
        "user1": "CachedName1",
        "user2": "GlobalName2",
        "user3": "username3",
    }


@pytest.mark.asyncio
async def test_resolve_single(resolver, mock_cache):
    """Test resolving single user display name."""
    guild_id = "123456789"
    user_id = "user1"

    mock_cache.get = AsyncMock(return_value="CachedName1")

    result = await resolver.resolve_single(guild_id, user_id)

    assert result == "CachedName1"


@pytest.mark.asyncio
async def test_resolve_single_user_not_found(resolver, mock_discord_api, mock_cache):
    """Test resolving single user that doesn't exist."""
    guild_id = "123456789"
    user_id = "user1"

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(return_value=[])

    result = await resolver.resolve_single(guild_id, user_id)

    assert result == "Unknown User"


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_cache(resolver, mock_cache):
    """Test resolving display names and avatars from cache."""
    guild_id = "123456789"
    user_ids = ["user1", "user2"]

    # Mock cache hits with JSON data
    mock_cache.get = AsyncMock(
        side_effect=[
            json.dumps(
                {
                    "display_name": "CachedName1",
                    "avatar_url": "https://cdn.example.com/avatar1.png",
                }
            ),
            json.dumps({"display_name": "CachedName2", "avatar_url": None}),
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {
        "user1": {
            "display_name": "CachedName1",
            "avatar_url": "https://cdn.example.com/avatar1.png",
        },
        "user2": {"display_name": "CachedName2", "avatar_url": None},
    }
    assert mock_cache.get.call_count == 2


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_api_with_guild_avatar(
    resolver, mock_discord_api, mock_cache
):
    """Test resolving display names and avatars from Discord API with guild-specific avatar."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                    "avatar": "user_avatar_hash",
                },
                "nick": "GuildNick1",
                "avatar": "guild_avatar_hash",
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    # Guild avatar should take priority
    expected_url = "https://cdn.discordapp.com/guilds/123456789/users/user1/avatars/guild_avatar_hash.png?size=64"
    assert result == {"user1": {"display_name": "GuildNick1", "avatar_url": expected_url}}
    assert mock_cache.set.call_count == 1


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_from_api_with_user_avatar(
    resolver, mock_discord_api, mock_cache
):
    """Test resolving display names and avatars from Discord API with user avatar only."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": "GlobalName1",
                    "avatar": "user_avatar_hash",
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    # User avatar should be used when no guild avatar
    expected_url = "https://cdn.discordapp.com/avatars/user1/user_avatar_hash.png?size=64"
    assert result == {"user1": {"display_name": "GlobalName1", "avatar_url": expected_url}}


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_no_avatar(resolver, mock_discord_api, mock_cache):
    """Test resolving display names and avatars when user has no avatar."""
    guild_id = "123456789"
    user_ids = ["user1"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        return_value=[
            {
                "user": {
                    "id": "user1",
                    "username": "username1",
                    "global_name": None,
                    "avatar": None,
                },
                "nick": None,
                "avatar": None,
            }
        ]
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {"user1": {"display_name": "username1", "avatar_url": None}}


@pytest.mark.asyncio
async def test_resolve_display_names_and_avatars_api_error(resolver, mock_discord_api, mock_cache):
    """Test fallback on Discord API error for avatar resolution."""
    guild_id = "123456789"
    user_ids = ["user1234"]

    mock_cache.get = AsyncMock(return_value=None)
    mock_discord_api.get_guild_members_batch = AsyncMock(
        side_effect=discord_client.DiscordAPIError(500, "API Error")
    )

    result = await resolver.resolve_display_names_and_avatars(guild_id, user_ids)

    assert result == {"user1234": {"display_name": "User#1234", "avatar_url": None}}


@pytest.mark.asyncio
async def test_build_avatar_url_guild_priority(resolver):
    """Test avatar URL construction with guild avatar priority."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar="guild_hash",
        user_avatar="user_hash",
    )

    assert (
        url
        == "https://cdn.discordapp.com/guilds/guild456/users/user123/avatars/guild_hash.png?size=64"
    )


@pytest.mark.asyncio
async def test_build_avatar_url_user_fallback(resolver):
    """Test avatar URL construction with user avatar fallback."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar=None,
        user_avatar="user_hash",
    )

    assert url == "https://cdn.discordapp.com/avatars/user123/user_hash.png?size=64"


@pytest.mark.asyncio
async def test_build_avatar_url_no_avatar(resolver):
    """Test avatar URL construction with no avatar."""
    url = resolver._build_avatar_url(
        user_id="user123",
        guild_id="guild456",
        member_avatar=None,
        user_avatar=None,
    )

    assert url is None

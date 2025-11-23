"""Unit tests for role verification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.api.auth import discord_client, roles


@pytest.fixture
def role_service():
    """Create role verification service instance."""
    return roles.RoleVerificationService()


@pytest.fixture
def mock_cache():
    """Mock Redis cache client."""
    cache = AsyncMock()
    cache.get_json = AsyncMock()
    cache.set_json = AsyncMock()
    cache.delete = AsyncMock()
    return cache


@pytest.fixture
def mock_discord_client():
    """Mock Discord API client."""
    client = AsyncMock()
    client.get_guild_member = AsyncMock()
    client.get_user_guilds = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_get_user_role_ids_from_cache(role_service, mock_cache):
    """Test retrieving user roles from cache."""
    mock_cache.get_json.return_value = ["role1", "role2"]

    with patch.object(role_service, "_get_cache", return_value=mock_cache):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == ["role1", "role2"]
    mock_cache.get_json.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_from_api(role_service, mock_cache, mock_discord_client):
    """Test retrieving user roles from Discord API when not cached."""
    mock_cache.get_json.return_value = None
    mock_discord_client.get_guild_member.return_value = {"roles": ["role1", "role2", "role3"]}

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == ["role1", "role2", "role3"]
    mock_cache.get_json.assert_called_once()
    mock_discord_client.get_guild_member.assert_called_once_with("guild456", "user123")
    mock_cache.set_json.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_force_refresh(role_service, mock_cache, mock_discord_client):
    """Test force refresh skips cache."""
    mock_discord_client.get_guild_member.return_value = {"roles": ["role1"]}

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456", force_refresh=True)

    assert role_ids == ["role1"]
    mock_cache.get_json.assert_not_called()
    mock_discord_client.get_guild_member.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_role_ids_api_error(role_service, mock_cache, mock_discord_client):
    """Test handling Discord API error."""
    mock_cache.get_json.return_value = None
    mock_discord_client.get_guild_member.side_effect = discord_client.DiscordAPIError(
        404, "Not found"
    )

    with (
        patch.object(role_service, "_get_cache", return_value=mock_cache),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        role_ids = await role_service.get_user_role_ids("user123", "guild456")

    assert role_ids == []


@pytest.mark.asyncio
async def test_check_game_host_permission_channel_roles(role_service):
    """Test game host permission with channel-specific roles."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_channel = MagicMock()
    mock_channel.allowed_host_role_ids = ["role1", "role2"]
    mock_result.scalar_one_or_none.return_value = mock_channel
    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch.object(role_service, "get_user_role_ids", return_value=["role1", "role3"]):
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            channel_id="channel789",
        )

    assert has_perm is True


@pytest.mark.asyncio
async def test_check_game_host_permission_guild_roles(role_service):
    """Test game host permission falls back to guild roles."""
    mock_db = AsyncMock()

    # Channel query returns None
    mock_channel_result = MagicMock()
    mock_channel_result.scalar_one_or_none.return_value = None

    # Guild query returns config with allowed roles
    mock_guild_result = MagicMock()
    mock_guild = MagicMock()
    mock_guild.allowed_host_role_ids = ["role2", "role3"]
    mock_guild_result.scalar_one_or_none.return_value = mock_guild

    mock_db.execute = AsyncMock(side_effect=[mock_channel_result, mock_guild_result])

    with patch.object(role_service, "get_user_role_ids", return_value=["role2", "role4"]):
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            channel_id="channel789",
        )

    assert has_perm is True


@pytest.mark.asyncio
async def test_check_game_host_permission_manage_guild_fallback(role_service):
    """Test game host permission falls back to MANAGE_GUILD."""
    mock_db = AsyncMock()
    mock_discord_client = AsyncMock()

    # Channel and guild queries return None/no roles
    mock_channel_result = MagicMock()
    mock_channel_result.scalar_one_or_none.return_value = None

    mock_guild_result = MagicMock()
    mock_guild = MagicMock()
    mock_guild.allowed_host_role_ids = []
    mock_guild_result.scalar_one_or_none.return_value = mock_guild

    mock_db.execute = AsyncMock(side_effect=[mock_channel_result, mock_guild_result])

    mock_discord_client.get_user_guilds.return_value = [{"id": "guild456", "permissions": "32"}]

    with (
        patch.object(role_service, "get_user_role_ids", return_value=[]),
        patch.object(role_service, "discord_client", mock_discord_client),
    ):
        has_perm = await role_service.check_game_host_permission(
            "user123",
            "guild456",
            mock_db,
            access_token="token",
        )

    assert has_perm is True


@pytest.mark.asyncio
async def test_invalidate_user_roles(role_service, mock_cache):
    """Test invalidating cached user roles."""
    with patch.object(role_service, "_get_cache", return_value=mock_cache):
        await role_service.invalidate_user_roles("user123", "guild456")

    mock_cache.delete.assert_called_once()


def test_get_role_service_singleton():
    """Test role service singleton pattern."""
    service1 = roles.get_role_service()
    service2 = roles.get_role_service()

    assert service1 is service2

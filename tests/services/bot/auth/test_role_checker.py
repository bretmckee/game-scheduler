"""Tests for role verification service."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.auth.role_checker import RoleChecker, get_role_checker


@pytest.fixture
def mock_bot():
    """Create mock Discord bot."""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 12345
    return bot


@pytest.fixture
def mock_guild():
    """Create mock Discord guild."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 67890
    guild.roles = []
    return guild


@pytest.fixture
def mock_member():
    """Create mock Discord member with proper type."""
    member = MagicMock(spec=discord.Member)
    member.id = 11111
    member.roles = []
    member.guild_permissions = MagicMock()
    return member


@pytest.fixture
def role_checker(mock_bot):
    """Create RoleChecker instance."""
    return RoleChecker(mock_bot)


class TestRoleChecker:
    """Test suite for RoleChecker."""

    def test_initialization(self, mock_bot):
        """Test RoleChecker initialization."""
        checker = RoleChecker(mock_bot)
        assert checker.bot == mock_bot

    @pytest.mark.asyncio
    async def test_has_manage_guild_permission_with_permission(self, role_checker, mock_member):
        """Test checking MANAGE_GUILD when member has permission."""
        mock_member.guild_permissions.manage_guild = True
        mock_member.guild_permissions.administrator = False

        result = await role_checker.has_manage_guild_permission(mock_member)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_manage_guild_permission_with_administrator(self, role_checker, mock_member):
        """Test checking MANAGE_GUILD when member has administrator."""
        mock_member.guild_permissions.manage_guild = False
        mock_member.guild_permissions.administrator = True

        result = await role_checker.has_manage_guild_permission(mock_member)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_manage_guild_permission_without_permission(self, role_checker, mock_member):
        """Test checking MANAGE_GUILD when member lacks permission."""
        mock_member.guild_permissions.manage_guild = False
        mock_member.guild_permissions.administrator = False

        result = await role_checker.has_manage_guild_permission(mock_member)

        assert result is False

    @pytest.mark.asyncio
    async def test_has_manage_channels_permission_with_permission(self, role_checker, mock_member):
        """Test checking MANAGE_CHANNELS when member has permission."""
        mock_member.guild_permissions.manage_channels = True
        mock_member.guild_permissions.administrator = False

        result = await role_checker.has_manage_channels_permission(mock_member)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_manage_channels_permission_with_administrator(
        self, role_checker, mock_member
    ):
        """Test checking MANAGE_CHANNELS when member has administrator."""
        mock_member.guild_permissions.manage_channels = False
        mock_member.guild_permissions.administrator = True

        result = await role_checker.has_manage_channels_permission(mock_member)

        assert result is True

    @pytest.mark.asyncio
    async def test_has_manage_channels_permission_without_permission(
        self, role_checker, mock_member
    ):
        """Test checking MANAGE_CHANNELS when member lacks permission."""
        mock_member.guild_permissions.manage_channels = False
        mock_member.guild_permissions.administrator = False

        result = await role_checker.has_manage_channels_permission(mock_member)

        assert result is False

    @pytest.mark.asyncio
    async def test_invalidate_member_roles(self, role_checker, mock_guild, mock_member):
        """Test invalidating cached member roles."""
        with patch("services.bot.auth.cache.get_role_cache") as mock_get_cache:
            mock_cache = AsyncMock()
            mock_get_cache.return_value = mock_cache

            await role_checker.invalidate_member_roles(mock_guild, mock_member)

            mock_cache.invalidate_user_roles.assert_called_once_with(
                str(mock_member.id), str(mock_guild.id)
            )


def test_get_role_checker_singleton(mock_bot):
    """Test that get_role_checker returns singleton instance."""
    checker1 = get_role_checker(mock_bot)
    checker2 = get_role_checker(mock_bot)

    assert checker1 is checker2

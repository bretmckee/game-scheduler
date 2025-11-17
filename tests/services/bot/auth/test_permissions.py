"""Tests for Discord permission utilities."""

from services.bot.auth.permissions import (
    DiscordPermissions,
    has_administrator,
    has_all_permissions,
    has_any_permission,
    has_manage_channels,
    has_manage_guild,
    has_permission,
)


class TestPermissionChecks:
    """Test suite for permission checking functions."""

    def test_has_permission_with_single_permission(self):
        """Test checking for a single permission."""
        perms = DiscordPermissions.MANAGE_GUILD
        assert has_permission(perms, DiscordPermissions.MANAGE_GUILD) is True
        assert has_permission(perms, DiscordPermissions.ADMINISTRATOR) is False

    def test_has_permission_with_multiple_permissions(self):
        """Test checking permissions when user has multiple."""
        perms = DiscordPermissions.MANAGE_GUILD | DiscordPermissions.MANAGE_CHANNELS
        assert has_permission(perms, DiscordPermissions.MANAGE_GUILD) is True
        assert has_permission(perms, DiscordPermissions.MANAGE_CHANNELS) is True
        assert has_permission(perms, DiscordPermissions.ADMINISTRATOR) is False

    def test_has_permission_with_administrator(self):
        """Test that ADMINISTRATOR permission is detected."""
        perms = DiscordPermissions.ADMINISTRATOR
        assert has_permission(perms, DiscordPermissions.ADMINISTRATOR) is True

    def test_has_any_permission_with_one_match(self):
        """Test checking for any permission when one matches."""
        perms = DiscordPermissions.MANAGE_GUILD
        required = [DiscordPermissions.MANAGE_GUILD, DiscordPermissions.ADMINISTRATOR]
        assert has_any_permission(perms, required) is True

    def test_has_any_permission_with_no_match(self):
        """Test checking for any permission when none match."""
        perms = DiscordPermissions.SEND_MESSAGES
        required = [DiscordPermissions.MANAGE_GUILD, DiscordPermissions.ADMINISTRATOR]
        assert has_any_permission(perms, required) is False

    def test_has_all_permissions_with_all_present(self):
        """Test checking for all permissions when all are present."""
        perms = (
            DiscordPermissions.MANAGE_GUILD
            | DiscordPermissions.MANAGE_CHANNELS
            | DiscordPermissions.MANAGE_ROLES
        )
        required = [DiscordPermissions.MANAGE_GUILD, DiscordPermissions.MANAGE_CHANNELS]
        assert has_all_permissions(perms, required) is True

    def test_has_all_permissions_with_missing_permission(self):
        """Test checking for all permissions when one is missing."""
        perms = DiscordPermissions.MANAGE_GUILD
        required = [DiscordPermissions.MANAGE_GUILD, DiscordPermissions.MANAGE_CHANNELS]
        assert has_all_permissions(perms, required) is False

    def test_has_manage_guild(self):
        """Test MANAGE_GUILD permission check."""
        assert has_manage_guild(DiscordPermissions.MANAGE_GUILD) is True
        assert has_manage_guild(DiscordPermissions.SEND_MESSAGES) is False

    def test_has_administrator(self):
        """Test ADMINISTRATOR permission check."""
        assert has_administrator(DiscordPermissions.ADMINISTRATOR) is True
        assert has_administrator(DiscordPermissions.MANAGE_GUILD) is False

    def test_has_manage_channels(self):
        """Test MANAGE_CHANNELS permission check."""
        assert has_manage_channels(DiscordPermissions.MANAGE_CHANNELS) is True
        assert has_manage_channels(DiscordPermissions.SEND_MESSAGES) is False

    def test_permission_flags_are_powers_of_two(self):
        """Test that permission flags are valid bitwise values."""
        assert DiscordPermissions.CREATE_INSTANT_INVITE == 1 << 0
        assert DiscordPermissions.KICK_MEMBERS == 1 << 1
        assert DiscordPermissions.BAN_MEMBERS == 1 << 2
        assert DiscordPermissions.ADMINISTRATOR == 1 << 3
        assert DiscordPermissions.MANAGE_CHANNELS == 1 << 4
        assert DiscordPermissions.MANAGE_GUILD == 1 << 5

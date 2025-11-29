"""Unit tests for cache TTL configuration."""

from shared.cache.ttl import CacheTTL


class TestCacheTTL:
    """Test suite for CacheTTL constants."""

    def test_display_name_ttl(self):
        """Test display name TTL is 5 minutes."""
        assert CacheTTL.DISPLAY_NAME == 300

    def test_user_roles_ttl(self):
        """Test user roles TTL is 5 minutes."""
        assert CacheTTL.USER_ROLES == 300

    def test_session_ttl(self):
        """Test session TTL is 24 hours."""
        assert CacheTTL.SESSION == 86400

    def test_guild_config_ttl(self):
        """Test guild config TTL is 10 minutes."""
        assert CacheTTL.GUILD_CONFIG == 600

    def test_channel_config_ttl(self):
        """Test channel config TTL is 10 minutes."""
        assert CacheTTL.CHANNEL_CONFIG == 600

    def test_game_details_ttl(self):
        """Test game details TTL is 1 minute."""
        assert CacheTTL.GAME_DETAILS == 60

    def test_message_update_throttle_ttl(self):
        """Test message update throttle TTL is 2 seconds."""
        assert CacheTTL.MESSAGE_UPDATE_THROTTLE == 2

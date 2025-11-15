"""Unit tests for cache key patterns."""

from shared.cache.keys import CacheKeys


class TestCacheKeys:
    """Test suite for CacheKeys pattern generation."""

    def test_display_name_key(self):
        """Test display name cache key generation."""
        key = CacheKeys.display_name("guild123", "user456")
        assert key == "display:guild123:user456"

    def test_user_roles_key(self):
        """Test user roles cache key generation."""
        key = CacheKeys.user_roles("user456", "guild123")
        assert key == "user_roles:user456:guild123"

    def test_session_key(self):
        """Test session cache key generation."""
        key = CacheKeys.session("session_abc123")
        assert key == "session:session_abc123"

    def test_guild_config_key(self):
        """Test guild config cache key generation."""
        key = CacheKeys.guild_config("guild123")
        assert key == "guild_config:guild123"

    def test_channel_config_key(self):
        """Test channel config cache key generation."""
        key = CacheKeys.channel_config("channel789")
        assert key == "channel_config:channel789"

    def test_game_details_key(self):
        """Test game details cache key generation."""
        key = CacheKeys.game_details("game_uuid_123")
        assert key == "game:game_uuid_123"

    def test_oauth_state_key(self):
        """Test OAuth state cache key generation."""
        key = CacheKeys.oauth_state("state_random123")
        assert key == "oauth_state:state_random123"

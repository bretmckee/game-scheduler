"""Cache key pattern definitions for Redis."""


class CacheKeys:
    """Cache key patterns for consistent key generation."""

    @staticmethod
    def display_name(guild_id: str, user_id: str) -> str:
        """Return cache key for Discord user display names in a specific guild."""
        return f"display:{guild_id}:{user_id}"

    @staticmethod
    def user_roles(user_id: str, guild_id: str) -> str:
        """Return cache key for user's role IDs in a guild."""
        return f"user_roles:{user_id}:{guild_id}"

    @staticmethod
    def session(session_id: str) -> str:
        """Return cache key for user session data."""
        return f"session:{session_id}"

    @staticmethod
    def guild_config(guild_id: str) -> str:
        """Return cache key for guild configuration."""
        return f"guild_config:{guild_id}"

    @staticmethod
    def channel_config(channel_id: str) -> str:
        """Return cache key for channel configuration."""
        return f"channel_config:{channel_id}"

    @staticmethod
    def game_details(game_id: str) -> str:
        """Return cache key for game session details."""
        return f"game:{game_id}"

    @staticmethod
    def oauth_state(state: str) -> str:
        """Return cache key for OAuth2 state parameter."""
        return f"oauth_state:{state}"

    @staticmethod
    def message_update_throttle(game_id: str) -> str:
        """Return cache key for message update throttling."""
        return f"message_update:{game_id}"

"""Cache TTL configuration constants."""


class CacheTTL:
    """Time-to-live (TTL) constants for cache entries in seconds."""

    DISPLAY_NAME = 300  # 5 minutes
    USER_ROLES = 300  # 5 minutes
    SESSION = 86400  # 24 hours
    GUILD_CONFIG = 600  # 10 minutes
    CHANNEL_CONFIG = 600  # 10 minutes
    GAME_DETAILS = 60  # 1 minute

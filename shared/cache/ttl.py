"""Cache TTL configuration constants."""


class CacheTTL:
    """Time-to-live (TTL) constants for cache entries in seconds."""

    DISPLAY_NAME = 300  # 5 minutes
    USER_ROLES = 300  # 5 minutes
    SESSION = 86400  # 24 hours
    GUILD_CONFIG = 600  # 10 minutes
    CHANNEL_CONFIG = 600  # 10 minutes
    GAME_DETAILS = 60  # 1 minute
    USER_GUILDS = 300  # 5 minutes - Discord user guild membership
    DISCORD_CHANNEL = 300  # 5 minutes - Discord channel objects
    DISCORD_GUILD = 600  # 10 minutes - Discord guild objects
    DISCORD_USER = 300  # 5 minutes - Discord user objects
    MESSAGE_UPDATE_THROTTLE = 1.25  # 1.25 seconds - Rate limit for message updates

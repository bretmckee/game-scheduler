"""Cache TTL configuration constants."""


class CacheTTL:
    """Time-to-live (TTL) constants for cache entries in seconds."""

    DISPLAY_NAME: int = 300  # 5 minutes
    USER_ROLES: int = 300  # 5 minutes
    SESSION: int = 86400  # 24 hours
    GUILD_CONFIG: int = 600  # 10 minutes
    CHANNEL_CONFIG: int = 600  # 10 minutes
    GAME_DETAILS: int = 60  # 1 minute
    USER_GUILDS: int = 300  # 5 minutes - Discord user guild membership
    DISCORD_CHANNEL: int = 300  # 5 minutes - Discord channel objects
    DISCORD_GUILD: int = 600  # 10 minutes - Discord guild objects
    DISCORD_USER: int = 300  # 5 minutes - Discord user objects
    MESSAGE_UPDATE_THROTTLE: int = 2  # 2 seconds - Rate limit for message updates

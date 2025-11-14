"""TTL (Time To Live) configuration constants for different cache types."""

from typing import Final


class TTL:
    """TTL constants for different types of cached data."""
    
    # Short-term caching (minutes)
    DISPLAY_NAME: Final[int] = 5 * 60  # 5 minutes
    USER_ROLES: Final[int] = 5 * 60    # 5 minutes
    USER_PERMISSIONS: Final[int] = 5 * 60  # 5 minutes
    GUILD_MEMBER: Final[int] = 5 * 60  # 5 minutes
    
    # Medium-term caching (hours)
    GUILD_CONFIG: Final[int] = 30 * 60  # 30 minutes
    CHANNEL_CONFIG: Final[int] = 30 * 60  # 30 minutes
    GUILD_ROLES: Final[int] = 15 * 60   # 15 minutes
    GUILD_CHANNELS: Final[int] = 15 * 60  # 15 minutes
    
    # Game session caching
    GAME_SESSION: Final[int] = 10 * 60  # 10 minutes
    GAME_PARTICIPANTS: Final[int] = 2 * 60  # 2 minutes (frequently updated)
    GAME_SETTINGS: Final[int] = 15 * 60  # 15 minutes
    
    # Authentication and sessions
    USER_SESSION: Final[int] = 24 * 60 * 60  # 24 hours
    OAUTH_STATE: Final[int] = 10 * 60  # 10 minutes (OAuth flow timeout)
    OAUTH_TOKEN: Final[int] = 6 * 60 * 60  # 6 hours (shorter than Discord's 7 days)
    
    # Rate limiting
    RATE_LIMIT_USER: Final[int] = 60  # 1 minute
    RATE_LIMIT_IP: Final[int] = 60    # 1 minute
    RATE_LIMIT_DISCORD_API: Final[int] = 1  # 1 second (for burst protection)
    
    # Notification tracking
    NOTIFICATION_SENT: Final[int] = 7 * 24 * 60 * 60  # 7 days
    NOTIFICATION_LOCK: Final[int] = 5 * 60  # 5 minutes (prevent duplicate notifications)
    
    # Service health monitoring
    SERVICE_STATUS: Final[int] = 60  # 1 minute
    LAST_HEARTBEAT: Final[int] = 2 * 60  # 2 minutes
    
    # Batch operation caching
    DISPLAY_NAME_BATCH: Final[int] = 5 * 60  # 5 minutes
    
    @classmethod
    def get_ttl(cls, cache_type: str) -> int:
        """Get TTL for a specific cache type.
        
        Args:
            cache_type: Type of cache (e.g., 'display_name', 'user_roles')
            
        Returns:
            TTL in seconds
            
        Raises:
            KeyError: If cache_type is not defined
        """
        cache_type_upper = cache_type.upper()
        
        if hasattr(cls, cache_type_upper):
            return getattr(cls, cache_type_upper)
        
        # Default TTL if type not found
        return cls.DISPLAY_NAME  # 5 minutes default


class CacheTier:
    """Cache tier classification for different data types."""
    
    # Frequently changing data - short TTL
    HIGH_FREQUENCY = [
        "GAME_PARTICIPANTS",
        "USER_ROLES", 
        "USER_PERMISSIONS",
        "DISPLAY_NAME",
        "GUILD_MEMBER"
    ]
    
    # Moderately changing data - medium TTL
    MEDIUM_FREQUENCY = [
        "GUILD_CONFIG",
        "CHANNEL_CONFIG", 
        "GUILD_ROLES",
        "GAME_SESSION",
        "GAME_SETTINGS"
    ]
    
    # Rarely changing data - long TTL  
    LOW_FREQUENCY = [
        "USER_SESSION",
        "OAUTH_TOKEN",
        "NOTIFICATION_SENT"
    ]
    
    # Very short-lived data - minimal TTL
    TRANSIENT = [
        "OAUTH_STATE",
        "RATE_LIMIT_USER",
        "RATE_LIMIT_IP", 
        "RATE_LIMIT_DISCORD_API",
        "NOTIFICATION_LOCK"
    ]
    
    @classmethod
    def get_tier(cls, cache_type: str) -> str:
        """Get cache tier for a specific cache type.
        
        Args:
            cache_type: Type of cache
            
        Returns:
            Cache tier name
        """
        cache_type_upper = cache_type.upper()
        
        if cache_type_upper in cls.HIGH_FREQUENCY:
            return "HIGH_FREQUENCY"
        elif cache_type_upper in cls.MEDIUM_FREQUENCY:
            return "MEDIUM_FREQUENCY"
        elif cache_type_upper in cls.LOW_FREQUENCY:
            return "LOW_FREQUENCY"
        elif cache_type_upper in cls.TRANSIENT:
            return "TRANSIENT"
        else:
            return "UNKNOWN"


# Common TTL shortcuts for quick access
DISPLAY_NAME_TTL = TTL.DISPLAY_NAME
USER_ROLES_TTL = TTL.USER_ROLES
GUILD_CONFIG_TTL = TTL.GUILD_CONFIG
OAUTH_TOKEN_TTL = TTL.OAUTH_TOKEN
NOTIFICATION_TTL = TTL.NOTIFICATION_SENT
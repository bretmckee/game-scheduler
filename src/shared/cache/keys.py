"""Cache key pattern definitions for consistent key naming."""


class CacheKeys:
    """Centralized cache key patterns for consistent naming across services."""

    # User role caching patterns
    USER_ROLES = "user_roles:{user_id}:{guild_id}"
    USER_PERMISSIONS = "user_perms:{user_id}:{guild_id}"
    USER_GUILD_MEMBER = "guild_member:{guild_id}:{user_id}"

    # Display name resolution patterns
    DISPLAY_NAME = "display:{guild_id}:{user_id}"
    DISPLAY_NAME_BATCH = "display_batch:{guild_id}:{hash}"

    # Guild and channel data caching
    GUILD_CONFIG = "guild_config:{guild_id}"
    CHANNEL_CONFIG = "channel_config:{channel_id}"
    GUILD_ROLES = "guild_roles:{guild_id}"
    GUILD_CHANNELS = "guild_channels:{guild_id}"

    # Game session caching
    GAME_SESSION = "game_session:{game_id}"
    GAME_PARTICIPANTS = "game_participants:{game_id}"
    GAME_SETTINGS = "game_settings:{game_id}"

    # User session management (for web dashboard)
    USER_SESSION = "session:{session_id}"
    OAUTH_STATE = "oauth_state:{state}"
    OAUTH_TOKEN = "oauth_token:{user_id}"

    # Rate limiting patterns
    RATE_LIMIT_USER = "rate_limit:user:{user_id}"
    RATE_LIMIT_IP = "rate_limit:ip:{ip_address}"
    RATE_LIMIT_DISCORD_API = "rate_limit:discord_api:{endpoint}"

    # Notification tracking
    NOTIFICATION_SENT = "notification:{game_id}:{user_id}:{type}"
    NOTIFICATION_LOCK = "notification_lock:{game_id}"

    # Service health and status
    SERVICE_STATUS = "service_status:{service_name}"
    LAST_HEARTBEAT = "heartbeat:{service_name}"

    @classmethod
    def user_roles(cls, user_id: str, guild_id: str) -> str:
        """Generate user roles cache key.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Formatted cache key
        """
        return cls.USER_ROLES.format(user_id=user_id, guild_id=guild_id)

    @classmethod
    def user_permissions(cls, user_id: str, guild_id: str) -> str:
        """Generate user permissions cache key.
        
        Args:
            user_id: Discord user ID
            guild_id: Discord guild ID
            
        Returns:
            Formatted cache key
        """
        return cls.USER_PERMISSIONS.format(user_id=user_id, guild_id=guild_id)

    @classmethod
    def display_name(cls, guild_id: str, user_id: str) -> str:
        """Generate display name cache key.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            
        Returns:
            Formatted cache key
        """
        return cls.DISPLAY_NAME.format(guild_id=guild_id, user_id=user_id)

    @classmethod
    def guild_member(cls, guild_id: str, user_id: str) -> str:
        """Generate guild member cache key.
        
        Args:
            guild_id: Discord guild ID
            user_id: Discord user ID
            
        Returns:
            Formatted cache key
        """
        return cls.USER_GUILD_MEMBER.format(guild_id=guild_id, user_id=user_id)

    @classmethod
    def guild_config(cls, guild_id: str) -> str:
        """Generate guild configuration cache key.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Formatted cache key
        """
        return cls.GUILD_CONFIG.format(guild_id=guild_id)

    @classmethod
    def channel_config(cls, channel_id: str) -> str:
        """Generate channel configuration cache key.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            Formatted cache key
        """
        return cls.CHANNEL_CONFIG.format(channel_id=channel_id)

    @classmethod
    def guild_roles(cls, guild_id: str) -> str:
        """Generate guild roles cache key.
        
        Args:
            guild_id: Discord guild ID
            
        Returns:
            Formatted cache key
        """
        return cls.GUILD_ROLES.format(guild_id=guild_id)

    @classmethod
    def game_session(cls, game_id: str) -> str:
        """Generate game session cache key.
        
        Args:
            game_id: Game session UUID
            
        Returns:
            Formatted cache key
        """
        return cls.GAME_SESSION.format(game_id=game_id)

    @classmethod
    def game_participants(cls, game_id: str) -> str:
        """Generate game participants cache key.
        
        Args:
            game_id: Game session UUID
            
        Returns:
            Formatted cache key
        """
        return cls.GAME_PARTICIPANTS.format(game_id=game_id)

    @classmethod
    def user_session(cls, session_id: str) -> str:
        """Generate user session cache key.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted cache key
        """
        return cls.USER_SESSION.format(session_id=session_id)

    @classmethod
    def oauth_state(cls, state: str) -> str:
        """Generate OAuth state cache key.
        
        Args:
            state: OAuth state parameter
            
        Returns:
            Formatted cache key
        """
        return cls.OAUTH_STATE.format(state=state)

    @classmethod
    def oauth_token(cls, user_id: str) -> str:
        """Generate OAuth token cache key.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Formatted cache key
        """
        return cls.OAUTH_TOKEN.format(user_id=user_id)

    @classmethod
    def notification_sent(cls, game_id: str, user_id: str, notification_type: str) -> str:
        """Generate notification tracking cache key.
        
        Args:
            game_id: Game session UUID
            user_id: Discord user ID
            notification_type: Type of notification (e.g., '1_hour_before')
            
        Returns:
            Formatted cache key
        """
        return cls.NOTIFICATION_SENT.format(
            game_id=game_id,
            user_id=user_id,
            type=notification_type
        )

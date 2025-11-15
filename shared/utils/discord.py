"""Discord API helper utilities."""


def format_discord_timestamp(unix_timestamp: int, format_type: str = "F") -> str:
    """
    Format Unix timestamp for Discord's native timestamp rendering.

    Args:
        unix_timestamp: Unix timestamp (seconds since epoch)
        format_type: Discord timestamp format:
            - 'F': Full (e.g., "Friday, November 15, 2025 7:00 PM")
            - 'f': Short (e.g., "November 15, 2025 7:00 PM")
            - 'R': Relative (e.g., "in 2 hours")
            - 'D': Date only (e.g., "11/15/2025")
            - 'T': Time only (e.g., "7:00 PM")

    Returns:
        Discord timestamp string (e.g., "<t:1731700800:F>")
    """
    return f"<t:{unix_timestamp}:{format_type}>"


def format_user_mention(user_id: str) -> str:
    """
    Format Discord user ID as mention.

    Args:
        user_id: Discord user snowflake ID

    Returns:
        Discord mention string (e.g., "<@123456789012345678>")
    """
    return f"<@{user_id}>"


def format_channel_mention(channel_id: str) -> str:
    """
    Format Discord channel ID as mention.

    Args:
        channel_id: Discord channel snowflake ID

    Returns:
        Discord channel mention string (e.g., "<#987654321098765432>")
    """
    return f"<#{channel_id}>"


def format_role_mention(role_id: str) -> str:
    """
    Format Discord role ID as mention.

    Args:
        role_id: Discord role snowflake ID

    Returns:
        Discord role mention string (e.g., "<@&555444333222111000>")
    """
    return f"<@&{role_id}>"


def parse_mention(mention_text: str) -> str | None:
    """
    Parse user ID from Discord mention format.

    Args:
        mention_text: Mention string (e.g., "<@123456789012345678>")

    Returns:
        User ID if valid mention, None otherwise
    """
    if mention_text.startswith("<@") and mention_text.endswith(">"):
        # Handle both <@123> and <@!123> formats
        user_id = mention_text[2:-1].lstrip("!")
        if user_id.isdigit():
            return user_id
    return None


def has_permission(permissions: int, permission_flag: int) -> bool:
    """
    Check if permission bitfield has specific permission.

    Args:
        permissions: Permission bitfield from Discord
        permission_flag: Specific permission to check (e.g., 0x00000020 for MANAGE_GUILD)

    Returns:
        True if permission is granted
    """
    return (permissions & permission_flag) == permission_flag


class DiscordPermissions:
    """Common Discord permission flags."""

    ADMINISTRATOR = 0x00000008
    MANAGE_GUILD = 0x00000020
    MANAGE_CHANNELS = 0x00000010
    MANAGE_ROLES = 0x10000000
    SEND_MESSAGES = 0x00000800
    EMBED_LINKS = 0x00004000
    USE_EXTERNAL_EMOJIS = 0x00040000
    ADD_REACTIONS = 0x00000040


def build_oauth_url(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: str,
) -> str:
    """
    Build Discord OAuth2 authorization URL.

    Args:
        client_id: Discord application client ID
        redirect_uri: OAuth2 redirect URI
        scopes: List of OAuth2 scopes (e.g., ['identify', 'guilds'])
        state: CSRF protection state token

    Returns:
        Full OAuth2 authorization URL
    """
    scope_str = " ".join(scopes)
    return (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope_str}"
        f"&state={state}"
    )

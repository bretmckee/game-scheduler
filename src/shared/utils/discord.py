"""
Discord API helpers and utilities for user resolution and permission checking.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DiscordUser:
    """Discord user information."""
    id: str
    username: str
    global_name: Optional[str] = None
    avatar: Optional[str] = None


@dataclass 
class GuildMember:
    """Discord guild member information."""
    user: DiscordUser
    nick: Optional[str] = None
    roles: List[str] = None
    
    @property
    def display_name(self) -> str:
        """Get resolved display name using Discord priority."""
        return self.nick or self.user.global_name or self.user.username


def extract_mention_text(mention: str) -> str:
    """
    Extract username from @mention format.
    
    Args:
        mention: Input string (e.g., "@username", "  @display name  ")
        
    Returns:
        Cleaned mention text without @ prefix
        
    Raises:
        ValueError: If input doesn't start with @
    """
    mention = mention.strip()
    if not mention.startswith('@'):
        raise ValueError("Mention must start with @")
    
    return mention[1:].strip().lower()


def is_mention_format(text: str) -> bool:
    """Check if text is in @mention format."""
    return text.strip().startswith('@')


def validate_discord_id(discord_id: str) -> str:
    """
    Validate Discord snowflake ID format.
    
    Args:
        discord_id: Discord ID string
        
    Returns:
        Validated Discord ID
        
    Raises:
        ValueError: If ID format is invalid
    """
    if not discord_id.isdigit():
        raise ValueError("Discord ID must be numeric")
    
    if len(discord_id) < 17 or len(discord_id) > 19:
        raise ValueError("Discord ID must be 17-19 digits (snowflake format)")
    
    return discord_id


def parse_discord_permissions(permissions: str) -> int:
    """
    Parse Discord permissions bitfield.
    
    Args:
        permissions: Permissions as string (from OAuth2 response)
        
    Returns:
        Permissions as integer bitfield
    """
    try:
        return int(permissions)
    except (ValueError, TypeError):
        return 0


def has_permission(permissions: int, permission_flag: int) -> bool:
    """
    Check if permissions bitfield contains specific permission.
    
    Args:
        permissions: User's permissions bitfield
        permission_flag: Permission flag to check
        
    Returns:
        Whether user has the permission
    """
    return (permissions & permission_flag) == permission_flag


# Discord permission flags (bitfield values)
class DiscordPermissions:
    """Discord permission flag constants."""
    CREATE_INSTANT_INVITE = 0x00000001
    KICK_MEMBERS = 0x00000002
    BAN_MEMBERS = 0x00000004
    ADMINISTRATOR = 0x00000008
    MANAGE_CHANNELS = 0x00000010
    MANAGE_GUILD = 0x00000020
    ADD_REACTIONS = 0x00000040
    VIEW_AUDIT_LOG = 0x00000080
    PRIORITY_SPEAKER = 0x00000100
    STREAM = 0x00000200
    VIEW_CHANNEL = 0x00000400
    SEND_MESSAGES = 0x00000800
    SEND_TTS_MESSAGES = 0x00001000
    MANAGE_MESSAGES = 0x00002000
    EMBED_LINKS = 0x00004000
    ATTACH_FILES = 0x00008000
    READ_MESSAGE_HISTORY = 0x00010000
    MENTION_EVERYONE = 0x00020000
    USE_EXTERNAL_EMOJIS = 0x00040000
    VIEW_GUILD_INSIGHTS = 0x00080000
    CONNECT = 0x00100000
    SPEAK = 0x00200000
    MUTE_MEMBERS = 0x00400000
    DEAFEN_MEMBERS = 0x00800000
    MOVE_MEMBERS = 0x01000000
    USE_VAD = 0x02000000
    CHANGE_NICKNAME = 0x04000000
    MANAGE_NICKNAMES = 0x08000000
    MANAGE_ROLES = 0x10000000
    MANAGE_WEBHOOKS = 0x20000000
    MANAGE_EMOJIS_AND_STICKERS = 0x40000000


def can_manage_guild(permissions: int) -> bool:
    """Check if user can manage guild settings."""
    return has_permission(permissions, DiscordPermissions.ADMINISTRATOR) or \
           has_permission(permissions, DiscordPermissions.MANAGE_GUILD)


def can_manage_channels(permissions: int) -> bool:
    """Check if user can manage channel settings."""
    return has_permission(permissions, DiscordPermissions.ADMINISTRATOR) or \
           has_permission(permissions, DiscordPermissions.MANAGE_CHANNELS)


def format_user_mention(discord_id: str) -> str:
    """
    Format Discord user ID as mention for bot messages.
    
    Args:
        discord_id: Discord user ID
        
    Returns:
        Discord mention string (e.g., "<@123456789>")
    """
    validate_discord_id(discord_id)
    return f"<@{discord_id}>"


def parse_user_mention(mention: str) -> Optional[str]:
    """
    Parse Discord user mention to extract user ID.
    
    Args:
        mention: Discord mention string (e.g., "<@123456789>" or "<@!123456789>")
        
    Returns:
        Discord user ID or None if not a valid mention
    """
    # Match both <@123456789> and <@!123456789> formats
    match = re.match(r'^<@!?(\d{17,19})>$', mention.strip())
    if match:
        return match.group(1)
    return None


def build_member_search_query(query: str) -> str:
    """
    Build query string for Discord guild member search API.
    
    Args:
        query: User search input
        
    Returns:
        Formatted query for Discord API
    """
    # Remove common prefixes and clean up
    query = query.strip().lower()
    if query.startswith('@'):
        query = query[1:]
    
    # Discord API expects URL-encoded query
    return query.strip()
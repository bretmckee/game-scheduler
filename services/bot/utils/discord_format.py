# Copyright 2025-2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


"""Discord message formatting utilities.

This module provides utilities for formatting Discord messages with mentions,
timestamps, and participant lists following Discord's native formatting patterns.
"""

import logging
from datetime import datetime

import discord

from services.bot.dependencies.discord_client import get_discord_client
from shared.discord import client as discord_client

logger = logging.getLogger(__name__)


async def get_member_display_info(
    _bot: discord.Client, guild_id: str, user_id: str
) -> tuple[str | None, str | None]:
    """Get member display name and avatar URL from Discord with caching.

    Uses DiscordAPIClient for caching to reduce Discord API calls across services.
    Falls back to discord.py in-memory cache if member not in API cache.

    Args:
        bot: Discord bot client (kept for compatibility, used as fallback)
        guild_id: Discord guild ID
        user_id: Discord user ID

    Returns:
        Tuple of (display_name, avatar_url) or (None, None) if member not found
    """
    try:
        discord_api = get_discord_client()
        member_data = await discord_api.get_guild_member(guild_id, user_id)

        if not member_data:
            logger.warning("Member %s not found in guild %s", user_id, guild_id)
            return None, None

        display_name = (
            member_data.get("nick")
            or member_data["user"].get("global_name")
            or member_data["user"].get("username")
        )

        member_avatar = member_data.get("avatar")
        user_avatar = member_data["user"].get("avatar")
        avatar_url = _build_avatar_url(user_id, guild_id, member_avatar, user_avatar)

        return display_name, avatar_url

    except discord_client.DiscordAPIError as e:
        logger.warning(
            "API error fetching member info for %s in guild %s: %s",
            user_id,
            guild_id,
            e,
        )
        return None, None
    except (ValueError, KeyError) as e:
        logger.warning("Failed to parse member info for %s in guild %s: %s", user_id, guild_id, e)
        return None, None
    except Exception as e:
        logger.error("Unexpected error getting member info: %s", e)
        return None, None


def _build_avatar_url(
    user_id: str,
    guild_id: str,
    member_avatar: str | None,
    user_avatar: str | None,
    size: int = 64,
) -> str | None:
    """
    Build Discord CDN avatar URL with proper priority.

    Priority: guild member avatar > user avatar > None.

    Args:
        user_id: Discord user ID
        guild_id: Discord guild ID
        member_avatar: Guild-specific avatar hash (optional)
        user_avatar: User's global avatar hash (optional)
        size: Image size in pixels (default 64)

    Returns:
        Discord CDN avatar URL or None if no avatar
    """
    if member_avatar:
        ext = "gif" if member_avatar.startswith("a_") else "png"
        return (
            f"https://cdn.discordapp.com/guilds/{guild_id}/users/{user_id}/avatars/"
            f"{member_avatar}.{ext}?size={size}"
        )
    if user_avatar:
        ext = "gif" if user_avatar.startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user_id}/{user_avatar}.{ext}?size={size}"

    # Fallback to default embed avatar when no custom avatar
    try:
        default_index = int(user_id) % 6
        return f"https://cdn.discordapp.com/embed/avatars/{default_index}.png?size={size}"
    except ValueError:
        return None


def format_discord_mention(user_id: str) -> str:
    """Format a Discord user mention.

    Args:
        user_id: Discord user snowflake ID

    Returns:
        Discord mention string in format <@user_id>
    """
    return f"<@{user_id}>"


def format_user_or_placeholder(user_id: str) -> str:
    """Format a user ID as Discord mention or return placeholder name.

    Args:
        user_id: Discord user ID (numeric string) or placeholder name

    Returns:
        Discord mention for IDs, plain text for placeholder names
    """
    return user_id if not user_id.isdigit() else format_discord_mention(user_id)


def format_discord_timestamp(dt: datetime, style: str = "F") -> str:
    """Format a datetime as a Discord timestamp.

    Discord timestamps are automatically displayed in each user's local timezone.

    Args:
        dt: Datetime to format (should be UTC)
        style: Discord timestamp style:
            - F: Full date/time (default): "Friday, November 15, 2025 7:00 PM"
            - f: Short date/time: "November 15, 2025 7:00 PM"
            - D: Date only: "11/15/2025"
            - d: Short date: "11/15/25"
            - T: Time only: "7:00 PM"
            - t: Short time: "7:00 PM"
            - R: Relative: "in 2 hours"

    Returns:
        Discord timestamp string in format <t:unix_timestamp:style>
    """
    unix_timestamp = int(dt.timestamp())
    return f"<t:{unix_timestamp}:{style}>"


def format_participant_list(
    participant_ids: list[str],
    max_display: int = 10,
    include_count: bool = True,
    start_number: int = 1,
) -> str:
    """Format a list of participants using Discord mentions or placeholder names.

    Args:
        participant_ids: List of Discord user IDs or placeholder names
        max_display: Maximum number of participants to display
        include_count: Whether to include total count if truncated
        start_number: Starting number for the numbered list (default: 1)

    Returns:
        Formatted participant list with Discord mentions and/or placeholder names
    """
    if not participant_ids:
        return "No participants yet"

    # Format each participant with number: Discord mention for IDs, plain text for placeholders
    mentions = [
        f"{start_number + i}. {format_user_or_placeholder(uid)}"
        for i, uid in enumerate(participant_ids[:max_display])
    ]
    result = "\n".join(mentions)

    if len(participant_ids) > max_display and include_count:
        remaining = len(participant_ids) - max_display
        result += f"\n... and {remaining} more"

    return result


def format_game_status_emoji(status: str) -> str:
    """Get emoji for game status.

    Args:
        status: Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)

    Returns:
        Appropriate emoji for the status
    """
    emoji_map = {
        "SCHEDULED": "📅",
        "IN_PROGRESS": "🎮",
        "COMPLETED": "✅",
        "CANCELLED": "❌",
    }
    return emoji_map.get(status, "❓")


def format_rules_section(rules: str | None, max_length: int = 500) -> str:
    """Format rules section for display in embed.

    Args:
        rules: Game rules text
        max_length: Maximum length before truncation

    Returns:
        Formatted rules text, truncated if necessary
    """
    if not rules or not rules.strip():
        return "No rules specified"

    if len(rules) > max_length:
        return rules[: max_length - 3] + "..."
    return rules


def format_duration(minutes: int | None) -> str:
    """Format duration in minutes to human-readable string.

    Args:
        minutes: Duration in minutes

    Returns:
        Formatted duration string (e.g., "2h 30m", "1h", "45m")
    """
    if minutes is None or minutes <= 0:
        return ""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if hours > 0 and remaining_minutes > 0:
        return f"{hours}h {remaining_minutes}m"
    if hours > 0:
        return f"{hours}h"
    return f"{remaining_minutes}m"

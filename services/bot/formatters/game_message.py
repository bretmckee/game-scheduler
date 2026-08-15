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


"""Game session message formatter.

This module provides utilities for formatting Discord messages for game sessions,
including announcements, updates, and participant lists.
"""

import contextlib
import logging
import math
from datetime import datetime

import discord

from services.bot.config import get_config
from services.bot.utils.discord_format import (
    format_discord_mention,
    format_discord_timestamp,
    format_duration,
    format_numbered_participants,
    format_participant_list,
    format_user_or_placeholder,
    split_row_major,
)
from services.bot.views.game_view import GameView
from shared.models import GameStatus
from shared.utils.limits import DISCORD_EMBED_TOTAL_SAFE_LIMIT, EMBED_FIELD_REWARDS

logger = logging.getLogger(__name__)

_MIME_TO_EXT: dict[str, str] = {
    "image/gif": ".gif",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

# Participants always occupy two side-by-side embed columns, leaving room for
# the Links field to complete that row. The waitlist, when present, gets its
# own row below split across three columns. See _add_participant_fields.
_PARTICIPANT_COLUMNS = 2
_WAITLIST_COLUMNS = 3
_PARTICIPANT_MAX_DISPLAY = 15
_WAITLIST_MAX_DISPLAY = 15


class GameMessageFormatter:
    """Formatter for game session Discord messages.

    Formats game announcements and updates with Discord native mentions,
    timestamps, and embedded content.
    """

    @staticmethod
    def _prepare_description_and_urls(
        description: str,
        game_id: str | None,
        thumbnail_url: str | None,
        image_url: str | None,
    ) -> tuple[str, str | None, str | None, str | None]:
        """Prepare truncated description and URLs for embed.

        Args:
            description: Original game description
            game_id: Optional game UUID
            thumbnail_url: Optional thumbnail URL
            image_url: Optional image URL

        Returns:
            Tuple of (truncated_description, calendar_url, thumbnail_url, image_url)
        """
        truncated_description = description

        calendar_url = None
        if game_id:
            config = get_config()
            calendar_url = f"{config.frontend_url}/download-calendar/{game_id}"

        return truncated_description, calendar_url, thumbnail_url, image_url

    @staticmethod
    def _configure_embed_author(
        embed: discord.Embed,
        host_id: str,
        host_display_name: str | None,
        host_avatar_url: str | None,
    ) -> None:
        """Configure embed author with host information.

        Args:
            embed: Discord embed to configure
            host_id: Discord ID of the game host
            host_display_name: Optional display name for host
            host_avatar_url: Optional host avatar URL
        """
        if host_display_name:
            author_name = f"@{host_display_name}"
        else:
            author_name = host_id if not host_id.isdigit() else "@User"

        if host_avatar_url:
            embed.set_author(name=author_name, icon_url=host_avatar_url)
        else:
            embed.set_author(name=author_name)

    @staticmethod
    def _add_game_time_fields(
        embed: discord.Embed,
        scheduled_at: datetime,
        host_id: str,
        expected_duration_minutes: int | None,
        where: str | None,
        channel_id: str | None,
    ) -> None:
        """Add game time, host, duration, location, and channel fields.

        Args:
            embed: Discord embed to configure
            scheduled_at: When game is scheduled
            host_id: Discord ID of host
            expected_duration_minutes: Optional game duration
            where: Optional game location
            channel_id: Optional voice channel ID
        """
        game_time_value = (
            f"{format_discord_timestamp(scheduled_at, 'F')} "
            f"({format_discord_timestamp(scheduled_at, 'R')})"
        )
        embed.add_field(name="Game Time", value=game_time_value, inline=False)

        # The host is always mentioned live in the message content (see
        # format_game_announcement), which caches them client-side, so this
        # field can use a plain mention rather than a resolved display name.
        formatted_host = format_user_or_placeholder(host_id)
        embed.add_field(name="Host", value=formatted_host, inline=True)

        if expected_duration_minutes:
            duration_text = format_duration(expected_duration_minutes)
            embed.add_field(name="Run Time", value=duration_text, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if where:
            embed.add_field(name="Where", value=where, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if channel_id:
            embed.add_field(name="Voice Channel", value=f"<#{channel_id}>", inline=False)

    @staticmethod
    def _add_participant_fields(
        embed: discord.Embed,
        participant_ids: list[str],
        overflow_ids: list[str],
        current_count: int,
        max_players: int,
        calendar_url: str | None = None,
        overflow_display_names: dict[str, str] | None = None,
    ) -> None:
        """Add participant, waitlist, and links fields to embed.

        Participants always fill two side-by-side columns (split contiguously
        in half), leaving room for the Links field to complete that row. When
        there's a waitlist, it gets its own row below, split row-major across
        three columns and numbered independently starting at 1 (see
        split_row_major) rather than continuing from the participant count.

        Args:
            embed: Discord embed to configure
            participant_ids: List of confirmed participant IDs
            overflow_ids: List of waitlisted participant IDs
            current_count: Current participant count
            max_players: Maximum allowed participants
            calendar_url: Optional calendar download URL, rendered as the
                third column alongside the two participant columns
            overflow_display_names: Optional map of user_id -> resolved
                display name for waitlisted participants, rendered instead of
                a raw `<@id>` mention. Confirmed participants are always
                rendered as raw mentions since they're mentioned live in the
                message content (see format_game_announcement), which caches
                them client-side; waitlisted participants aren't mentioned
                there, so they still need the resolved-name workaround.
        """
        open_slots = max(0, max_players - len(participant_ids))
        if open_slots > 0:
            participant_ids = list(participant_ids) + ["open slot"] * open_slots

        participants_name = f"Participants ({current_count}/{max_players})"
        if participant_ids:
            left_text, right_text = GameMessageFormatter._format_participant_columns(
                participant_ids
            )
            embed.add_field(name=participants_name, value=left_text, inline=True)
            embed.add_field(name="\u200b", value=right_text, inline=True)
        else:
            embed.add_field(name=participants_name, value="No participants yet", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if calendar_url:
            links_value = f"📅 [Add to Calendar]({calendar_url})"
            embed.add_field(name="Links", value=links_value, inline=True)
        else:
            embed.add_field(name="\u200b", value="\u200b", inline=True)

        if overflow_ids:
            for index, text in enumerate(
                GameMessageFormatter._format_waitlist_columns(overflow_ids, overflow_display_names)
            ):
                name = f"Waitlisted ({len(overflow_ids)})" if index == 0 else "\u200b"
                embed.add_field(name=name, value=text, inline=True)

    @staticmethod
    def _format_participant_columns(participant_ids: list[str]) -> tuple[str, str]:
        """Split a (already open-slot-padded) participant list into two columns.

        The list is truncated to `_PARTICIPANT_MAX_DISPLAY` entries and split
        contiguously in half, with any excess noted as "... and N more" at
        the end of the second column.

        Args:
            participant_ids: Confirmed participant IDs, padded with "open
                slot" placeholders up to capacity

        Returns:
            Tuple of (left_column_text, right_column_text)
        """
        displayed = participant_ids[:_PARTICIPANT_MAX_DISPLAY]
        remaining = len(participant_ids) - len(displayed)
        midpoint = math.ceil(len(displayed) / _PARTICIPANT_COLUMNS)
        left, right = displayed[:midpoint], displayed[midpoint:]

        left_text = format_participant_list(left, max_display=len(left), include_count=False)
        right_text = (
            format_participant_list(
                right, max_display=len(right), start_number=midpoint + 1, include_count=False
            )
            if right
            else "\u200b"
        )
        if remaining:
            note = f"... and {remaining} more"
            right_text = f"{right_text}\n{note}" if right_text != "\u200b" else note

        return left_text, right_text

    @staticmethod
    def _format_waitlist_columns(
        overflow_ids: list[str],
        overflow_display_names: dict[str, str] | None,
    ) -> list[str]:
        """Split the waitlist into row-major columns, numbered independently from 1.

        The list is truncated to `_WAITLIST_MAX_DISPLAY` entries before being
        distributed across `_WAITLIST_COLUMNS` columns, with any excess noted
        as "... and N more" at the end of the last column.

        Args:
            overflow_ids: Waitlisted participant IDs, in join order
            overflow_display_names: Optional map of user_id -> resolved
                display name

        Returns:
            One rendered column of text per waitlist column
        """
        displayed = overflow_ids[:_WAITLIST_MAX_DISPLAY]
        remaining = len(overflow_ids) - len(displayed)
        columns = split_row_major(displayed, _WAITLIST_COLUMNS)
        texts = [format_numbered_participants(column, overflow_display_names) for column in columns]

        if remaining:
            note = f"... and {remaining} more"
            texts[-1] = f"{texts[-1]}\n{note}" if texts[-1] != "\u200b" else note

        return texts

    @staticmethod
    def _add_footer(embed: discord.Embed, status: str) -> None:
        """Add the status footer to embed.

        The Links field is added earlier, alongside the participant columns
        (see _add_participant_fields), so this only sets the footer.

        Args:
            embed: Discord embed to configure
            status: Game status
        """
        status_display = status
        with contextlib.suppress(ValueError, AttributeError):
            status_display = GameStatus(status).display_name

        embed.set_footer(text=f"Status: {status_display}")

    @staticmethod
    def create_game_embed(
        game_title: str,
        description: str,
        scheduled_at: datetime,
        host_id: str,
        participant_ids: list[str],
        overflow_ids: list[str],
        current_count: int,
        max_players: int,
        status: str,
        channel_id: str | None = None,
        _signup_instructions: str | None = None,
        expected_duration_minutes: int | None = None,
        where: str | None = None,
        game_id: str | None = None,
        host_display_name: str | None = None,
        host_avatar_url: str | None = None,
        thumbnail_url: str | None = None,
        image_url: str | None = None,
        rewards: str | None = None,
        overflow_display_names: dict[str, str] | None = None,
    ) -> discord.Embed:
        """Create an embed for a game session.

        Args:
            game_title: Game title
            description: Game description
            scheduled_at: When game is scheduled (UTC datetime)
            host_id: Discord ID of the game host
            participant_ids: List of confirmed participant Discord IDs (within max_players)
            overflow_ids: List of overflow participant Discord IDs (beyond max_players)
            current_count: Current confirmed participant count
            max_players: Maximum allowed participants
            status: Game status
            channel_id: Optional Discord channel ID
            signup_instructions: Optional signup instructions
            expected_duration_minutes: Optional expected game duration in minutes
            where: Optional game location
            game_id: Optional game UUID for calendar download link
            host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
            thumbnail_url: Optional thumbnail image URL
            image_url: Optional banner image URL
            overflow_display_names: Optional map of user_id -> resolved
                display name for waitlisted participants, rendered instead of
                a raw `<@id>` mention

        Returns:
            Configured Discord embed
        """
        truncated_description, calendar_url, thumb_url, img_url = (
            GameMessageFormatter._prepare_description_and_urls(
                description, game_id, thumbnail_url, image_url
            )
        )

        embed = discord.Embed(
            title=game_title,
            description=truncated_description,
            color=GameMessageFormatter._get_status_color(status),
        )

        GameMessageFormatter._configure_embed_author(
            embed, host_id, host_display_name, host_avatar_url
        )

        if thumb_url:
            embed.set_thumbnail(url=thumb_url)
        if img_url:
            embed.set_image(url=img_url)

        GameMessageFormatter._add_game_time_fields(
            embed,
            scheduled_at,
            host_id,
            expected_duration_minutes,
            where,
            channel_id,
        )

        GameMessageFormatter._add_participant_fields(
            embed,
            participant_ids,
            overflow_ids,
            current_count,
            max_players,
            calendar_url,
            overflow_display_names,
        )

        if rewards:
            embed.add_field(name=EMBED_FIELD_REWARDS, value=f"||{rewards}||", inline=False)

        GameMessageFormatter._add_footer(embed, status)

        return GameMessageFormatter._trim_embed_if_needed(embed)

    @staticmethod
    def _trim_embed_if_needed(embed: discord.Embed) -> discord.Embed:
        excess = len(embed) - DISCORD_EMBED_TOTAL_SAFE_LIMIT
        if excess > 0 and embed.description:
            trim_to = len(embed.description) - excess - 3
            embed.description = embed.description[:trim_to] + "..."
        return embed

    @staticmethod
    def _get_status_color(status: str) -> discord.Color:
        """Get Discord color for game status.

        Args:
            status: Game status

        Returns:
            Discord color
        """
        color_map = {
            "SCHEDULED": discord.Color.green(),
            "IN_PROGRESS": discord.Color.blue(),
            "COMPLETED": discord.Color.gold(),
            "CANCELLED": discord.Color.red(),
        }
        return color_map.get(status, discord.Color.greyple())

    @staticmethod
    def create_notification_embed(
        game_title: str,
        scheduled_at: datetime,
        host_id: str,
        time_until: str,
    ) -> discord.Embed:
        """Create notification embed for game reminders.

        Args:
            game_title: Game title
            scheduled_at: When game is scheduled
            host_id: Discord ID of game host
            time_until: Human-readable time until game (e.g., "in 1 hour")

        Returns:
            Configured notification embed
        """
        embed = discord.Embed(
            title="🔔 Game Reminder",
            description=f"**{game_title}** starts {time_until}!",
            color=discord.Color.blue(),
        )

        embed.add_field(
            name="📅 Start Time",
            value=format_discord_timestamp(scheduled_at, "F"),
            inline=False,
        )

        embed.add_field(name="🎯 Host", value=format_discord_mention(host_id), inline=False)

        return embed


def format_game_announcement(
    game_id: str,
    game_title: str,
    description: str,
    scheduled_at: datetime,
    host_id: str,
    participant_ids: list[str],
    overflow_ids: list[str],
    current_count: int,
    max_players: int,
    status: str,
    signup_method: str,
    channel_id: str | None = None,
    signup_instructions: str | None = None,
    expected_duration_minutes: int | None = None,
    notify_role_ids: list[str] | None = None,
    where: str | None = None,
    host_display_name: str | None = None,
    host_avatar_url: str | None = None,
    thumbnail_id: str | None = None,
    banner_image_id: str | None = None,
    guild_id: str | None = None,
    rewards: str | None = None,
    thumbnail_mime_type: str | None = None,
    banner_image_mime_type: str | None = None,
    overflow_display_names: dict[str, str] | None = None,
) -> tuple[str | None, discord.Embed, GameView]:
    """Format a complete game announcement with embed and buttons.

    Args:
        game_id: Game session UUID
        game_title: Game title
        description: Game description
        scheduled_at: When game is scheduled (UTC)
        host_id: Discord ID of game host
        participant_ids: List of confirmed participant Discord IDs (within max_players)
        overflow_ids: List of overflow participant Discord IDs (beyond max_players)
        current_count: Current confirmed participant count
        max_players: Maximum allowed participants
        status: Game status
        signup_method: Signup method (SELF_SIGNUP or HOST_SELECTED)
        channel_id: Optional voice channel ID
        signup_instructions: Optional signup instructions
        expected_duration_minutes: Optional expected game duration in minutes
        notify_role_ids: Optional list of Discord role IDs to mention
        where: Optional game location
        host_avatar_url: Optional host Discord CDN avatar URL for embed author icon
        thumbnail_id: UUID of thumbnail image if present
        banner_image_id: UUID of banner image if present
        guild_id: Optional guild ID for special @everyone handling
        overflow_display_names: Optional map of user_id -> resolved
            display name for waitlisted participants, rendered instead of a
            raw `<@id>` mention

    Returns:
        Tuple of (content, embed, view) where content contains role mentions
        (if any), the host mention, and confirmed participant mentions
    """
    formatter = GameMessageFormatter()

    config = get_config()
    thumbnail_url = None
    image_url = None

    if thumbnail_id:
        ext = _MIME_TO_EXT.get(thumbnail_mime_type or "", "")
        thumbnail_url = f"{config.backend_url}/api/v1/public/images/{thumbnail_id}{ext}"

    if banner_image_id:
        ext = _MIME_TO_EXT.get(banner_image_mime_type or "", "")
        image_url = f"{config.backend_url}/api/v1/public/images/{banner_image_id}{ext}"

    embed = formatter.create_game_embed(
        game_title=game_title,
        description=description,
        scheduled_at=scheduled_at,
        host_id=host_id,
        participant_ids=participant_ids,
        overflow_ids=overflow_ids,
        current_count=current_count,
        max_players=max_players,
        status=status,
        channel_id=channel_id,
        _signup_instructions=signup_instructions,
        expected_duration_minutes=expected_duration_minutes,
        where=where,
        game_id=game_id,
        host_display_name=host_display_name,
        host_avatar_url=host_avatar_url,
        thumbnail_url=thumbnail_url,
        image_url=image_url,
        rewards=rewards,
        overflow_display_names=overflow_display_names,
    )

    view = GameView.from_game_data(
        game_id=game_id,
        current_players=current_count,
        max_players=max_players,
        status=status,
        signup_method=signup_method,
    )

    # Format mentions for message content (appears above embed): roles, then
    # the host, then confirmed (non-waitlisted) participants with real Discord
    # IDs. Placeholder participants (display_name only, no Discord account)
    # are excluded since they have no ID to mention.
    mentions = []
    for role_id in notify_role_ids or []:
        # Special handling: @everyone uses literal string, not <@&guild_id>
        if guild_id and role_id == guild_id:
            mentions.append("@everyone")
        else:
            mentions.append(f"<@&{role_id}>")

    if host_id.isdigit():
        mentions.append(format_discord_mention(host_id))
    mentions.extend(
        format_discord_mention(uid) for uid in participant_ids if uid.isdigit() and uid != host_id
    )

    content = " ".join(mentions) if mentions else None

    return content, embed, view

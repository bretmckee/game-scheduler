"""Game session message formatter.

This module provides utilities for formatting Discord messages for game sessions,
including announcements, updates, and participant lists.
"""

from datetime import datetime

import discord

from services.bot.utils.discord_format import (
    format_discord_mention,
    format_discord_timestamp,
    format_game_status_emoji,
    format_participant_list,
    format_rules_section,
)
from services.bot.views.game_view import GameView


class GameMessageFormatter:
    """Formatter for game session Discord messages.

    Formats game announcements and updates with Discord native mentions,
    timestamps, and embedded content.
    """

    @staticmethod
    def create_game_embed(
        game_title: str,
        description: str,
        scheduled_at: datetime,
        host_id: str,
        participant_ids: list[str],
        current_count: int,
        max_players: int,
        status: str,
        rules: str | None = None,
        channel_id: str | None = None,
    ) -> discord.Embed:
        """Create an embed for a game session.

        Args:
            game_title: Game title
            description: Game description
            scheduled_at: When game is scheduled (UTC datetime)
            host_id: Discord ID of the game host
            participant_ids: List of participant Discord IDs
            current_count: Current participant count
            max_players: Maximum allowed participants
            status: Game status
            rules: Optional game rules
            channel_id: Optional Discord channel ID

        Returns:
            Configured Discord embed
        """
        status_emoji = format_game_status_emoji(status)
        embed = discord.Embed(
            title=f"{status_emoji} {game_title}",
            description=description,
            color=GameMessageFormatter._get_status_color(status),
            timestamp=scheduled_at,
        )

        embed.add_field(
            name="📅 When",
            value=f"{format_discord_timestamp(scheduled_at, 'F')}\n"
            f"({format_discord_timestamp(scheduled_at, 'R')})",
            inline=False,
        )

        embed.add_field(name="👥 Players", value=f"{current_count}/{max_players}", inline=True)

        embed.add_field(name="🎯 Host", value=format_discord_mention(host_id), inline=True)

        if channel_id:
            embed.add_field(name="📍 Voice Channel", value=f"<#{channel_id}>", inline=True)

        if participant_ids:
            embed.add_field(
                name="✅ Participants",
                value=format_participant_list(participant_ids, max_display=15),
                inline=False,
            )

        if rules:
            embed.add_field(
                name="📋 Rules", value=format_rules_section(rules, max_length=400), inline=False
            )

        embed.set_footer(text=f"Status: {status}")

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
            name="📅 Start Time", value=format_discord_timestamp(scheduled_at, "F"), inline=False
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
    current_count: int,
    max_players: int,
    status: str,
    rules: str | None = None,
    channel_id: str | None = None,
) -> tuple[discord.Embed, GameView]:
    """Format a complete game announcement with embed and buttons.

    Args:
        game_id: Game session UUID
        game_title: Game title
        description: Game description
        scheduled_at: When game is scheduled (UTC)
        host_id: Discord ID of game host
        participant_ids: List of participant Discord IDs
        current_count: Current participant count
        max_players: Maximum allowed participants
        status: Game status
        rules: Optional game rules
        channel_id: Optional voice channel ID

    Returns:
        Tuple of (embed, view) ready to send to Discord
    """
    formatter = GameMessageFormatter()

    embed = formatter.create_game_embed(
        game_title=game_title,
        description=description,
        scheduled_at=scheduled_at,
        host_id=host_id,
        participant_ids=participant_ids,
        current_count=current_count,
        max_players=max_players,
        status=status,
        rules=rules,
        channel_id=channel_id,
    )

    view = GameView.from_game_data(
        game_id=game_id,
        current_players=current_count,
        max_players=max_players,
        status=status,
    )

    return embed, view

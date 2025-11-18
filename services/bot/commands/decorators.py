"""Permission check decorators for Discord commands."""

import logging
from collections.abc import Callable
from functools import wraps

import discord
from discord import Interaction

logger = logging.getLogger(__name__)


def get_permissions(interaction: Interaction) -> discord.Permissions:
    """
    Get user permissions from interaction, preferring interaction permissions.

    Args:
        interaction: Discord interaction object

    Returns:
        User's permissions in the current context
    """
    if interaction.permissions and interaction.permissions.value != 0:
        return interaction.permissions

    member = interaction.user
    if isinstance(member, discord.Member):
        return member.guild_permissions

    return discord.Permissions.none()


def require_manage_guild() -> Callable:
    """
    Decorator to require MANAGE_GUILD permission for command execution.

    Returns:
        Decorator function that checks permissions before command execution
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            permissions = get_permissions(interaction)
            if not permissions.manage_guild:
                await interaction.response.send_message(
                    "❌ You need the **Manage Server** permission to use this command.",
                    ephemeral=True,
                )
                return

            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator


def require_manage_channels() -> Callable:
    """
    Decorator to require MANAGE_CHANNELS permission for command execution.

    Returns:
        Decorator function that checks permissions before command execution
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: Interaction, *args, **kwargs):
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True,
                )
                return

            permissions = get_permissions(interaction)
            if not permissions.manage_channels:
                await interaction.response.send_message(
                    "❌ You need the **Manage Channels** permission to use this command.",
                    ephemeral=True,
                )
                return

            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator


__all__ = ["require_manage_guild", "require_manage_channels"]

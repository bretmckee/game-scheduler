# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Permission check decorators for Discord commands."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

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


def _create_permission_decorator(permission_attr: str, permission_display_name: str) -> Callable:
    """
    Create a permission check decorator for Discord commands.

    Args:
        permission_attr: Permission attribute name (e.g., 'manage_guild')
        permission_display_name: Human-readable permission name for error messages

    Returns:
        Decorator function that checks permissions before command execution
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(interaction: Interaction, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            if not interaction.guild:
                await interaction.response.send_message(
                    "❌ This command can only be used in a server.",
                    ephemeral=True,
                )
                return None

            permissions = get_permissions(interaction)
            if not getattr(permissions, permission_attr):
                await interaction.response.send_message(
                    f"❌ You need the **{permission_display_name}** permission "
                    "to use this command.",
                    ephemeral=True,
                )
                return None

            return await func(interaction, *args, **kwargs)

        return wrapper

    return decorator


def require_manage_guild() -> Callable:
    """
    Decorator to require MANAGE_GUILD permission for command execution.

    Returns:
        Decorator function that checks permissions before command execution
    """
    return _create_permission_decorator("manage_guild", "Manage Server")


def require_manage_channels() -> Callable:
    """
    Decorator to require MANAGE_CHANNELS permission for command execution.

    Returns:
        Decorator function that checks permissions before command execution
    """
    return _create_permission_decorator("manage_channels", "Manage Channels")


__all__ = ["require_manage_channels", "require_manage_guild"]

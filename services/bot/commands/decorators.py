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

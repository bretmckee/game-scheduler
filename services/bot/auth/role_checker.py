"""Role verification service for Discord authorization."""

import logging
from typing import TYPE_CHECKING

import discord
from sqlalchemy import select

from services.bot.auth import cache as auth_cache
from services.bot.auth import permissions
from shared import database
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration

if TYPE_CHECKING:
    from discord import Guild, Member

logger = logging.getLogger(__name__)


class RoleChecker:
    """Service for checking user roles and permissions against configured requirements."""

    def __init__(self, bot: discord.Client):
        """
        Initialize role checker with bot instance.

        Args:
            bot: Discord bot client for API access
        """
        self.bot = bot

    async def get_member_roles(
        self, guild: "Guild", member: "Member", use_cache: bool = True
    ) -> list[str]:
        """
        Get user's role IDs from Discord API with optional caching.

        Args:
            guild: Discord guild
            member: Discord member
            use_cache: Whether to use Redis cache (default True)

        Returns:
            List of role IDs the user has in the guild
        """
        user_id = str(member.id)
        guild_id = str(guild.id)

        if use_cache:
            cache = await auth_cache.get_role_cache()
            cached_roles = await cache.get_user_roles(user_id, guild_id)
            if cached_roles is not None:
                return cached_roles

        role_ids = [str(role.id) for role in member.roles if role.id != guild.id]

        if use_cache:
            cache = await auth_cache.get_role_cache()
            await cache.set_user_roles(user_id, guild_id, role_ids)

        logger.debug(f"Fetched {len(role_ids)} roles for user {user_id} in guild {guild_id}")
        return role_ids

    async def invalidate_member_roles(self, guild: "Guild", member: "Member") -> None:
        """
        Invalidate cached role data for a member.

        Call this when roles change or critical operations need fresh data.

        Args:
            guild: Discord guild
            member: Discord member
        """
        cache = await auth_cache.get_role_cache()
        await cache.invalidate_user_roles(str(member.id), str(guild.id))
        logger.debug(f"Invalidated role cache for user {member.id} in guild {guild.id}")

    async def has_manage_guild_permission(self, member: "Member") -> bool:
        """
        Check if member has MANAGE_GUILD permission.

        Args:
            member: Discord member to check

        Returns:
            True if member has MANAGE_GUILD or ADMINISTRATOR permission
        """
        if not isinstance(member, discord.Member):
            return False

        perms = member.guild_permissions

        if perms.administrator:
            return True

        if perms.manage_guild:
            return True

        return False

    async def has_manage_channels_permission(self, member: "Member") -> bool:
        """
        Check if member has MANAGE_CHANNELS permission.

        Args:
            member: Discord member to check

        Returns:
            True if member has MANAGE_CHANNELS or ADMINISTRATOR permission
        """
        if not isinstance(member, discord.Member):
            return False

        perms = member.guild_permissions

        if perms.administrator:
            return True

        if perms.manage_channels:
            return True

        return False

    async def check_permission_from_roles(
        self,
        guild: "Guild",
        role_ids: list[str],
        required_permission: permissions.DiscordPermissions,
    ) -> bool:
        """
        Check if any of the user's roles grant a specific permission.

        Args:
            guild: Discord guild
            role_ids: List of role IDs to check
            required_permission: Permission flag to check for

        Returns:
            True if any role grants the permission
        """
        for role in guild.roles:
            if str(role.id) in role_ids:
                if permissions.has_permission(role.permissions.value, required_permission):
                    return True

        return False

    async def can_host_game(
        self,
        guild: "Guild",
        member: "Member",
        channel_id: str | None = None,
    ) -> bool:
        """
        Check if member can host games based on configured allowed roles.

        Checks channel-specific roles first, then guild roles, then MANAGE_GUILD permission.

        Args:
            guild: Discord guild
            member: Discord member to check
            channel_id: Optional channel ID for channel-specific role checks

        Returns:
            True if member is authorized to host games
        """
        guild_id = str(guild.id)

        async with database.get_db_session() as db:
            if channel_id:
                channel_config = await db.execute(
                    select(ChannelConfiguration).where(ChannelConfiguration.channelId == channel_id)
                )
                channel = channel_config.scalar_one_or_none()

                if channel and channel.allowedHostRoleIds:
                    member_roles = await self.get_member_roles(guild, member)
                    return any(role_id in channel.allowedHostRoleIds for role_id in member_roles)

            guild_config = await db.execute(
                select(GuildConfiguration).where(GuildConfiguration.guildId == guild_id)
            )
            guild_cfg = guild_config.scalar_one_or_none()

            if guild_cfg and guild_cfg.allowedHostRoleIds:
                member_roles = await self.get_member_roles(guild, member)
                return any(role_id in guild_cfg.allowedHostRoleIds for role_id in member_roles)

        return await self.has_manage_guild_permission(member)

    async def can_configure_guild(self, member: "Member") -> bool:
        """
        Check if member can configure guild settings.

        Requires MANAGE_GUILD or ADMINISTRATOR permission.

        Args:
            member: Discord member to check

        Returns:
            True if member is authorized to configure guild
        """
        return await self.has_manage_guild_permission(member)

    async def can_configure_channel(self, member: "Member") -> bool:
        """
        Check if member can configure channel settings.

        Requires MANAGE_CHANNELS or ADMINISTRATOR permission.

        Args:
            member: Discord member to check

        Returns:
            True if member is authorized to configure channel
        """
        return await self.has_manage_channels_permission(member)


# Global role checker instance
_role_checker: RoleChecker | None = None


def get_role_checker(bot: discord.Client) -> RoleChecker:
    """
    Get global role checker instance.

    Args:
        bot: Discord bot client

    Returns:
        Singleton RoleChecker instance
    """
    global _role_checker
    if _role_checker is None:
        _role_checker = RoleChecker(bot)
    return _role_checker

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


"""Database query functions for guild and channel configurations."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from shared.data_access.guild_isolation import (
    get_current_guild_ids,
    set_current_guild_ids,
)
from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration


async def get_guild_by_id(db: AsyncSession, guild_id: str) -> GuildConfiguration | None:
    """
    Fetch guild configuration by database UUID.

    Args:
        db: Database session
        guild_id: Database UUID

    Returns:
        Guild configuration or None if not found
    """
    result = await db.execute(select(GuildConfiguration).where(GuildConfiguration.id == guild_id))
    return result.scalar_one_or_none()


async def require_guild_by_id(
    db: AsyncSession,
    guild_id: str,
    access_token: str,
    user_discord_id: str,
    not_found_detail: str = "Guild configuration not found",
) -> GuildConfiguration:
    """
    Fetch guild configuration by UUID with automatic RLS context setup.

    Sets RLS context if not already set (idempotent). Returns 404 for both
    "not found" and "unauthorized" to prevent information disclosure.

    Args:
        db: Database session
        guild_id: Database UUID (GuildConfiguration.id)
        access_token: User's OAuth2 access token
        user_discord_id: User's Discord ID
        not_found_detail: Custom error message for 404 response

    Returns:
        Guild configuration (verified user has access)

    Raises:
        HTTPException(404): If guild not found OR user not authorized
    """
    from services.api.auth import oauth2

    # Ensure RLS context is set (idempotent - only fetches if not already set)
    if get_current_guild_ids() is None:
        user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
        guild_ids = [g["id"] for g in user_guilds]
        set_current_guild_ids(guild_ids)

    guild_config = await get_guild_by_id(db, guild_id)
    if not guild_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    # Defense in depth: Manual authorization check (RLS also enforces at DB level)
    authorized_guild_ids = get_current_guild_ids()
    if authorized_guild_ids is None or guild_config.guild_id not in authorized_guild_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=not_found_detail,
        )

    return guild_config


async def get_guild_by_discord_id(
    db: AsyncSession, guild_discord_id: str
) -> GuildConfiguration | None:
    """
    Fetch guild configuration by Discord guild ID.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID

    Returns:
        Guild configuration or None if not found
    """
    result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.guild_id == guild_discord_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_id(db: AsyncSession, channel_id: str) -> ChannelConfiguration | None:
    """
    Fetch channel configuration by database UUID with guild relationship.

    Args:
        db: Database session
        channel_id: Database UUID

    Returns:
        Channel configuration or None if not found
    """
    result = await db.execute(
        select(ChannelConfiguration)
        .options(selectinload(ChannelConfiguration.guild))
        .where(ChannelConfiguration.id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_channel_by_discord_id(
    db: AsyncSession, channel_discord_id: str
) -> ChannelConfiguration | None:
    """
    Fetch channel configuration by Discord channel ID with guild relationship.

    Args:
        db: Database session
        channel_discord_id: Discord channel snowflake ID

    Returns:
        Channel configuration or None if not found
    """
    result = await db.execute(
        select(ChannelConfiguration)
        .options(selectinload(ChannelConfiguration.guild))
        .where(ChannelConfiguration.channel_id == channel_discord_id)
    )
    return result.scalar_one_or_none()


async def get_channels_by_guild(db: AsyncSession, guild_id: str) -> list[ChannelConfiguration]:
    """
    Fetch all channels for a guild.

    Args:
        db: Database session
        guild_id: Guild configuration ID (UUID)

    Returns:
        List of channel configurations
    """
    result = await db.execute(
        select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild_id)
    )
    return list(result.scalars().all())

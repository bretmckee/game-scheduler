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


"""Guild configuration service for create and update operations."""

import asyncio
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.database import queries
from services.api.dependencies.discord import get_discord_client
from services.api.services import channel_service
from services.api.services import template_service as template_service_module
from shared.data_access.guild_isolation import get_current_guild_ids
from shared.discord.client import DiscordAPIClient
from shared.models.guild import GuildConfiguration


async def create_guild_config(
    db: AsyncSession,
    guild_discord_id: str,
    **settings: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Create new guild configuration.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.commit()
    await db.refresh(guild_config)
    return guild_config


async def update_guild_config(
    db: AsyncSession,
    guild_config: GuildConfiguration,
    **updates: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Update guild configuration.

    Args:
        db: Database session
        guild_config: Existing guild configuration
        **updates: Fields to update

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        setattr(guild_config, key, value)

    await db.commit()
    await db.refresh(guild_config)
    return guild_config


async def _compute_candidate_guild_ids(
    client: DiscordAPIClient,
    access_token: str,
    user_id: str,
) -> set[str]:
    """
    Compute candidate guild IDs: intersection of user admin guilds and bot guilds.

    Args:
        client: Discord API client
        access_token: User's OAuth2 access token
        user_id: Discord user ID

    Returns:
        Set of guild IDs where user has MANAGE_GUILD permission and bot is present
    """
    # Fetch user's guilds with MANAGE_GUILD permission
    user_guilds = await client.get_guilds(access_token, user_id)
    manage_guild = 0x00000020  # Permission bit for MANAGE_GUILD
    admin_guild_ids = {
        guild["id"] for guild in user_guilds if int(guild.get("permissions", 0)) & manage_guild
    }

    # Respect Discord rate limit (1 req/sec for /users/@me/guilds)
    await asyncio.sleep(1.1)

    # Fetch bot's current guilds
    bot_guilds = await client.get_guilds()
    bot_guild_ids = {guild["id"] for guild in bot_guilds}

    # Compute candidate guilds: (bot guilds ∩ user admin guilds)
    return admin_guild_ids & bot_guild_ids


async def _expand_rls_context_for_guilds(db: AsyncSession, candidate_guild_ids: set[str]) -> None:
    """
    Expand RLS context to include candidate guilds for query and insert operations.

    Args:
        db: Database session
        candidate_guild_ids: Set of guild IDs to include in RLS context
    """
    current_guild_ids = get_current_guild_ids() or []
    expanded_guild_ids = list(set(current_guild_ids) | candidate_guild_ids)
    expanded_ids_csv = ",".join(expanded_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{expanded_ids_csv}'"))


async def _get_existing_guild_ids(db: AsyncSession) -> set[str]:
    """
    Query existing guild IDs from database.

    Args:
        db: Database session

    Returns:
        Set of guild IDs that already exist in database
    """
    result = await db.execute(select(GuildConfiguration))
    existing_guilds = result.scalars().all()
    return {guild.guild_id for guild in existing_guilds}


async def _create_guild_with_channels_and_template(
    db: AsyncSession,
    client: DiscordAPIClient,
    guild_discord_id: str,
) -> tuple[int, int]:
    """
    Create guild configuration, channel configurations, and default template.

    Args:
        db: Database session
        client: Discord API client
        guild_discord_id: Discord guild snowflake ID

    Returns:
        Tuple of (guilds_created, channels_created) counts
    """
    # Create guild config
    guild_config = await create_guild_config(db, guild_discord_id)

    # Fetch guild channels using bot token
    guild_channels = await client.get_guild_channels(guild_discord_id)

    # Create channel configs for text channels
    text_channel = 0
    channels_created = 0
    for channel in guild_channels:
        if channel.get("type") == text_channel:
            await channel_service.create_channel_config(
                db, guild_config.id, channel["id"], is_active=True
            )
            channels_created += 1

    # Create default template for the guild using first text channel
    if guild_channels:
        first_channel = next((ch for ch in guild_channels if ch.get("type") == text_channel), None)
        if first_channel:
            # Get the created channel config UUID
            channel_config = await queries.get_channel_by_discord_id(db, first_channel["id"])
            if channel_config:
                template_svc = template_service_module.TemplateService(db)
                await template_svc.create_default_template(guild_config.id, channel_config.id)

    return (1, channels_created)


async def sync_user_guilds(db: AsyncSession, access_token: str, user_id: str) -> dict[str, int]:
    """
    Sync user's Discord guilds with database.

    Fetches user's guilds with MANAGE_GUILD permission and bot's guilds,
    then creates GuildConfiguration and ChannelConfiguration for new guilds.
    Creates default template for each new guild.

    Args:
        db: Database session
        access_token: User's OAuth2 access token
        user_id: Discord user ID

    Returns:
        Dictionary with counts: {
            "new_guilds": number of new guilds created,
            "new_channels": number of new channels created
        }
    """
    discord_client = get_discord_client()

    # Compute candidate guilds: (bot guilds ∩ user admin guilds)
    candidate_guild_ids = await _compute_candidate_guild_ids(discord_client, access_token, user_id)

    # Set RLS context to include ALL candidate guilds for query and insert
    await _expand_rls_context_for_guilds(db, candidate_guild_ids)

    # Query for existing guilds with proper RLS context set
    existing_guild_ids = await _get_existing_guild_ids(db)

    new_guild_ids = candidate_guild_ids - existing_guild_ids

    if not new_guild_ids:
        return {"new_guilds": 0, "new_channels": 0}

    # Create guild and channel configs for new guilds
    new_guilds_count = 0
    new_channels_count = 0

    for guild_discord_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(
            db, discord_client, guild_discord_id
        )
        new_guilds_count += guilds_created
        new_channels_count += channels_created

    return {"new_guilds": new_guilds_count, "new_channels": new_channels_count}

# Copyright 2026 Bret McKee
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


"""Bot guild sync service for automatic guild synchronization."""

from typing import Any

import discord
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.data_access import guild_queries
from shared.data_access.guild_isolation import (
    get_current_guild_ids,
    set_current_guild_ids,
)
from shared.discord.client import DiscordAPIClient
from shared.models.guild import GuildConfiguration


async def create_guild_config(
    db: AsyncSession,
    guild_discord_id: str,
    **settings: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Create new guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild_discord_id: Discord guild snowflake ID
        **settings: Additional configuration settings

    Returns:
        Created guild configuration
    """
    guild_config = GuildConfiguration(guild_id=guild_discord_id, **settings)
    db.add(guild_config)
    await db.flush()
    return guild_config


async def update_guild_config(
    guild_config: GuildConfiguration,
    **updates: Any,  # noqa: ANN401
) -> GuildConfiguration:
    """
    Update guild configuration.

    Does not commit. Caller must commit transaction.

    Args:
        guild_config: Existing guild configuration
        **updates: Fields to update

    Returns:
        Updated guild configuration
    """
    for key, value in updates.items():
        setattr(guild_config, key, value)
    return guild_config


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
    set_current_guild_ids(expanded_guild_ids)


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
    # Set RLS context to Discord snowflake ID for guild creation
    current_guild_ids = get_current_guild_ids() or []
    initial_guild_ids = list(set(current_guild_ids) | {guild_discord_id})
    initial_ids_csv = ",".join(initial_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{initial_ids_csv}'"))
    set_current_guild_ids(initial_guild_ids)

    # Create guild config
    guild_config = await create_guild_config(db, guild_discord_id)

    # Update RLS context to include the new guild UUID (for template creation)
    current_guild_ids = get_current_guild_ids() or []
    updated_guild_ids = list(set(current_guild_ids) | {str(guild_config.id)})
    updated_ids_csv = ",".join(updated_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{updated_ids_csv}'"))
    set_current_guild_ids(updated_guild_ids)

    # Fetch guild channels using bot token
    guild_channels = await client.get_guild_channels(guild_discord_id)

    # Create channel configs for text, voice, and announcement channels
    # Discord channel types: 0=text, 2=voice, 5=announcement
    supported_channel_types = {0, 2, 5}

    channels_created = 0
    for channel in guild_channels:
        if channel.get("type") in supported_channel_types:
            await guild_queries.create_channel_config(
                db, guild_config.id, channel["id"], is_active=True
            )
            channels_created += 1

    # Create default template for the guild using first text channel
    if guild_channels:
        first_channel = next((ch for ch in guild_channels if ch.get("type") == 0), None)
        if first_channel:
            # Get the created channel config UUID
            channel_config = await guild_queries.get_channel_by_discord_id(db, first_channel["id"])
            if channel_config:
                await guild_queries.create_default_template(db, guild_config.id, channel_config.id)

    return (1, channels_created)


async def _refresh_guild_channels(
    db: AsyncSession, discord_client: DiscordAPIClient, guild_discord_id: str
) -> int:
    """
    Refresh channels for an existing guild from Discord.

    Fetches channels from Discord API and updates database:
    - Creates new channel records for new channels
    - Marks deleted channels as inactive
    - Reactivates previously inactive channels that reappear

    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        discord_client: Discord API client
        guild_discord_id: Discord guild ID (snowflake)

    Returns:
        Number of channels modified (created, activated, or deactivated)
    """
    # Get guild configuration to find database UUID
    guild_result = await db.execute(
        select(GuildConfiguration).where(GuildConfiguration.guild_id == guild_discord_id)
    )
    guild = guild_result.scalar_one_or_none()
    if not guild:
        return 0

    # Fetch channels from Discord
    discord_channels = await discord_client.get_guild_channels(guild_discord_id)

    # Filter for text, voice, and announcement channels (types 0, 2, 5)
    supported_channel_types = {0, 2, 5}
    discord_text_channel_ids = {
        ch["id"] for ch in discord_channels if ch.get("type") in supported_channel_types
    }

    # Get existing channels from database
    channels_result = await db.execute(
        text(
            "SELECT id, channel_id, is_active FROM channel_configurations "
            "WHERE guild_id = :guild_id"
        ),
        {"guild_id": str(guild.id)},
    )
    existing_channels = {
        row[1]: {"id": row[0], "is_active": row[2]} for row in channels_result.fetchall()
    }

    modified_count = 0

    # Add new channels or reactivate existing ones
    for channel_discord_id in discord_text_channel_ids:
        if channel_discord_id in existing_channels:
            channel_info = existing_channels[channel_discord_id]
            if not channel_info["is_active"]:
                # Reactivate channel
                await db.execute(
                    text("UPDATE channel_configurations SET is_active = true WHERE id = :id"),
                    {"id": str(channel_info["id"])},
                )
                modified_count += 1
        else:
            # Create new channel
            await guild_queries.create_channel_config(
                db, str(guild.id), channel_discord_id, is_active=True
            )
            modified_count += 1

    # Mark missing channels as inactive
    for channel_discord_id, channel_info in existing_channels.items():
        if channel_discord_id not in discord_text_channel_ids and channel_info["is_active"]:
            await db.execute(
                text("UPDATE channel_configurations SET is_active = false WHERE id = :id"),
                {"id": str(channel_info["id"])},
            )
            modified_count += 1

    return modified_count


async def sync_all_bot_guilds(
    discord_client: DiscordAPIClient, db: AsyncSession, bot_token: str
) -> dict[str, int]:
    """
    Sync all bot guilds using bot token (no user authentication required).

    Fetches all guilds the bot is present in and creates new guild configurations
    with channels and default templates. Refreshes channels for existing guilds.

    Does not commit. Caller must commit transaction.

    Args:
        discord_client: Discord API client
        db: Database session
        bot_token: Discord bot token

    Returns:
        Dictionary with counts: {
            "new_guilds": number of new guilds created,
            "new_channels": number of new channels created
        }
    """
    # Fetch all bot guilds using bot token
    bot_guilds = await discord_client.get_guilds(token=bot_token)
    bot_guild_ids = {guild["id"] for guild in bot_guilds}

    # Expand RLS context to include all bot guild IDs
    await _expand_rls_context_for_guilds(db, bot_guild_ids)

    # Query existing guild IDs from database
    existing_guild_ids = await _get_existing_guild_ids(db)

    # Compute new guilds (bot guilds - existing guilds)
    new_guild_ids = bot_guild_ids - existing_guild_ids

    new_guilds_count = 0
    new_channels_count = 0

    # Create guild and channel configs for new guilds
    for guild_id in new_guild_ids:
        guilds_created, channels_created = await _create_guild_with_channels_and_template(
            db, discord_client, guild_id
        )
        new_guilds_count += guilds_created
        new_channels_count += channels_created

    return {
        "new_guilds": new_guilds_count,
        "new_channels": new_channels_count,
    }


async def _create_guild_with_gateway_channels(
    db: AsyncSession,
    guild: discord.Guild,
) -> tuple[int, int]:
    """
    Create guild configuration and channel configs using gateway-supplied channel data.

    Uses guild.channels directly from the in-memory cache — no REST calls.
    Does not commit. Caller must commit transaction.

    Args:
        db: Database session
        guild: discord.Guild object from the gateway

    Returns:
        Tuple of (guilds_created, channels_created) counts
    """
    guild_discord_id = str(guild.id)

    current_guild_ids = get_current_guild_ids() or []
    initial_guild_ids = list(set(current_guild_ids) | {guild_discord_id})
    initial_ids_csv = ",".join(initial_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{initial_ids_csv}'"))
    set_current_guild_ids(initial_guild_ids)

    guild_config = await create_guild_config(db, guild_discord_id)

    current_guild_ids = get_current_guild_ids() or []
    updated_guild_ids = list(set(current_guild_ids) | {str(guild_config.id)})
    updated_ids_csv = ",".join(updated_guild_ids)
    await db.execute(text(f"SET LOCAL app.current_guild_ids = '{updated_ids_csv}'"))
    set_current_guild_ids(updated_guild_ids)

    supported_channel_types = {0, 2, 5}
    channels_created = 0
    first_text_channel_discord_id: str | None = None

    for channel in guild.channels:
        channel_type = channel.type.value
        if channel_type in supported_channel_types:
            await guild_queries.create_channel_config(
                db, guild_config.id, str(channel.id), is_active=True
            )
            channels_created += 1
            if channel_type == 0 and first_text_channel_discord_id is None:
                first_text_channel_discord_id = str(channel.id)

    if first_text_channel_discord_id:
        channel_config = await guild_queries.get_channel_by_discord_id(
            db, first_text_channel_discord_id
        )
        if channel_config:
            await guild_queries.create_default_template(db, guild_config.id, channel_config.id)

    return (1, channels_created)


async def sync_guilds_from_gateway(bot: discord.Client, db: AsyncSession) -> dict[str, int]:
    """
    Sync all bot guilds using gateway-supplied data without REST calls.

    Iterates bot.guilds (populated by the gateway) and creates configurations
    for any guild not already in the database. Uses guild.channels directly
    from the in-memory cache — no REST calls.

    Does not commit. Caller must commit transaction.

    Args:
        bot: Discord bot client with populated guild cache
        db: Database session

    Returns:
        Dictionary with counts: {"new_guilds": ..., "new_channels": ...}
    """
    bot_guild_ids = {str(guild.id) for guild in bot.guilds}

    await _expand_rls_context_for_guilds(db, bot_guild_ids)

    existing_guild_ids = await _get_existing_guild_ids(db)

    new_guild_ids = bot_guild_ids - existing_guild_ids

    new_guilds_count = 0
    new_channels_count = 0

    for guild in bot.guilds:
        if str(guild.id) in new_guild_ids:
            guilds_created, channels_created = await _create_guild_with_gateway_channels(db, guild)
            new_guilds_count += guilds_created
            new_channels_count += channels_created

    return {
        "new_guilds": new_guilds_count,
        "new_channels": new_channels_count,
    }


async def sync_single_guild_from_gateway(guild: discord.Guild, db: AsyncSession) -> dict[str, int]:
    """
    Sync a single guild using the gateway-supplied guild object.

    Used by on_guild_join where the guild object is already available from
    the event. Creates guild config and channels using guild.channels from
    the gateway — no REST calls.

    Does not commit. Caller must commit transaction.

    Args:
        guild: Discord Guild object from a gateway event
        db: Database session

    Returns:
        Dictionary with counts: {"new_guilds": ..., "new_channels": ...}
    """
    guild_discord_id = str(guild.id)

    await _expand_rls_context_for_guilds(db, {guild_discord_id})

    existing_guild_ids = await _get_existing_guild_ids(db)

    if guild_discord_id in existing_guild_ids:
        return {"new_guilds": 0, "new_channels": 0}

    guilds_created, channels_created = await _create_guild_with_gateway_channels(db, guild)

    return {
        "new_guilds": guilds_created,
        "new_channels": channels_created,
    }

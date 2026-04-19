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


"""Background task for refreshing display names at login time."""

import logging

from sqlalchemy import select

from services.api.database.queries import setup_rls_and_convert_guild_ids
from services.api.services.user_display_names import UserDisplayNameService
from shared.cache import client as cache_client
from shared.cache import keys as cache_keys
from shared.cache import projection as member_projection
from shared.cache import ttl as cache_ttl
from shared.data_access.guild_isolation import clear_current_guild_ids
from shared.database import AsyncSessionLocal
from shared.models.guild import GuildConfiguration

logger = logging.getLogger(__name__)


def _resolve_member_display_name(member: dict) -> str:
    return member.get("nick") or member.get("global_name") or member["username"]


async def _build_guild_entry(
    user_discord_id: str,
    guild_config: GuildConfiguration,
    redis: cache_client.RedisClient,
) -> dict | None:
    """
    Read projection for one guild and build a display-name entry dict.

    Also caches the user's role IDs for the guild. Returns None if the
    member is absent from the projection.
    """
    member = await member_projection.get_member(guild_config.guild_id, user_discord_id, redis=redis)
    if member is None:
        logger.info(
            "refresh_display_name_on_login: guild %s user %s absent from projection",
            guild_config.guild_id,
            user_discord_id,
        )
        return None

    role_ids = list(member.get("roles", []))
    if guild_config.guild_id not in role_ids:
        role_ids.append(guild_config.guild_id)
    await redis.set_json(
        cache_keys.CacheKeys.user_roles(user_discord_id, guild_config.guild_id),
        role_ids,
        ttl=cache_ttl.CacheTTL.USER_ROLES,
    )

    return {
        "user_discord_id": user_discord_id,
        "guild_discord_id": guild_config.guild_id,
        "display_name": _resolve_member_display_name(member),
        "avatar_url": member.get("avatar_url"),
    }


async def refresh_display_name_on_login(
    user_discord_id: str,
) -> None:
    """
    Refresh the logged-in user's display name across all bot-registered guilds.

    Runs as a FastAPI background task after the OAuth callback so it does not
    block the login response. Reads member data from the Redis projection written
    by the Discord bot, making zero Discord REST calls.
    """
    logger.info("refresh_display_name_on_login: started for user %s", user_discord_id)
    try:
        redis = await cache_client.get_redis_client()
        discord_guild_ids = await member_projection.get_user_guilds(user_discord_id, redis=redis)
        if discord_guild_ids is None:
            logger.info(
                "refresh_display_name_on_login: user %s absent from projection, skipping",
                user_discord_id,
            )
            return

        async with AsyncSessionLocal() as db:
            await setup_rls_and_convert_guild_ids(db, discord_guild_ids)
            result = await db.execute(select(GuildConfiguration))
            guilds = result.scalars().all()

            logger.info(
                "refresh_display_name_on_login: found %d guild(s) for user %s",
                len(guilds),
                user_discord_id,
            )

            if not guilds:
                return

            entries = []

            for guild_config in guilds:
                logger.info(
                    "refresh_display_name_on_login: reading projection for guild %s user %s",
                    guild_config.guild_id,
                    user_discord_id,
                )
                entry = await _build_guild_entry(user_discord_id, guild_config, redis)
                if entry is not None:
                    entries.append(entry)

            logger.info(
                "refresh_display_name_on_login: upserting %d entries for user %s",
                len(entries),
                user_discord_id,
            )
            service = UserDisplayNameService(db=db)
            await service.upsert_batch(entries)
            await db.commit()
            logger.info("refresh_display_name_on_login: completed for user %s", user_discord_id)
    except Exception:
        logger.exception(
            "refresh_display_name_on_login: unhandled error for user %s", user_discord_id
        )
    finally:
        clear_current_guild_ids()

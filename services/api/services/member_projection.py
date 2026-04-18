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


"""API-side reader for the Discord member projection stored in Redis."""

import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from opentelemetry import metrics

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys

logger = logging.getLogger(__name__)
meter = metrics.get_meter(__name__)

_read_retry_counter = meter.create_counter(
    name="api.projection.read.retries",
    description="Number of gen-rotation retries during projection reads",
    unit="1",
)
_read_not_found_counter = meter.create_counter(
    name="api.projection.read.not_found",
    description="Number of stable-gen misses during projection reads",
    unit="1",
)

_MAX_GEN_RETRIES = 3
_BOT_FRESHNESS_SECONDS = 120


async def _read_with_gen_retry(
    redis: RedisClient, key_fn: Callable[..., str], *key_args: str
) -> str | None:
    """
    Read a projection key with generation-rotation retry.

    Handles the window where the gen pointer has flipped to a new value but
    the caller's key was constructed with the old value. Retries up to
    _MAX_GEN_RETRIES times before giving up.

    Args:
        redis: Redis async client wrapper
        key_fn: Key factory function (e.g., CacheKeys.proj_member)
        *key_args: Arguments to pass to key_fn after the gen argument

    Returns:
        Cached value string, or None if absent
    """
    gen = await redis.get(CacheKeys.proj_gen())
    for _ in range(_MAX_GEN_RETRIES):
        value = await redis.get(key_fn(gen, *key_args))
        if value is not None:
            return value
        gen2 = await redis.get(CacheKeys.proj_gen())
        if gen == gen2:
            _read_not_found_counter.add(1)
            return None
        _read_retry_counter.add(1)
        gen = gen2
    return None


async def get_user_guilds(uid: str, *, redis: RedisClient) -> list[str] | None:
    """
    Get the list of guild IDs the user belongs to from the projection.

    Args:
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        List of guild ID strings, or None if absent
    """
    raw = await _read_with_gen_retry(redis, CacheKeys.proj_user_guilds, uid)
    if raw is None:
        return None
    return json.loads(raw)


async def get_member(guild_id: str, uid: str, *, redis: RedisClient) -> dict | None:
    """
    Get member data for a user in a guild from the projection.

    Args:
        guild_id: Discord guild ID
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        Member dict with keys: roles, nick, global_name, username, avatar_url;
        or None if absent
    """
    raw = await _read_with_gen_retry(redis, CacheKeys.proj_member, guild_id, uid)
    if raw is None:
        return None
    return json.loads(raw)


async def get_user_roles(guild_id: str, uid: str, *, redis: RedisClient) -> list[str]:
    """
    Get the role IDs for a user in a guild from the projection.

    Args:
        guild_id: Discord guild ID
        uid: Discord user ID
        redis: Redis async client wrapper

    Returns:
        List of role ID strings, empty list if member absent
    """
    member = await get_member(guild_id, uid, redis=redis)
    if member is None:
        return []
    return member.get("roles", [])


async def get_guild_name(guild_id: str, *, redis: RedisClient) -> str | None:
    """
    Get the guild name from the projection.

    Args:
        guild_id: Discord guild ID
        redis: Redis async client wrapper

    Returns:
        Guild name string, or None if absent
    """
    return await _read_with_gen_retry(redis, CacheKeys.proj_guild_name, guild_id)


async def is_bot_fresh(*, redis: RedisClient) -> bool:
    """
    Check whether the bot projection is fresh (bot heartbeat recently seen).

    Args:
        redis: Redis async client wrapper

    Returns:
        True if bot:last_seen key exists and timestamp is within acceptable age
    """
    raw = await redis.get(CacheKeys.bot_last_seen())
    if raw is None:
        return False
    try:
        last_seen = datetime.fromisoformat(raw)
        age = datetime.now(UTC) - last_seen
        return age < timedelta(seconds=_BOT_FRESHNESS_SECONDS)
    except ValueError:
        return False

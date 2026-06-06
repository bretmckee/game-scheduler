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


"""Bot-side projection writer and reader for Discord member data from gateway events."""

import json
import logging
from collections.abc import Iterable
from datetime import UTC, datetime

import discord
from opentelemetry import metrics
from redis.asyncio.client import Pipeline

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.cache.operations import read_projection_key


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
    raw = await read_projection_key(redis, CacheKeys.proj_member, guild_id, uid)
    if raw is None:
        return []
    return json.loads(raw).get("roles", [])


logger = logging.getLogger(__name__)
meter = metrics.get_meter(__name__)

repopulation_started_counter = meter.create_counter(
    name="bot.projection.repopulation.started",
    description="Number of projection repopulation cycles started",
    unit="1",
)
repopulation_duration_gauge = meter.create_gauge(
    name="bot.projection.repopulation.duration",
    description="Duration of projection repopulation in seconds",
    unit="s",
)
repopulation_members_written_gauge = meter.create_gauge(
    name="bot.projection.repopulation.members_written",
    description="Number of members written in projection repopulation",
    unit="{member}",
)
repopulation_coalesced_counter = meter.create_counter(
    name="bot.projection.repopulation.coalesced",
    description="Number of repopulation triggers dropped because one was already pending",
    unit="1",
)


async def _delete_old_generation(redis: RedisClient, prev_gen: str) -> None:
    """Delete all projection keys from the previous generation.

    Collects all matching keys via SCAN first, then deletes in a single pipeline
    to avoid one round-trip per key batch.
    """
    pattern = f"proj:*:{prev_gen}:*"
    all_keys: list[bytes] = []
    cursor = 0
    while True:
        cursor, keys = await redis._client.scan(cursor, match=pattern, count=500)
        all_keys.extend(keys)
        if cursor == 0:
            break
    if not all_keys:
        return
    async with redis._client.pipeline(transaction=False) as pipe:
        for i in range(0, len(all_keys), 1000):
            pipe.delete(*all_keys[i : i + 1000])
        await pipe.execute()


def _build_member_data(member: discord.Member) -> dict[str, object]:
    return {
        "roles": [str(role.id) for role in member.roles],
        "nick": member.nick,
        "global_name": member.global_name,
        "username": member.name,
        "avatar_url": member.avatar.url if member.avatar else None,
    }


def _member_username_variants(member: discord.Member) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for name in [member.name, member.global_name, member.nick]:
        if not name:
            continue
        lower = name.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(lower)
    return result


def _queue_member_to_pipe(
    pipe: Pipeline,
    gen: str,
    guild_id: str,
    uid: str,
    member: discord.Member,
) -> None:
    """Queue a single member write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_member(gen, guild_id, uid)
    pipe.set(key, json.dumps(_build_member_data(member)))

    usernames_key = CacheKeys.proj_usernames(gen, guild_id)
    for name_lower in _member_username_variants(member):
        pipe.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})


def _queue_user_guilds_to_pipe(
    pipe: Pipeline,
    gen: str,
    uid: str,
    guild_ids: list[str],
) -> None:
    """Queue a user-guilds write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_user_guilds(gen, uid)
    pipe.set(key, json.dumps(guild_ids))


def _queue_guild_name_to_pipe(
    pipe: Pipeline,
    gen: str,
    guild_id: str,
    guild_name: str,
) -> None:
    """Queue a guild-name write into a Redis pipeline buffer (synchronous)."""
    key = CacheKeys.proj_guild_name(gen, guild_id)
    pipe.set(key, guild_name)


async def _write_all_members(
    bot: discord.Client,
    redis: RedisClient,
    new_gen: str,
) -> tuple[int, dict[str, list[str]]]:
    """Write all member records and accumulate user->guild mapping via a single pipeline.

    Returns:
        Tuple of (total_members_written, user_guild_map)
    """
    user_guild_map: dict[str, list[str]] = {}
    total_members_written = 0

    async with redis._client.pipeline(transaction=False) as pipe:
        for guild in bot.guilds:
            guild_id = str(guild.id)
            _queue_guild_name_to_pipe(pipe, new_gen, guild_id, guild.name)
            for member in guild.members:
                uid = str(member.id)
                _queue_member_to_pipe(pipe, new_gen, guild_id, uid, member)
                total_members_written += 1
                user_guild_map.setdefault(uid, []).append(guild_id)

        for uid, guild_ids in user_guild_map.items():
            _queue_user_guilds_to_pipe(pipe, new_gen, uid, guild_ids)

        await pipe.execute()

    return total_members_written, user_guild_map


async def repopulate_all(
    *,
    bot: discord.Client,
    redis: RedisClient,
) -> None:
    """
    Repopulate entire member projection from bot gateway cache.

    Writes all member and user_guilds keys, then atomically flips the generation
    pointer to signal visibility. Old generation keys are cleaned up after the flip.

    Args:
        bot: Discord bot instance with guild cache
        redis: Redis async client
    """
    start_time = datetime.now(UTC)

    new_gen = str(int(datetime.now(UTC).timestamp() * 1000))
    prev_gen = await redis.get(CacheKeys.proj_gen())

    total_members_written, _ = await _write_all_members(bot, redis, new_gen)

    # CRITICAL: Flip generation pointer AFTER all writes are complete.
    # Readers observing the new gen value are guaranteed to find all data present.
    await redis.set(CacheKeys.proj_gen(), new_gen)

    # Mark bot as fresh immediately — projection is now fully populated.
    # Without this, is_bot_fresh() returns False until the heartbeat task fires
    # (up to 30 seconds after on_ready), causing membership checks to deny access.
    await write_bot_last_seen(redis=redis)

    write_duration = (datetime.now(UTC) - start_time).total_seconds()
    repopulation_duration_gauge.set(write_duration)
    repopulation_members_written_gauge.set(total_members_written)

    logger.info(
        "Projection repopulation complete: %d members, %.2fs",
        total_members_written,
        write_duration,
    )

    if prev_gen:
        delete_start = datetime.now(UTC)
        await _delete_old_generation(redis, prev_gen)
        delete_duration = (datetime.now(UTC) - delete_start).total_seconds()
        logger.info("Projection old-gen cleanup: %.2fs, gen=%s", delete_duration, prev_gen)


async def write_member(
    *,
    redis: RedisClient,
    gen: str,
    guild_id: str,
    uid: str,
    member: discord.Member,
) -> None:
    """
    Write a single member record to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        guild_id: Discord guild ID
        uid: Discord user ID
        member: Discord Member object

    Raises:
        NotImplementedError: Function not yet implemented
    """
    key = CacheKeys.proj_member(gen, guild_id, uid)
    await redis.set_json(key, _build_member_data(member), ttl=None)

    usernames_key = CacheKeys.proj_usernames(gen, guild_id)
    for name_lower in _member_username_variants(member):
        await redis._client.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})


async def write_user_guilds(
    *,
    redis: RedisClient,
    gen: str,
    uid: str,
    guild_ids: list[str],
) -> None:
    """
    Write the user's guild list to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        uid: Discord user ID
        guild_ids: List of guild IDs the user is in

    Raises:
        NotImplementedError: Function not yet implemented
    """
    key = CacheKeys.proj_user_guilds(gen, uid)
    await redis.set_json(key, guild_ids, ttl=None)


async def write_guild_name(
    *,
    redis: RedisClient,
    gen: str,
    guild_id: str,
    guild_name: str,
) -> None:
    """
    Write a guild name to the projection.

    Args:
        redis: Redis async client
        gen: Generation pointer value
        guild_id: Discord guild ID
        guild_name: Guild name to store
    """
    key = CacheKeys.proj_guild_name(gen, guild_id)
    await redis.set(key, guild_name, ttl=None)


async def update_member(
    gen: str,
    member_before: discord.Member,
    member_after: discord.Member,
    *,
    redis: RedisClient,
) -> None:
    """Update a single member record in the current generation using an atomic pipeline.

    Writes the member key with after-state data. If username variants changed,
    ZADDs the new variants and ZREMs the dropped ones on the sorted set.
    Does not change the generation pointer.

    Args:
        gen: Current generation pointer value
        member_before: Member state before the update
        member_after: Member state after the update
        redis: Redis async client
    """
    guild_id = str(member_after.guild.id)
    uid = str(member_after.id)

    old_variants = set(_member_username_variants(member_before))
    new_variants = set(_member_username_variants(member_after))

    member_key = CacheKeys.proj_member(gen, guild_id, uid)
    usernames_key = CacheKeys.proj_usernames(gen, guild_id)

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.set(member_key, json.dumps(_build_member_data(member_after)))
        if old_variants != new_variants:
            for name_lower in new_variants - old_variants:
                pipe.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})
            for name_lower in old_variants - new_variants:
                pipe.zrem(usernames_key, f"{name_lower}\x00{uid}")
        await pipe.execute()


async def add_member(gen: str, member: discord.Member, *, redis: RedisClient) -> None:
    """Add a new member to the projection incrementally using an atomic pipeline.

    Writes the member key, appends the guild to the user's guild list, and ZADDs
    all username variants. Does not change the generation pointer.

    Args:
        gen: Current generation pointer value
        member: The new Discord member
        redis: Redis async client
    """
    guild_id = str(member.guild.id)
    uid = str(member.id)

    raw = await redis.get(CacheKeys.proj_user_guilds(gen, uid))
    current_guilds: list[str] = json.loads(raw) if raw else []
    if guild_id not in current_guilds:
        current_guilds.append(guild_id)

    member_key, guilds_key, usernames_key = _member_projection_keys(gen, guild_id, uid)

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.set(member_key, json.dumps(_build_member_data(member)))
        pipe.set(guilds_key, json.dumps(current_guilds))
        for name_lower in _member_username_variants(member):
            pipe.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})
        await pipe.execute()


async def remove_member(gen: str, member: discord.Member, *, redis: RedisClient) -> None:
    """Remove a member from the projection incrementally using an atomic pipeline.

    Deletes the member key, removes the guild from the user's guild list, and ZREMs
    all username variants. Does not change the generation pointer.

    Args:
        gen: Current generation pointer value
        member: The Discord member being removed
        redis: Redis async client
    """
    guild_id = str(member.guild.id)
    uid = str(member.id)

    raw = await redis.get(CacheKeys.proj_user_guilds(gen, uid))
    current_guilds: list[str] = json.loads(raw) if raw else []
    updated_guilds = [g for g in current_guilds if g != guild_id]

    member_key, guilds_key, usernames_key = _member_projection_keys(gen, guild_id, uid)

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        pipe.delete(member_key)
        pipe.set(guilds_key, json.dumps(updated_guilds))
        for name_lower in _member_username_variants(member):
            pipe.zrem(usernames_key, f"{name_lower}\x00{uid}")
        await pipe.execute()


def _member_projection_keys(gen: str, guild_id: str, uid: str) -> tuple[str, str, str]:
    """Return the three projection keys for a single guild member."""
    return (
        CacheKeys.proj_member(gen, guild_id, uid),
        CacheKeys.proj_user_guilds(gen, uid),
        CacheKeys.proj_usernames(gen, guild_id),
    )


def _user_global_variants(user: discord.User) -> list[str]:
    """Return lowercased, deduplicated name variants for a User (username and global_name only).

    Mirrors _member_username_variants but takes a discord.User. Nick is guild-scoped
    and is not available on the User object.
    """
    seen: set[str] = set()
    result: list[str] = []
    for name in [user.name, user.global_name]:
        if not name:
            continue
        lower = name.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(lower)
    return result


async def update_user(
    gen: str,
    user_before: discord.User,
    user_after: discord.User,
    bot_guilds: Iterable[discord.Guild],
    *,
    redis: RedisClient,
) -> None:
    """Update member records and username sorted sets for all guilds when a User changes.

    Returns early without touching Redis when the indexed name variants (username and
    global_name) are unchanged — avatar-only changes don't need projection writes.

    For each guild where the user is a member, writes the member key with after-state
    data and ZADDs/ZREMs only the changed username variants.

    Args:
        gen: Current generation pointer value
        user_before: User state before the update
        user_after: User state after the update
        bot_guilds: All guilds known to the bot
        redis: Redis async client
    """
    old_variants = set(_user_global_variants(user_before))
    new_variants = set(_user_global_variants(user_after))

    if old_variants == new_variants:
        return

    uid = str(user_after.id)
    added_variants = new_variants - old_variants
    removed_variants = old_variants - new_variants

    async with redis._client.pipeline(transaction=True) as pipe:
        pipe.multi()
        for guild in bot_guilds:
            member = guild.get_member(user_after.id)
            if member is None:
                continue
            guild_id = str(guild.id)
            pipe.set(
                CacheKeys.proj_member(gen, guild_id, uid),
                json.dumps(_build_member_data(member)),
            )
            usernames_key = CacheKeys.proj_usernames(gen, guild_id)
            for name_lower in added_variants:
                pipe.zadd(usernames_key, {f"{name_lower}\x00{uid}": 0})
            for name_lower in removed_variants:
                pipe.zrem(usernames_key, f"{name_lower}\x00{uid}")
        await pipe.execute()


async def write_bot_last_seen(
    *,
    redis: RedisClient,
    heartbeat_interval: int = 30,
) -> None:
    """
    Write bot heartbeat timestamp.

    Args:
        redis: Redis async client
        heartbeat_interval: Heartbeat interval in seconds

    Raises:
        NotImplementedError: Function not yet implemented
    """
    timestamp = datetime.now(UTC).isoformat()
    ttl = heartbeat_interval * 3
    key = CacheKeys.bot_last_seen()
    await redis.set(key, timestamp, ttl=ttl)

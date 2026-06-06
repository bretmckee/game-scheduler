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


"""Integration tests for guild projection write functions against a real Redis instance."""

import json
import os
from unittest.mock import MagicMock

import discord
import pytest

from services.bot import guild_projection
from shared.cache import client as cache_module
from shared.cache.keys import CacheKeys
from shared.cache.projection import search_members_by_prefix

pytestmark = pytest.mark.integration


def _make_mock_member(
    uid: int,
    name: str,
    global_name: str | None = None,
    nick: str | None = None,
    role_ids: list[int] | None = None,
) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.id = uid
    member.name = name
    member.global_name = global_name
    member.nick = nick
    member.roles = [MagicMock(id=rid) for rid in (role_ids or [])]
    member.avatar = None
    return member


def _make_mock_guild(guild_id: int, name: str, members: list[MagicMock]) -> MagicMock:
    guild = MagicMock(spec=discord.Guild)
    guild.id = guild_id
    guild.name = name
    guild.members = members
    return guild


def _make_mock_bot(guilds: list[MagicMock]) -> MagicMock:
    bot = MagicMock(spec=discord.Client)
    bot.guilds = guilds
    return bot


@pytest.fixture
async def redis() -> cache_module.RedisClient:
    """Async Redis client connected to the integration test Redis instance."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = cache_module.RedisClient(redis_url=redis_url)
    await client.connect()
    yield client
    await client.disconnect()


@pytest.fixture
def two_guild_bot() -> MagicMock:
    """Mock Discord bot with 2 guilds (3 members each, member_3 in both guilds)."""
    guild_a_members = [
        _make_mock_member(1001, "alice", global_name="Alice Smith", nick="ali", role_ids=[9001]),
        _make_mock_member(1002, "bob", global_name="Bob Jones", nick=None, role_ids=[9002]),
        _make_mock_member(1003, "shared_user", global_name="Shared One", nick="shared"),
    ]
    guild_b_members = [
        _make_mock_member(2001, "carol", global_name="Carol White", nick=None),
        _make_mock_member(2002, "dave", global_name="Dave Black", nick="davey"),
        _make_mock_member(1003, "shared_user", global_name="Shared One", nick="shared"),
    ]
    guild_a = _make_mock_guild(111, "Guild Alpha", guild_a_members)
    guild_b = _make_mock_guild(222, "Guild Beta", guild_b_members)
    return _make_mock_bot([guild_a, guild_b])


@pytest.mark.asyncio
async def test_repopulate_all_sets_gen_pointer(
    redis: cache_module.RedisClient, two_guild_bot: MagicMock
) -> None:
    """repopulate_all writes a new, non-empty proj:gen that differs from the seed value."""
    old_gen = await redis.get(CacheKeys.proj_gen())

    await guild_projection.repopulate_all(bot=two_guild_bot, redis=redis)

    new_gen = await redis.get(CacheKeys.proj_gen())
    assert new_gen is not None
    assert new_gen != ""
    assert new_gen != old_gen


@pytest.mark.asyncio
async def test_repopulate_all_writes_member_keys(
    redis: cache_module.RedisClient, two_guild_bot: MagicMock
) -> None:
    """repopulate_all writes proj:member keys for every guild/member pair with required fields."""
    await guild_projection.repopulate_all(bot=two_guild_bot, redis=redis)
    gen = await redis.get(CacheKeys.proj_gen())
    assert gen is not None

    guild_a_id = "111"
    guild_b_id = "222"

    for uid, guild_id in [
        ("1001", guild_a_id),
        ("1002", guild_a_id),
        ("1003", guild_a_id),
        ("2001", guild_b_id),
        ("2002", guild_b_id),
        ("1003", guild_b_id),
    ]:
        raw = await redis._client.get(CacheKeys.proj_member(gen, guild_id, uid))
        assert raw is not None, f"Missing proj:member for guild={guild_id} uid={uid}"
        data = json.loads(raw)
        for field in ("roles", "nick", "global_name", "username", "avatar_url"):
            assert field in data, f"Missing field '{field}' for guild={guild_id} uid={uid}"


@pytest.mark.asyncio
async def test_repopulate_all_writes_user_guilds(
    redis: cache_module.RedisClient, two_guild_bot: MagicMock
) -> None:
    """repopulate_all writes proj:user_guilds for a member present in both guilds."""
    await guild_projection.repopulate_all(bot=two_guild_bot, redis=redis)
    gen = await redis.get(CacheKeys.proj_gen())
    assert gen is not None

    raw = await redis._client.get(CacheKeys.proj_user_guilds(gen, "1003"))
    assert raw is not None
    guild_ids = json.loads(raw)
    assert "111" in guild_ids
    assert "222" in guild_ids


@pytest.mark.asyncio
async def test_repopulate_all_writes_username_sorted_set(
    redis: cache_module.RedisClient, two_guild_bot: MagicMock
) -> None:
    """repopulate_all writes all non-empty name variants into proj:usernames sorted sets."""
    await guild_projection.repopulate_all(bot=two_guild_bot, redis=redis)
    gen = await redis.get(CacheKeys.proj_gen())
    assert gen is not None

    guild_a_key = CacheKeys.proj_usernames(gen, "111")
    entries_raw = await redis._client.zrangebylex(guild_a_key, "-", "+")
    entries = {e.rsplit("\x00", 1)[0] for e in entries_raw}

    assert "alice" in entries
    assert "alice smith" in entries
    assert "ali" in entries
    assert "bob" in entries
    assert "bob jones" in entries
    assert "shared_user" in entries
    assert "shared one" in entries
    assert "shared" in entries


@pytest.mark.asyncio
async def test_repopulate_all_search_returns_member(
    redis: cache_module.RedisClient, two_guild_bot: MagicMock
) -> None:
    """search_members_by_prefix finds the correct member after repopulate_all."""
    await guild_projection.repopulate_all(bot=two_guild_bot, redis=redis)

    results = await search_members_by_prefix("111", "ali", redis=redis)

    assert len(results) >= 1
    uids = [r["uid"] for r in results]
    assert "1001" in uids
    matched = next(r for r in results if r["uid"] == "1001")
    assert matched["username"] == "alice"
    assert matched["global_name"] == "Alice Smith"

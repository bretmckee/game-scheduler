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


"""Unit tests for incremental projection update functions."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.bot import GameSchedulerBot
from services.bot.guild_projection import update_member
from shared.cache.keys import CacheKeys


def _make_pipeline_mock() -> MagicMock:
    """Return a mock pipeline that records synchronous queue calls and supports await execute()."""
    pipe = MagicMock()
    pipe.multi = MagicMock()
    pipe.set = MagicMock()
    pipe.zadd = MagicMock()
    pipe.zrem = MagicMock()
    pipe.execute = AsyncMock()
    return pipe


def _make_redis_mock(pipe: MagicMock) -> MagicMock:
    """Return a mock RedisClient whose _client.pipeline() yields the given pipe."""
    redis = MagicMock()

    @asynccontextmanager
    async def _pipeline_ctx(transaction: bool = False):
        yield pipe

    redis._client.pipeline = _pipeline_ctx
    return redis


def _make_member(
    uid: int,
    name: str,
    global_name: str | None,
    nick: str | None,
    role_ids: list[int],
    guild_id: int = 111,
) -> MagicMock:
    member = MagicMock(spec=discord.Member)
    member.id = uid
    member.name = name
    member.global_name = global_name
    member.nick = nick
    member.roles = [MagicMock(id=rid) for rid in role_ids]
    member.avatar = None
    guild = MagicMock()
    guild.id = guild_id
    member.guild = guild
    return member


class TestUpdateMember:
    """update_member writes incremental pipeline ops for a member change."""

    @pytest.mark.asyncio
    async def test_always_writes_member_key(self) -> None:
        """update_member always sets the proj:member key with after-state data."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        before = _make_member(1001, "alice", "Alice Smith", "ali", [9001])
        after = _make_member(1001, "alice", "Alice Smith", "ali", [9001, 9002])

        await update_member("gen1", before, after, redis=redis)

        expected_key = CacheKeys.proj_member("gen1", "111", "1001")
        pipe.set.assert_called_once()
        actual_key, actual_val = pipe.set.call_args[0]
        assert actual_key == expected_key
        data = json.loads(actual_val)
        role_ids = data["roles"]
        assert "9001" in role_ids
        assert "9002" in role_ids

    @pytest.mark.asyncio
    async def test_skips_sorted_set_ops_when_names_unchanged(self) -> None:
        """When username variants are identical, zadd and zrem are not called."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        before = _make_member(1001, "alice", "Alice Smith", "ali", [9001])
        after = _make_member(1001, "alice", "Alice Smith", "ali", [9001, 9002])

        await update_member("gen1", before, after, redis=redis)

        pipe.zadd.assert_not_called()
        pipe.zrem.assert_not_called()

    @pytest.mark.asyncio
    async def test_adds_new_variants_when_nick_added(self) -> None:
        """When a nick is added, the new nick variant is zadd-ed."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        before = _make_member(1001, "alice", "Alice Smith", None, [9001])
        after = _make_member(1001, "alice", "Alice Smith", "ally", [9001])

        await update_member("gen1", before, after, redis=redis)

        usernames_key = CacheKeys.proj_usernames("gen1", "111")
        zadd_calls = pipe.zadd.call_args_list
        assert len(zadd_calls) >= 1
        added_entries: set[str] = set()
        for call in zadd_calls:
            assert call[0][0] == usernames_key
            added_entries.update(call[0][1].keys())
        assert "ally\x001001" in added_entries

    @pytest.mark.asyncio
    async def test_removes_dropped_variants_when_nick_removed(self) -> None:
        """When a nick is removed, the old nick variant is zrem-ed."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        before = _make_member(1001, "alice", "Alice Smith", "ali", [9001])
        after = _make_member(1001, "alice", "Alice Smith", None, [9001])

        await update_member("gen1", before, after, redis=redis)

        usernames_key = CacheKeys.proj_usernames("gen1", "111")
        zrem_calls = pipe.zrem.call_args_list
        assert len(zrem_calls) >= 1
        removed_entries: set[str] = set()
        for call in zrem_calls:
            assert call[0][0] == usernames_key
            removed_entries.update(call[0][1:])
        assert "ali\x001001" in removed_entries

    @pytest.mark.asyncio
    async def test_executes_pipeline(self) -> None:
        """update_member always awaits pipe.execute()."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        before = _make_member(1001, "alice", "Alice Smith", "ali", [9001])
        after = _make_member(1001, "alice", "Alice Smith", "ali", [9002])

        await update_member("gen1", before, after, redis=redis)

        pipe.execute.assert_awaited_once()


def _make_bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    instance = GameSchedulerBot.__new__(GameSchedulerBot)
    instance.config = cfg
    instance.button_handler = None
    instance.event_handlers = None
    instance.event_publisher = None
    instance.api_cache = None
    instance._sweep_task = None
    instance._refresh_listener_started = True
    return instance


class TestOnMemberUpdateHandler:
    """on_member_update calls update_member with the current gen."""

    @pytest.mark.asyncio
    async def test_calls_update_member_with_current_gen(self) -> None:
        """on_member_update fetches gen and delegates to guild_projection.update_member."""
        bot = _make_bot()
        before = MagicMock(spec=discord.Member)
        after = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="gen42")

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.update_member", new_callable=AsyncMock
            ) as mock_update,
        ):
            await bot.on_member_update(before, after)

        mock_update.assert_awaited_once_with("gen42", before, after, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_returns_early_when_gen_is_none(self) -> None:
        """on_member_update does nothing when proj:gen is absent (projection not yet populated)."""
        bot = _make_bot()
        before = MagicMock(spec=discord.Member)
        after = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.update_member", new_callable=AsyncMock
            ) as mock_update,
        ):
            await bot.on_member_update(before, after)

        mock_update.assert_not_awaited()

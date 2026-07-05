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
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

from services.bot.bot import GameSchedulerBot
from services.bot.guild_projection import (
    _user_global_variants,
    add_member,
    remove_member,
    update_member,
    update_user,
)
from shared.cache.keys import CacheKeys


def _make_pipeline_mock() -> MagicMock:
    """Return a mock pipeline that records synchronous queue calls and supports await execute()."""
    pipe = MagicMock()
    pipe.multi = MagicMock()
    pipe.set = MagicMock()
    pipe.zadd = MagicMock()
    pipe.zrem = MagicMock()
    pipe.delete = MagicMock()
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


class TestOnUserUpdateHandler:
    """on_user_update delegates to guild_projection.update_user with the current gen."""

    @pytest.mark.asyncio
    async def test_calls_update_user_with_current_gen(self) -> None:
        """on_user_update fetches gen and delegates to guild_projection.update_user."""
        bot = _make_bot()
        before = MagicMock(spec=discord.User)
        after = MagicMock(spec=discord.User)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="gen99")

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.update_user", new_callable=AsyncMock
            ) as mock_update,
            patch.object(type(bot), "guilds", new_callable=PropertyMock, return_value=[]),
        ):
            await bot.on_user_update(before, after)

        mock_update.assert_awaited_once_with("gen99", before, after, ANY, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_returns_early_when_gen_is_none(self) -> None:
        """on_user_update does nothing when proj:gen is absent."""
        bot = _make_bot()
        before = MagicMock(spec=discord.User)
        after = MagicMock(spec=discord.User)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.update_user", new_callable=AsyncMock
            ) as mock_update,
        ):
            await bot.on_user_update(before, after)

        mock_update.assert_not_awaited()


class TestUserGlobalVariants:
    """_user_global_variants returns deduped lowercase name and global_name."""

    def test_returns_username_and_global_name(self) -> None:
        """Both username and global_name appear when distinct."""
        user = MagicMock(spec=discord.User)
        user.name = "alice"
        user.global_name = "Alice Smith"

        result = _user_global_variants(user)

        assert "alice" in result
        assert "alice smith" in result

    def test_deduplicates_when_global_name_equals_username(self) -> None:
        """Only one entry when global_name lowercases to same value as username."""
        user = MagicMock(spec=discord.User)
        user.name = "sameuser"
        user.global_name = "SameUser"

        result = _user_global_variants(user)

        assert result.count("sameuser") == 1

    def test_skips_none_global_name(self) -> None:
        """Only username is returned when global_name is None."""
        user = MagicMock(spec=discord.User)
        user.name = "onlyuser"
        user.global_name = None

        result = _user_global_variants(user)

        assert result == ["onlyuser"]


class TestUpdateUser:
    """update_user writes incremental pipeline ops across all guilds the user is in."""

    def _make_guild_with_member(self, guild_id: int, uid: int) -> MagicMock:
        member = _make_member(uid, "alice", "Alice Smith", "ali", [9001], guild_id=guild_id)
        guild = MagicMock(spec=discord.Guild)
        guild.id = guild_id
        guild.get_member = MagicMock(return_value=member)
        return guild

    @pytest.mark.asyncio
    async def test_returns_early_when_variants_unchanged(self) -> None:
        """update_user does nothing when username and global_name are the same."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        user_before = MagicMock(spec=discord.User)
        user_before.name = "alice"
        user_before.global_name = "Alice Smith"
        user_after = MagicMock(spec=discord.User)
        user_after.name = "alice"
        user_after.global_name = "Alice Smith"
        user_after.id = 1001

        await update_user("gen1", user_before, user_after, [], redis=redis)

        pipe.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_updates_member_key_in_each_guild(self) -> None:
        """update_user sets proj:member in every guild where the user is a member."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        user_before = MagicMock(spec=discord.User)
        user_before.name = "alice"
        user_before.global_name = "Alice Old"
        user_after = MagicMock(spec=discord.User)
        user_after.name = "alice"
        user_after.global_name = "Alice New"
        user_after.id = 1001

        guild_a = self._make_guild_with_member(111, 1001)
        guild_b = self._make_guild_with_member(222, 1001)

        await update_user("gen1", user_before, user_after, [guild_a, guild_b], redis=redis)

        set_keys = [call[0][0] for call in pipe.set.call_args_list]
        assert CacheKeys.proj_member("gen1", "111", "1001") in set_keys
        assert CacheKeys.proj_member("gen1", "222", "1001") in set_keys

    @pytest.mark.asyncio
    async def test_skips_guilds_where_user_not_member(self) -> None:
        """Guilds where get_member returns None are skipped."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        user_before = MagicMock(spec=discord.User)
        user_before.name = "alice"
        user_before.global_name = "Old"
        user_after = MagicMock(spec=discord.User)
        user_after.name = "alice"
        user_after.global_name = "New"
        user_after.id = 1001

        guild_present = self._make_guild_with_member(111, 1001)
        guild_absent = MagicMock(spec=discord.Guild)
        guild_absent.id = 222
        guild_absent.get_member = MagicMock(return_value=None)

        await update_user(
            "gen1", user_before, user_after, [guild_present, guild_absent], redis=redis
        )

        set_keys = [call[0][0] for call in pipe.set.call_args_list]
        assert CacheKeys.proj_member("gen1", "111", "1001") in set_keys
        assert not any("222" in k for k in set_keys)

    @pytest.mark.asyncio
    async def test_zadds_new_global_name_and_zrems_old(self) -> None:
        """When global_name changes, new variant zadd-ed and old variant zrem-ed."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        user_before = MagicMock(spec=discord.User)
        user_before.name = "alice"
        user_before.global_name = "Alice Old"
        user_after = MagicMock(spec=discord.User)
        user_after.name = "alice"
        user_after.global_name = "Alice New"
        user_after.id = 1001

        guild = self._make_guild_with_member(111, 1001)

        await update_user("gen1", user_before, user_after, [guild], redis=redis)

        usernames_key = CacheKeys.proj_usernames("gen1", "111")
        added: set[str] = set()
        for call in pipe.zadd.call_args_list:
            if call[0][0] == usernames_key:
                added.update(call[0][1].keys())
        assert "alice new\x001001" in added

        removed: set[str] = set()
        for call in pipe.zrem.call_args_list:
            if call[0][0] == usernames_key:
                removed.update(call[0][1:])
        assert "alice old\x001001" in removed

    @pytest.mark.asyncio
    async def test_executes_pipeline(self) -> None:
        """update_user awaits pipe.execute() when variants changed."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)

        user_before = MagicMock(spec=discord.User)
        user_before.name = "alice"
        user_before.global_name = "Old Name"
        user_after = MagicMock(spec=discord.User)
        user_after.name = "alice"
        user_after.global_name = "New Name"
        user_after.id = 1001

        guild = self._make_guild_with_member(111, 1001)

        await update_user("gen1", user_before, user_after, [guild], redis=redis)

        pipe.execute.assert_awaited_once()


class TestAddMember:
    """add_member writes member key, user_guilds, and username variants atomically."""

    @pytest.mark.asyncio
    async def test_writes_member_key(self) -> None:
        """add_member sets the proj:member key with member data."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=None)

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await add_member("gen1", member, redis=redis)

        set_keys = [call[0][0] for call in pipe.set.call_args_list]
        assert CacheKeys.proj_member("gen1", "111", "1001") in set_keys

    @pytest.mark.asyncio
    async def test_appends_guild_to_user_guilds(self) -> None:
        """add_member appends the new guild_id to proj:user_guilds."""

        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=json.dumps(["999"]))

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await add_member("gen1", member, redis=redis)

        set_calls = {call[0][0]: call[0][1] for call in pipe.set.call_args_list}
        guilds_key = CacheKeys.proj_user_guilds("gen1", "1001")
        assert guilds_key in set_calls
        guilds = json.loads(set_calls[guilds_key])
        assert "111" in guilds
        assert "999" in guilds

    @pytest.mark.asyncio
    async def test_zadds_username_variants(self) -> None:
        """add_member ZADDs all username variants into the sorted set."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=None)

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await add_member("gen1", member, redis=redis)

        usernames_key = CacheKeys.proj_usernames("gen1", "111")
        added: set[str] = set()
        for call in pipe.zadd.call_args_list:
            if call[0][0] == usernames_key:
                added.update(call[0][1].keys())
        assert "alice\x001001" in added
        assert "alice smith\x001001" in added
        assert "ali\x001001" in added

    @pytest.mark.asyncio
    async def test_executes_pipeline(self) -> None:
        """add_member always awaits pipe.execute()."""
        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=None)

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await add_member("gen1", member, redis=redis)

        pipe.execute.assert_awaited_once()


class TestRemoveMember:
    """remove_member deletes member key, updates user_guilds, and removes username variants."""

    @pytest.mark.asyncio
    async def test_deletes_member_key(self) -> None:
        """remove_member deletes the proj:member key."""

        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=json.dumps(["111"]))

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await remove_member("gen1", member, redis=redis)

        deleted_keys = [call[0][0] for call in pipe.delete.call_args_list]
        assert CacheKeys.proj_member("gen1", "111", "1001") in deleted_keys

    @pytest.mark.asyncio
    async def test_removes_guild_from_user_guilds(self) -> None:
        """remove_member removes the guild_id from proj:user_guilds."""

        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=json.dumps(["111", "222"]))

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await remove_member("gen1", member, redis=redis)

        set_calls = {call[0][0]: call[0][1] for call in pipe.set.call_args_list}
        guilds_key = CacheKeys.proj_user_guilds("gen1", "1001")
        assert guilds_key in set_calls
        guilds = json.loads(set_calls[guilds_key])
        assert "111" not in guilds
        assert "222" in guilds

    @pytest.mark.asyncio
    async def test_zrems_username_variants(self) -> None:
        """remove_member ZREMs all username variants from the sorted set."""

        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=json.dumps(["111"]))

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await remove_member("gen1", member, redis=redis)

        usernames_key = CacheKeys.proj_usernames("gen1", "111")
        removed: set[str] = set()
        for call in pipe.zrem.call_args_list:
            if call[0][0] == usernames_key:
                removed.update(call[0][1:])
        assert "alice\x001001" in removed
        assert "alice smith\x001001" in removed
        assert "ali\x001001" in removed

    @pytest.mark.asyncio
    async def test_executes_pipeline(self) -> None:
        """remove_member always awaits pipe.execute()."""

        pipe = _make_pipeline_mock()
        redis = _make_redis_mock(pipe)
        redis.get = AsyncMock(return_value=json.dumps(["111"]))

        member = _make_member(1001, "alice", "Alice Smith", "ali", [9001])

        await remove_member("gen1", member, redis=redis)

        pipe.execute.assert_awaited_once()


class TestOnMemberAddHandler:
    """on_member_add delegates to guild_projection.add_member with the current gen."""

    @pytest.mark.asyncio
    async def test_calls_add_member_with_current_gen(self) -> None:
        """on_member_add fetches gen and delegates to guild_projection.add_member."""
        bot = _make_bot()
        member = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="gen7")

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.add_member", new_callable=AsyncMock
            ) as mock_add,
        ):
            await bot.on_member_add(member)

        mock_add.assert_awaited_once_with("gen7", member, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_returns_early_when_gen_is_none(self) -> None:
        """on_member_add does nothing when proj:gen is absent."""
        bot = _make_bot()
        member = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.add_member", new_callable=AsyncMock
            ) as mock_add,
        ):
            await bot.on_member_add(member)

        mock_add.assert_not_awaited()


class TestOnMemberRemoveHandler:
    """on_member_remove delegates to guild_projection.remove_member with the current gen."""

    @pytest.mark.asyncio
    async def test_calls_remove_member_with_current_gen(self) -> None:
        """on_member_remove fetches gen and delegates to guild_projection.remove_member."""
        bot = _make_bot()
        member = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="gen8")

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.remove_member", new_callable=AsyncMock
            ) as mock_remove,
        ):
            await bot.on_member_remove(member)

        mock_remove.assert_awaited_once_with("gen8", member, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_returns_early_when_gen_is_none(self) -> None:
        """on_member_remove does nothing when proj:gen is absent."""
        bot = _make_bot()
        member = MagicMock(spec=discord.Member)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with (
            patch(
                "services.bot.bot.get_redis_client", new_callable=AsyncMock, return_value=mock_redis
            ),
            patch(
                "services.bot.bot.guild_projection.remove_member", new_callable=AsyncMock
            ) as mock_remove,
        ):
            await bot.on_member_remove(member)

        mock_remove.assert_not_awaited()

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


"""Unit tests for AnnouncementLoop."""

import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.announcement_loop import AnnouncementLoop
from shared.models.game import GameSession


def _db_ctx(mock_db=None):
    if mock_db is None:
        mock_db = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_db)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return mock_db, ctx


async def test_announcement_loop_process_due_announces_due_games() -> None:
    """_process_due calls _announce for each game with past post_at and no message_id."""
    game_id = "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"
    mock_db, ctx = _db_ctx()

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [game_id]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute = AsyncMock(return_value=mock_result)

    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with (
        patch("services.bot.announcement_loop.get_db_session", return_value=ctx),
        patch.object(loop, "_announce", new=AsyncMock()) as mock_announce,
    ):
        await loop._process_due()

    mock_announce.assert_awaited_once_with(game_id)


async def test_announcement_loop_skips_already_announced_games() -> None:
    """_announce returns early when re-query finds game already announced (message_id set)."""
    game_id = "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"
    mock_db, ctx = _db_ctx()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    bot = MagicMock()
    bot.event_handlers = MagicMock()
    bot.event_handlers._get_bot_channel = AsyncMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with patch("services.bot.announcement_loop.get_db_session", return_value=ctx):
        await loop._announce(game_id)

    bot.event_handlers._get_bot_channel.assert_not_called()


async def test_announcement_loop_announce_posts_to_discord_and_sets_message_id() -> None:
    """_announce posts to Discord, sets message_id, and calls _setup_game_schedules."""
    game_id = "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"

    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.message_id = None
    game.channel.channel_id = "111222333444"
    game.reminder_minutes = [60, 15]
    game.expected_duration_minutes = 120

    mock_message = MagicMock()
    mock_message.id = 99999

    mock_channel = AsyncMock()
    mock_channel.send = AsyncMock(return_value=mock_message)

    bot = MagicMock()
    bot.event_handlers._get_bot_channel = AsyncMock(return_value=mock_channel)
    bot.event_handlers._create_game_announcement = AsyncMock(
        return_value=(None, MagicMock(), MagicMock())
    )

    fresh_game = MagicMock()
    fresh_game.reminder_minutes = [60, 15]
    fresh_game.expected_duration_minutes = 120

    mock_db, ctx = _db_ctx()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = game
    mock_db.execute = AsyncMock(return_value=mock_result)

    loop = AnnouncementLoop("postgresql://test", bot)

    mock_setup_schedules = AsyncMock()

    with (
        patch("services.bot.announcement_loop.get_db_session", return_value=ctx),
        patch(
            "services.bot.announcement_loop.setup_game_schedules",
            mock_setup_schedules,
        ),
    ):
        await loop._announce(game_id)

    assert game.message_id == "99999"
    mock_setup_schedules.assert_awaited_once_with(
        db=mock_db,
        game=game,
        reminder_minutes=[60, 15],
    )


async def test_announcement_loop_on_notify_sets_wake_event() -> None:
    """_on_notify wakes the loop by setting the wake event."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)
    loop._wake_event = asyncio.Event()
    assert not loop._wake_event.is_set()

    loop._on_notify(MagicMock(), 1234, "game_announcement_changed", "")

    assert loop._wake_event.is_set()


async def test_announcement_loop_next_due_time_returns_scalar() -> None:
    """_next_due_time queries the DB and returns the min post_at."""
    expected = datetime.datetime(2099, 1, 1, tzinfo=datetime.UTC).replace(tzinfo=None)
    mock_db, ctx = _db_ctx()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected
    mock_db.execute = AsyncMock(return_value=mock_result)

    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with patch("services.bot.announcement_loop.get_db_session", return_value=ctx):
        result = await loop._next_due_time()

    assert result == expected


async def test_announcement_loop_start_closes_connection_on_cancel() -> None:
    """start() closes the asyncpg connection when cancelled."""
    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()
    mock_conn.close = AsyncMock()

    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    call_count = 0

    async def fake_process_due() -> None:
        nonlocal call_count
        call_count += 1
        raise asyncio.CancelledError

    with (
        patch(
            "services.bot.announcement_loop.asyncpg.connect", new=AsyncMock(return_value=mock_conn)
        ),
        patch.object(loop, "_process_due", side_effect=fake_process_due),
    ):
        with pytest.raises(asyncio.CancelledError):
            await loop.start()

    mock_conn.close.assert_awaited_once()


async def test_announcement_loop_start_logs_sleep_and_wake() -> None:
    """start() logs the sleep duration and wake reason during a normal iteration."""
    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()
    mock_conn.close = AsyncMock()

    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    process_calls = 0

    async def fake_process_due() -> None:
        nonlocal process_calls
        process_calls += 1
        if process_calls >= 2:
            raise asyncio.CancelledError

    async def fake_wait_for(coro: object, timeout: float) -> None:
        if hasattr(coro, "close"):
            coro.close()

    with (
        patch(
            "services.bot.announcement_loop.asyncpg.connect",
            new=AsyncMock(return_value=mock_conn),
        ),
        patch.object(loop, "_process_due", side_effect=fake_process_due),
        patch.object(loop, "_next_due_time", new=AsyncMock(return_value=None)),
        patch(
            "services.bot.announcement_loop.asyncio.wait_for",
            side_effect=fake_wait_for,
        ),
    ):
        with pytest.raises(asyncio.CancelledError):
            await loop.start()

    assert process_calls == 2


async def test_announcement_loop_start_retries_after_transient_error() -> None:
    """start() catches non-CancelledError exceptions and retries the loop iteration."""
    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()
    mock_conn.close = AsyncMock()

    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    process_calls = 0

    async def fake_process_due() -> None:
        nonlocal process_calls
        process_calls += 1
        if process_calls == 1:
            msg = "transient DB error"
            raise RuntimeError(msg)
        raise asyncio.CancelledError

    with (
        patch(
            "services.bot.announcement_loop.asyncpg.connect",
            new=AsyncMock(return_value=mock_conn),
        ),
        patch.object(loop, "_process_due", side_effect=fake_process_due),
    ):
        with pytest.raises(asyncio.CancelledError):
            await loop.start()

    assert process_calls == 2


async def test_announcement_loop_announce_logs_error_when_channel_not_found() -> None:
    """_announce logs an error and returns when the Discord channel cannot be found."""
    game_id = "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"

    game = MagicMock(spec=GameSession)
    game.id = game_id
    game.channel.channel_id = "nonexistent"

    mock_db, ctx = _db_ctx()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = game
    mock_db.execute = AsyncMock(return_value=mock_result)

    bot = MagicMock()
    bot.event_handlers._get_bot_channel = AsyncMock(return_value=None)

    loop = AnnouncementLoop("postgresql://test", bot)

    with (
        patch("services.bot.announcement_loop.get_db_session", return_value=ctx),
        patch("services.bot.announcement_loop.logger") as mock_logger,
    ):
        await loop._announce(game_id)

    mock_logger.error.assert_called_once_with(
        "Channel not found for deferred game announcement: game=%s", game_id
    )
    bot.event_handlers._create_game_announcement.assert_not_called()

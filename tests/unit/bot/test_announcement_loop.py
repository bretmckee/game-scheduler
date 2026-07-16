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


async def _blocks_forever(*_args: object, **_kwargs: object) -> None:
    """Stand in for a real listener that runs until cancelled.

    Must be an ``async def`` (not a plain lambda returning a coroutine object)
    so AsyncMock's side_effect machinery actually awaits it — a lambda that
    merely returns ``asyncio.Event().wait()`` without awaiting it leaves that
    coroutine object unawaited, which pytest reports as a failure.
    """
    await asyncio.Event().wait()


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


async def test_start_delegates_to_listen_with_reconnect() -> None:
    """start() delegates connection lifecycle to listen_with_reconnect."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with patch(
        "services.bot.announcement_loop.listen_with_reconnect",
        new_callable=AsyncMock,
    ) as mock_listen:
        task = asyncio.create_task(loop.start())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    args = mock_listen.call_args[0]
    assert args[0] == loop._db_url
    assert args[1] == "game_announcement_changed"
    assert args[2] == loop._on_notify


async def test_announcement_loop_start_closes_connection_on_cancel() -> None:
    """Cancelling start()'s task raises CancelledError after the loop body has run."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with (
        patch(
            "services.bot.announcement_loop.listen_with_reconnect",
            new=AsyncMock(side_effect=_blocks_forever),
        ),
        patch.object(loop, "_process_due", new_callable=AsyncMock) as mock_process_due,
    ):
        task = asyncio.create_task(loop.start())
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    mock_process_due.assert_awaited()


async def test_announcement_loop_start_logs_sleep_and_wake() -> None:
    """start()'s loop body logs the sleep duration and wake reason each iteration."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    with (
        patch(
            "services.bot.announcement_loop.listen_with_reconnect",
            new=AsyncMock(side_effect=_blocks_forever),
        ),
        patch.object(loop, "_process_due", new_callable=AsyncMock),
        patch.object(loop, "_next_due_time", new=AsyncMock(return_value=None)),
        patch("services.bot.announcement_loop.logger") as mock_logger,
    ):
        task = asyncio.create_task(loop.start())
        # _run_loop clears _wake_event before waiting, so let it reach the
        # wait_for suspension first, then set the event from here to simulate
        # a NOTIFY arriving mid-wait, then give it turns to log "woke up".
        for _ in range(3):
            await asyncio.sleep(0)
        loop._wake_event.set()
        for _ in range(3):
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_logger.debug.assert_any_call("AnnouncementLoop sleeping %.1fs (next_due=%s)", 3600.0, None)
    mock_logger.debug.assert_any_call("AnnouncementLoop woke up (reason=%s)", "notify")


async def test_announcement_loop_start_retries_after_transient_error() -> None:
    """start() catches non-CancelledError exceptions and retries the loop iteration."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    process_calls = 0

    async def fake_process_due() -> None:
        nonlocal process_calls
        process_calls += 1
        if process_calls == 1:
            msg = "transient DB error"
            raise RuntimeError(msg)

    # Captured before patching asyncio.sleep below: patch() replaces the real,
    # process-wide asyncio module's sleep attribute (announcement_loop.py does
    # `import asyncio`, not `from asyncio import sleep`), so the driver's own
    # yields below must go through this real reference or they'd be mocked too.
    real_sleep = asyncio.sleep

    with (
        patch(
            "services.bot.announcement_loop.listen_with_reconnect",
            new=AsyncMock(side_effect=_blocks_forever),
        ),
        patch.object(loop, "_process_due", side_effect=fake_process_due),
        patch.object(loop, "_next_due_time", new=AsyncMock(return_value=None)),
        patch("services.bot.announcement_loop.logger") as mock_logger,
        patch("services.bot.announcement_loop.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        task = asyncio.create_task(loop.start())
        await real_sleep(0)
        await real_sleep(0)
        await real_sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert process_calls == 2
    mock_logger.exception.assert_called_once_with(
        "AnnouncementLoop: error in loop iteration, retrying"
    )
    mock_sleep.assert_any_call(1.0)


async def test_announcement_loop_start_clamps_wait_to_max_timeout() -> None:
    """_run_loop clamps the sleep duration to MAX_TIMEOUT even when next_due is further out."""
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    far_future = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
        hours=2
    )

    with (
        patch(
            "services.bot.announcement_loop.listen_with_reconnect",
            new=AsyncMock(side_effect=_blocks_forever),
        ),
        patch.object(loop, "_process_due", new_callable=AsyncMock),
        patch.object(loop, "_next_due_time", new=AsyncMock(return_value=far_future)),
        patch("services.bot.announcement_loop.logger") as mock_logger,
    ):
        task = asyncio.create_task(loop.start())
        for _ in range(3):
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_logger.debug.assert_any_call(
        "AnnouncementLoop sleeping %.1fs (next_due=%s)", 3600.0, far_future
    )


async def test_announcement_loop_start_survives_two_consecutive_exceptions() -> None:
    """_run_loop survives a second consecutive exception, proving no outer catch swallows it.

    Before this migration, any exception escaping the loop body (e.g. from a
    dropped connection) would hit the now-removed outer
    ``try/except Exception: logger.exception("AnnouncementLoop failed...")``
    and start() would return silently for good. With that outer catch gone,
    the per-iteration try/except must be the only thing standing between an
    error and a dead loop — proving it survives twice in a row (not just
    once) confirms it lives inside ``while True:``.
    """
    bot = MagicMock()
    loop = AnnouncementLoop("postgresql://test", bot)

    process_calls = 0

    async def fake_process_due() -> None:
        nonlocal process_calls
        process_calls += 1
        if process_calls <= 2:
            msg = f"transient DB error {process_calls}"
            raise RuntimeError(msg)

    real_sleep = asyncio.sleep

    with (
        patch(
            "services.bot.announcement_loop.listen_with_reconnect",
            new=AsyncMock(side_effect=_blocks_forever),
        ),
        patch.object(loop, "_process_due", side_effect=fake_process_due),
        patch.object(loop, "_next_due_time", new=AsyncMock(return_value=None)),
        patch("services.bot.announcement_loop.logger") as mock_logger,
        patch("services.bot.announcement_loop.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        task = asyncio.create_task(loop.start())
        for _ in range(4):
            await real_sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert process_calls >= 3
    mock_logger.exception.assert_called()
    assert mock_logger.exception.call_count >= 2
    assert mock_sleep.await_count >= 2
    mock_sleep.assert_any_call(1.0)


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

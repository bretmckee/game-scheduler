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


"""Unit tests for SchedulerLoop."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.scheduler_loop import SchedulerLoop
from shared.models import NotificationSchedule

_DB_URL = "postgresql+asyncpg://user:pass@localhost:5432/game_scheduler"
_NOTIFY_CHANNEL = "notification_schedule_changed"


def _make_loop(**kwargs: object) -> SchedulerLoop:
    defaults = {
        "db_url": _DB_URL,
        "notify_channel": _NOTIFY_CHANNEL,
        "model_class": NotificationSchedule,
        "time_field": "notification_time",
        "status_field": "sent",
        "event_builder": MagicMock(return_value=MagicMock()),
        "max_timeout": 600,
    }
    defaults.update(kwargs)
    return SchedulerLoop(**defaults)  # type: ignore[arg-type]


def test_construction_stores_params() -> None:
    """SchedulerLoop stores all seven constructor params without raising."""
    builder = MagicMock()
    loop = SchedulerLoop(
        db_url=_DB_URL,
        notify_channel=_NOTIFY_CHANNEL,
        model_class=NotificationSchedule,
        time_field="notification_time",
        status_field="sent",
        event_builder=builder,
        max_timeout=600,
    )
    assert loop._db_url == _DB_URL
    assert loop.notify_channel == _NOTIFY_CHANNEL
    assert loop.model_class is NotificationSchedule
    assert loop.time_field == "notification_time"
    assert loop.status_field == "sent"
    assert loop.event_builder is builder
    assert loop.max_timeout == 600


@pytest.mark.asyncio
async def test_process_item_writes_bot_action_queue_row() -> None:
    """_process_item calls event_builder and adds the result to the DB session."""
    queue_row = MagicMock()
    builder = MagicMock(return_value=queue_row)
    loop = _make_loop(event_builder=builder)

    item = MagicMock()
    item.sent = False

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock()

    with patch("services.bot.scheduler_loop.get_db_session", return_value=mock_session):
        await loop._process_item(item)

    builder.assert_called_once_with(item)
    mock_session.add.assert_any_call(queue_row)


@pytest.mark.asyncio
async def test_process_item_marks_status_field_true() -> None:
    """_process_item sets the item's status_field attribute to True."""
    loop = _make_loop(status_field="sent")

    item = MagicMock()
    item.sent = False

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock()

    with patch("services.bot.scheduler_loop.get_db_session", return_value=mock_session):
        await loop._process_item(item)

    assert item.sent is True


@pytest.mark.asyncio
async def test_process_item_commits_exactly_once() -> None:
    """_process_item performs a single db.commit() for both the queue row and status mark."""
    loop = _make_loop()

    item = MagicMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock()

    with patch("services.bot.scheduler_loop.get_db_session", return_value=mock_session):
        await loop._process_item(item)

    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_skips_process_item_when_not_due() -> None:
    """run() does not call _process_item when the next item's time_field is in the future."""
    loop = _make_loop()

    future_item = MagicMock()
    future_item.notification_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)

    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()

    with (
        patch(
            "services.bot.scheduler_loop.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch.object(loop, "_get_next_due_item", new_callable=AsyncMock, return_value=future_item),
        patch.object(loop, "_process_item", new_callable=AsyncMock) as mock_process,
    ):
        task = asyncio.create_task(loop.run())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_process.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_calls_process_item_when_due() -> None:
    """run() calls _process_item when the next item's time_field is in the past."""
    loop = _make_loop()

    past_item = MagicMock()
    past_item.notification_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)

    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()

    with (
        patch(
            "services.bot.scheduler_loop.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch.object(loop, "_get_next_due_item", new_callable=AsyncMock, return_value=past_item),
        patch.object(loop, "_process_item", new_callable=AsyncMock) as mock_process,
    ):
        task = asyncio.create_task(loop.run())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_process.assert_awaited_once_with(past_item)


@pytest.mark.asyncio
async def test_run_handles_no_items() -> None:
    """run() does not raise when no schedule rows exist."""
    loop = _make_loop()

    mock_conn = AsyncMock()
    mock_conn.add_listener = AsyncMock()

    with (
        patch(
            "services.bot.scheduler_loop.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch.object(loop, "_get_next_due_item", new_callable=AsyncMock, return_value=None),
        patch.object(loop, "_process_item", new_callable=AsyncMock) as mock_process,
    ):
        task = asyncio.create_task(loop.run())
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    mock_process.assert_not_awaited()


def test_on_notify_sets_notified_event() -> None:
    """_on_notify sets _notified so the wait_for in run() wakes up."""
    loop = _make_loop()
    assert not loop._notified.is_set()
    loop._on_notify(MagicMock(), 0, "test_channel", "")
    assert loop._notified.is_set()


@pytest.mark.asyncio
async def test_get_next_due_item_queries_database() -> None:
    """_get_next_due_item opens a DB session and returns the first unprocessed row."""
    loop = _make_loop()
    expected_item = MagicMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = expected_item

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("services.bot.scheduler_loop.get_db_session", return_value=mock_session):
        result = await loop._get_next_due_item()

    assert result is expected_item
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_clears_notified_after_waking() -> None:
    """run() calls _notified.clear() after the wait resolves, preventing a spurious re-wake."""
    loop = _make_loop()
    loop._notified.set()  # Pre-set so the first asyncio.wait_for resolves immediately

    mock_conn = AsyncMock()

    with (
        patch(
            "services.bot.scheduler_loop.asyncpg.connect",
            new_callable=AsyncMock,
            return_value=mock_conn,
        ),
        patch.object(loop, "_get_next_due_item", new_callable=AsyncMock, return_value=None),
        patch.object(loop, "_process_item", new_callable=AsyncMock),
    ):
        task = asyncio.create_task(loop.run())
        # Three yields: first lets run() reach wait_for; second lets the inner
        # Event.wait() coroutine complete; third lets run() resume and call
        # _notified.clear() before we cancel.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert not loop._notified.is_set()

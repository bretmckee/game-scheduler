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


"""Unit tests for BotActionListener."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.bot.bot_action_listener import BotActionListener
from shared.models.bot_action_queue import BotActionQueue


def _make_row(
    action_type: str,
    game_id: str | None = None,
    channel_id: str | None = None,
    message_id: str | None = None,
    discord_id: str | None = None,
    payload: dict | None = None,
) -> BotActionQueue:
    row = MagicMock(spec=BotActionQueue)
    row.id = str(uuid4())
    row.action_type = action_type
    row.game_id = game_id or str(uuid4())
    row.channel_id = channel_id
    row.message_id = message_id
    row.discord_id = discord_id
    row.payload = payload
    return row


@pytest.fixture
def event_handlers() -> MagicMock:
    h = MagicMock()
    h._handle_game_created = AsyncMock()
    h._handle_game_cancelled = AsyncMock()
    h._handle_player_removed = AsyncMock()
    h._handle_send_notification = AsyncMock()
    h._handle_notification_due = AsyncMock()
    h._handle_status_transition_due = AsyncMock()
    h._handle_participant_drop_due = AsyncMock()
    return h


@pytest.fixture
def listener(event_handlers: MagicMock) -> BotActionListener:
    return BotActionListener(
        bot_db_url="postgresql+asyncpg://user:pass@localhost/testdb",
        event_handlers=event_handlers,
    )


class TestProcessOneRow:
    """_process_one returns False on empty queue; True after processing a row."""

    @pytest.mark.asyncio
    async def test_returns_false_when_queue_empty(self, listener: BotActionListener) -> None:
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_db)
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot_action_listener.get_db_session", return_value=ctx):
            result = await listener._process_one()

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_and_deletes_row(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row("game_created", game_id="g1", channel_id="ch1")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_db)
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot_action_listener.get_db_session", return_value=ctx):
            result = await listener._process_one()

        assert result is True
        mock_db.delete.assert_awaited_once_with(row)
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deletes_row_even_when_dispatch_raises(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        """Row is deleted even if the handler raises, to avoid infinite retry loops."""
        row = _make_row("game_created", game_id="g1", channel_id="ch1")
        event_handlers._handle_game_created.side_effect = RuntimeError("discord error")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = row
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_db)
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("services.bot.bot_action_listener.get_db_session", return_value=ctx):
            result = await listener._process_one()

        assert result is True
        mock_db.delete.assert_awaited_once_with(row)
        mock_db.commit.assert_awaited_once()


class TestDispatchGameCreated:
    """game_created rows call _handle_game_created with game_id and channel_id."""

    @pytest.mark.asyncio
    async def test_dispatches_with_correct_data(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row("game_created", game_id="g123", channel_id="ch456")

        await listener._dispatch(row)

        event_handlers._handle_game_created.assert_awaited_once_with({
            "game_id": "g123",
            "channel_id": "ch456",
        })


class TestDispatchGameCancelled:
    """game_cancelled rows call _handle_game_cancelled with game_id, message_id, channel_id."""

    @pytest.mark.asyncio
    async def test_dispatches_with_correct_data(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row("game_cancelled", game_id="g1", channel_id="ch1", message_id="msg1")

        await listener._dispatch(row)

        event_handlers._handle_game_cancelled.assert_awaited_once_with({
            "game_id": "g1",
            "message_id": "msg1",
            "channel_id": "ch1",
        })


class TestDispatchPlayerRemoved:
    """player_removed rows call _handle_player_removed with merged column + payload fields."""

    @pytest.mark.asyncio
    async def test_dispatches_with_correct_data(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row(
            "player_removed",
            game_id="g1",
            channel_id="ch1",
            message_id="msg1",
            discord_id="d123",
            payload={
                "game_title": "My Game",
                "game_scheduled_at": "2026-08-01T18:00:00+00:00",
            },
        )

        await listener._dispatch(row)

        event_handlers._handle_player_removed.assert_awaited_once_with({
            "game_id": "g1",
            "discord_id": "d123",
            "message_id": "msg1",
            "channel_id": "ch1",
            "game_title": "My Game",
            "game_scheduled_at": "2026-08-01T18:00:00+00:00",
        })


class TestDispatchSendDm:
    """send_dm rows call _handle_send_notification mapping discord_id → user_id."""

    @pytest.mark.asyncio
    async def test_dispatches_with_correct_data(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row(
            "send_dm",
            game_id="g1",
            discord_id="d999",
            payload={
                "notification_type": "waitlist_promotion",
                "game_title": "My Game",
                "game_time_unix": 1234567890,
                "message": "You have been promoted!",
            },
        )

        await listener._dispatch(row)

        event_handlers._handle_send_notification.assert_awaited_once_with({
            "user_id": "d999",
            "game_id": "g1",
            "notification_type": "waitlist_promotion",
            "game_title": "My Game",
            "game_time_unix": 1234567890,
            "message": "You have been promoted!",
        })


class TestDispatchUnknownActionType:
    """Unknown action types are logged and do not raise."""

    @pytest.mark.asyncio
    async def test_unknown_type_logs_warning_and_does_not_raise(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row("totally_unknown_type")

        await listener._dispatch(row)

        event_handlers._handle_game_created.assert_not_awaited()
        event_handlers._handle_game_cancelled.assert_not_awaited()
        event_handlers._handle_player_removed.assert_not_awaited()
        event_handlers._handle_send_notification.assert_not_awaited()


class TestDispatchSchedulerActionTypes:
    """notification_due, status_transition_due, and participant_drop_due are dispatched."""

    @pytest.mark.asyncio
    async def test_notification_due_dispatches(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row(
            "notification_due",
            game_id="g1",
            payload={"notification_type": "reminder", "participant_id": None},
        )

        await listener._dispatch(row)

        event_handlers._handle_notification_due.assert_awaited_once()
        call_data = event_handlers._handle_notification_due.call_args[0][0]
        assert call_data["game_id"] == "g1"

    @pytest.mark.asyncio
    async def test_status_transition_due_dispatches(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row(
            "status_transition_due",
            game_id="g2",
            payload={"target_status": "IN_PROGRESS", "transition_time": "2026-08-01T00:00:00Z"},
        )

        await listener._dispatch(row)

        event_handlers._handle_status_transition_due.assert_awaited_once()
        call_data = event_handlers._handle_status_transition_due.call_args[0][0]
        assert call_data["game_id"] == "g2"

    @pytest.mark.asyncio
    async def test_participant_drop_due_dispatches(
        self, listener: BotActionListener, event_handlers: MagicMock
    ) -> None:
        row = _make_row(
            "participant_drop_due",
            game_id="g3",
            payload={"participant_id": "p-001"},
        )

        await listener._dispatch(row)

        event_handlers._handle_participant_drop_due.assert_awaited_once()
        call_data = event_handlers._handle_participant_drop_due.call_args[0][0]
        assert call_data["game_id"] == "g3"


class TestOnNotify:
    """_on_notify calls _spawn_drain."""

    def test_on_notify_spawns_drain(self, listener: BotActionListener) -> None:
        spawned = []

        def fake_spawn() -> None:
            spawned.append(True)

        listener._spawn_drain = fake_spawn  # type: ignore[method-assign]
        listener._on_notify(MagicMock(), 0, "bot_action_queue_changed", "")

        assert spawned == [True]


class TestStartExceptionHandling:
    """start() catches non-CancelledError exceptions without propagating."""

    @pytest.mark.asyncio
    async def test_start_handles_connect_error(self, listener: BotActionListener) -> None:
        with patch(
            "services.bot.bot_action_listener.asyncpg.connect",
            side_effect=OSError("connection refused"),
        ):
            await listener.start()  # must not raise

        assert listener._drain_task is None  # no drain was spawned


class TestDrainQueue:
    """_drain_queue loops until _process_one returns False."""

    @pytest.mark.asyncio
    async def test_drains_all_rows(self, listener: BotActionListener) -> None:
        calls = [True, True, False]
        call_iter = iter(calls)

        async def fake_process_one() -> bool:
            return next(call_iter)

        listener._process_one = fake_process_one  # type: ignore[method-assign]

        await listener._drain_queue()

        assert list(call_iter) == []


class TestSpawnDrain:
    """_spawn_drain creates a task only when no worker is running."""

    def _make_task_factory(self, task: MagicMock) -> object:
        """Return a create_task side_effect that closes the coroutine and returns task."""

        def factory(coro: object) -> MagicMock:
            import inspect  # noqa: PLC0415

            if inspect.iscoroutine(coro):
                coro.close()  # type: ignore[union-attr]
            return task

        return factory

    def test_spawns_task_when_none_exists(self, listener: BotActionListener) -> None:
        mock_task = MagicMock()

        with patch(
            "services.bot.bot_action_listener.asyncio.create_task",
            side_effect=self._make_task_factory(mock_task),
        ) as mock_ct:
            listener._spawn_drain()

        assert mock_ct.call_count == 1
        assert listener._drain_task is mock_task

    def test_no_duplicate_spawn_when_task_running(self, listener: BotActionListener) -> None:
        running_task = MagicMock()
        running_task.done.return_value = False
        listener._drain_task = running_task

        with patch("services.bot.bot_action_listener.asyncio.create_task") as mock_ct:
            listener._spawn_drain()

        mock_ct.assert_not_called()

    def test_respawns_when_previous_task_done(self, listener: BotActionListener) -> None:
        done_task = MagicMock()
        done_task.done.return_value = True
        listener._drain_task = done_task

        new_task = MagicMock()
        with patch(
            "services.bot.bot_action_listener.asyncio.create_task",
            side_effect=self._make_task_factory(new_task),
        ) as mock_ct:
            listener._spawn_drain()

        assert mock_ct.call_count == 1
        assert listener._drain_task is new_task


class TestStart:
    """start() opens asyncpg connection, LISTENs, drains pending rows, then blocks."""

    @pytest.mark.asyncio
    async def test_start_listens_and_drains_pending(self, listener: BotActionListener) -> None:
        mock_conn = AsyncMock()
        mock_conn.add_listener = AsyncMock()
        mock_conn.close = AsyncMock()

        # Make create_future() return a future that immediately resolves (so start() returns)
        done_future: asyncio.Future[None] = asyncio.get_event_loop().create_future()
        done_future.set_result(None)

        spawn_called: list[bool] = []

        def fake_spawn_drain() -> None:
            spawn_called.append(True)

        listener._spawn_drain = fake_spawn_drain  # type: ignore[method-assign]

        with (
            patch("services.bot.bot_action_listener.asyncpg.connect", return_value=mock_conn),
            patch.object(asyncio.get_event_loop(), "create_future", return_value=done_future),
        ):
            await listener.start()

        mock_conn.add_listener.assert_awaited_once_with(
            "bot_action_queue_changed", listener._on_notify
        )
        assert spawn_called == [True]
        mock_conn.close.assert_awaited_once()

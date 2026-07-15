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


"""Unit tests for listen_with_reconnect."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.pg_listen import listen_with_reconnect

_DB_URL = "postgresql+asyncpg://user:pass@localhost:5432/game_scheduler"
_CHANNEL = "some_channel"


def _make_conn() -> MagicMock:
    """A fresh mock asyncpg.Connection with the API listen_with_reconnect touches."""
    conn = MagicMock()
    conn.add_listener = AsyncMock()
    conn.add_termination_listener = MagicMock()
    conn.close = AsyncMock()
    conn.is_closed = MagicMock(return_value=False)
    return conn


async def _run_until(condition: object, *, attempts: int = 200) -> None:
    """Yield to the event loop until condition() is truthy or attempts run out."""
    for _ in range(attempts):
        if condition():
            return
        await asyncio.sleep(0)


async def _cancel_and_wait(task: asyncio.Task) -> None:
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


class TestListenWithReconnectInitialConnect:
    """Verify the first connection attempt sets up LISTEN correctly."""

    @pytest.mark.asyncio
    async def test_connects_and_registers_listener(self) -> None:
        """Strips the +asyncpg driver prefix and registers on_notify on channel."""
        conn = _make_conn()
        on_notify = MagicMock()

        with patch(
            "shared.pg_listen.asyncpg.connect", new_callable=AsyncMock, return_value=conn
        ) as mock_connect:
            task = asyncio.create_task(
                listen_with_reconnect(_DB_URL, _CHANNEL, on_notify, retry_delay_seconds=0)
            )
            await _run_until(lambda: mock_connect.await_count >= 1)
            await _cancel_and_wait(task)

        called_url = mock_connect.call_args[0][0]
        assert called_url == "postgresql://user:pass@localhost:5432/game_scheduler"
        conn.add_listener.assert_awaited_once_with(_CHANNEL, on_notify)

    @pytest.mark.asyncio
    async def test_calls_on_connected_after_listener_registered(self) -> None:
        """on_connected(conn) fires once LISTEN is registered."""
        conn = _make_conn()
        on_connected_calls: list[object] = []

        with patch("shared.pg_listen.asyncpg.connect", new_callable=AsyncMock, return_value=conn):
            task = asyncio.create_task(
                listen_with_reconnect(
                    _DB_URL,
                    _CHANNEL,
                    MagicMock(),
                    on_connected=on_connected_calls.append,
                    retry_delay_seconds=0,
                )
            )
            await _run_until(lambda: len(on_connected_calls) >= 1)
            await _cancel_and_wait(task)

        assert on_connected_calls == [conn]

    @pytest.mark.asyncio
    async def test_cancellation_closes_connection(self) -> None:
        """Cancelling the task closes the open connection and propagates."""
        conn = _make_conn()

        with patch("shared.pg_listen.asyncpg.connect", new_callable=AsyncMock, return_value=conn):
            task = asyncio.create_task(
                listen_with_reconnect(_DB_URL, _CHANNEL, MagicMock(), retry_delay_seconds=0)
            )
            await _run_until(lambda: conn.add_listener.await_count >= 1)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        conn.close.assert_awaited_once()


class TestListenWithReconnectOnConnectionLoss:
    """Verify a silently dropped connection triggers a reconnect."""

    @pytest.mark.asyncio
    async def test_reconnects_after_termination_listener_fires(self) -> None:
        """Simulating asyncpg's own disconnect callback triggers a second connect."""
        conn1 = _make_conn()
        conn2 = _make_conn()
        on_notify = MagicMock()

        with patch(
            "shared.pg_listen.asyncpg.connect",
            new_callable=AsyncMock,
            side_effect=[conn1, conn2],
        ) as mock_connect:
            task = asyncio.create_task(
                listen_with_reconnect(_DB_URL, _CHANNEL, on_notify, retry_delay_seconds=0)
            )
            await _run_until(lambda: conn1.add_termination_listener.call_count >= 1)

            # Simulate what asyncpg._cleanup() does when the socket dies: it invokes
            # every registered termination listener with the dead connection.
            termination_cb = conn1.add_termination_listener.call_args[0][0]
            termination_cb(conn1)

            await _run_until(lambda: mock_connect.await_count >= 2)
            await _cancel_and_wait(task)

        assert mock_connect.await_count == 2
        conn2.add_listener.assert_awaited_once_with(_CHANNEL, on_notify)

    @pytest.mark.asyncio
    async def test_calls_on_disconnected_after_connection_lost(self) -> None:
        """on_disconnected fires after the dead connection is cleaned up."""
        conn1 = _make_conn()
        conn2 = _make_conn()
        disconnect_count = 0

        def on_disconnected() -> None:
            nonlocal disconnect_count
            disconnect_count += 1

        with patch(
            "shared.pg_listen.asyncpg.connect",
            new_callable=AsyncMock,
            side_effect=[conn1, conn2],
        ):
            task = asyncio.create_task(
                listen_with_reconnect(
                    _DB_URL,
                    _CHANNEL,
                    MagicMock(),
                    on_disconnected=on_disconnected,
                    retry_delay_seconds=0,
                )
            )
            await _run_until(lambda: conn1.add_termination_listener.call_count >= 1)
            termination_cb = conn1.add_termination_listener.call_args[0][0]
            # Real asyncpg marks the connection closed before invoking termination
            # listeners; mirror that so the implementation can be seen not to double-close.
            conn1.is_closed.return_value = True
            termination_cb(conn1)

            await _run_until(lambda: disconnect_count >= 1)
            await _cancel_and_wait(task)

        assert disconnect_count == 1
        conn1.close.assert_not_awaited()  # already closed by asyncpg itself; do not double-close


class TestListenWithReconnectOnConnectError:
    """Verify a failed connection attempt is retried rather than raised."""

    @pytest.mark.asyncio
    async def test_retries_after_connect_failure(self) -> None:
        """asyncpg.connect raising does not propagate; the loop retries."""
        conn = _make_conn()

        with patch(
            "shared.pg_listen.asyncpg.connect",
            new_callable=AsyncMock,
            side_effect=[OSError("connection refused"), conn],
        ) as mock_connect:
            task = asyncio.create_task(
                listen_with_reconnect(_DB_URL, _CHANNEL, MagicMock(), retry_delay_seconds=0)
            )
            await _run_until(lambda: mock_connect.await_count >= 2)
            await _cancel_and_wait(task)

        assert mock_connect.await_count == 2
        conn.add_listener.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_logs_exception_on_connect_failure(self) -> None:
        """A connect failure is logged via logger.exception, not raised."""
        with (
            patch(
                "shared.pg_listen.asyncpg.connect",
                new_callable=AsyncMock,
                side_effect=OSError("connection refused"),
            ),
            patch("shared.pg_listen.logger") as mock_logger,
        ):
            task = asyncio.create_task(
                listen_with_reconnect(_DB_URL, _CHANNEL, MagicMock(), retry_delay_seconds=0)
            )
            await _run_until(lambda: mock_logger.exception.call_count >= 1)
            await _cancel_and_wait(task)

        mock_logger.exception.assert_called()

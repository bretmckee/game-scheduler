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


"""Resilient asyncpg LISTEN helper that reconnects after connection loss."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)

DEFAULT_RETRY_DELAY_SECONDS = 5.0


async def listen_with_reconnect(
    db_url: str,
    channel: str,
    on_notify: Callable[[asyncpg.Connection, int, str, str], Any],
    *,
    on_connected: Callable[[asyncpg.Connection], None] | None = None,
    on_disconnected: Callable[[], None] | None = None,
    retry_delay_seconds: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> None:
    """Maintain a Postgres LISTEN connection on ``channel``, reconnecting on loss.

    Runs until cancelled. Unlike a bare ``asyncpg.connect()`` + ``add_listener()``
    call, this detects a silently dropped connection (transient network loss, an
    idle-timeout kill from a proxy/pooler, a Postgres restart) via
    ``add_termination_listener`` and reconnects with a fixed delay, instead of
    hanging forever on a connection that will never deliver another NOTIFY.

    Args:
        db_url: PostgreSQL connection URL. Accepts either ``postgresql://`` or
            the SQLAlchemy ``postgresql+asyncpg://`` form; the driver prefix is
            stripped before being passed to asyncpg.
        channel: Channel name to LISTEN on.
        on_notify: Callback registered via ``add_listener`` for NOTIFY payloads.
        on_connected: Optional callback invoked with the new connection after
            each successful (re)connect, once LISTEN is registered.
        on_disconnected: Optional callback invoked after each connection is
            closed, whether due to cancellation, an error, or a lost connection.
        retry_delay_seconds: Delay before each reconnect attempt.
    """
    pg_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    while True:
        conn: asyncpg.Connection | None = None
        disconnected = asyncio.Event()
        try:
            conn = await asyncpg.connect(pg_url)
            conn.add_termination_listener(
                lambda _conn, _disconnected=disconnected: _disconnected.set()
            )
            await conn.add_listener(channel, on_notify)
            if on_connected is not None:
                on_connected(conn)
            await disconnected.wait()
            logger.warning(
                "LISTEN connection on channel %s lost, reconnecting in %.1fs",
                channel,
                retry_delay_seconds,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "LISTEN connection on channel %s failed, retrying in %.1fs",
                channel,
                retry_delay_seconds,
            )
        finally:
            if conn is not None and not conn.is_closed():
                await conn.close()
            if on_disconnected is not None:
                on_disconnected()
        await asyncio.sleep(retry_delay_seconds)

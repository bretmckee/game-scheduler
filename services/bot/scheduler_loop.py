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


"""Async scheduler loop running inside the bot service."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

import asyncpg
from sqlalchemy import select

from shared.database import get_db_session
from shared.models.base import utc_now

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


class SchedulerLoop:
    """Async replacement for SchedulerDaemon — one per schedule table."""

    def __init__(
        self,
        db_url: str,
        notify_channel: str,
        model_class: type,
        time_field: str,
        status_field: str,
        event_builder: Callable[..., Any],
        max_timeout: int = 900,
    ) -> None:
        self._db_url = db_url
        self.notify_channel = notify_channel
        self.model_class = model_class
        self.time_field = time_field
        self.status_field = status_field
        self.event_builder = event_builder
        self.max_timeout = max_timeout
        self._notified = asyncio.Event()

    async def run(self) -> None:
        """Open asyncpg LISTEN connection and run the scheduling loop."""
        pg_url = self._db_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(pg_url)
        await conn.add_listener(self.notify_channel, self._on_notify)
        while True:
            item = await self._get_next_due_item()
            if item is not None and self._is_due(item):
                await self._process_item(item)
                await asyncio.sleep(0)
            else:
                wait = self._time_until_due(item) or self.max_timeout
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(self._notified.wait(), timeout=wait)
                self._notified.clear()

    async def _process_item(self, item: object) -> None:
        """Build a BotActionQueue row, add it to the DB session, and mark item processed."""
        queue_row = self.event_builder(item)
        async with get_db_session() as db:
            db.add(queue_row)
            # Re-attach the detached item so the status change is tracked by this session.
            db.add(item)
            setattr(item, self.status_field, True)
            await db.commit()

    def _on_notify(
        self,
        _conn: asyncpg.Connection,
        _pid: int,
        _channel: str,
        _payload: str,
    ) -> None:
        """Wake the scheduling loop when a NOTIFY arrives."""
        self._notified.set()

    async def _get_next_due_item(self) -> object | None:
        """Query for the earliest unprocessed schedule row."""
        async with get_db_session() as db:
            result: Any = await db.execute(
                select(self.model_class)
                .where(getattr(self.model_class, self.status_field).is_(False))
                .where(getattr(self.model_class, self.time_field).isnot(None))
                .order_by(getattr(self.model_class, self.time_field).asc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    def _is_due(self, item: object) -> bool:
        """Return True if item's scheduled time is now or in the past."""
        return getattr(item, self.time_field) <= utc_now()

    def _time_until_due(self, item: object | None) -> float | None:
        """Return seconds until item is due, or None if no item."""
        if item is None:
            return None
        scheduled_time = getattr(item, self.time_field)
        return max(0.0, (scheduled_time - utc_now()).total_seconds())

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


"""asyncpg LISTEN-based listener that processes bot_action_queue rows on NOTIFY."""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import asyncpg
from sqlalchemy import select

from shared.database import get_db_session
from shared.models.bot_action_queue import BotActionQueue
from shared.pg_listen import listen_with_reconnect

if TYPE_CHECKING:
    from services.bot.events.handlers import EventHandlers

logger = logging.getLogger(__name__)


def _build_handler_data(row: BotActionQueue) -> dict[str, Any]:
    """Map BotActionQueue columns to the data dict expected by each handler."""
    payload: dict[str, Any] = row.payload or {}
    match row.action_type:
        case "game_created":
            return {"game_id": row.game_id, "channel_id": row.channel_id}
        case "game_cancelled":
            return {
                "game_id": row.game_id,
                "message_id": row.message_id,
                "channel_id": row.channel_id,
            }
        case "player_removed":
            return {
                "game_id": row.game_id,
                "discord_id": row.discord_id,
                "message_id": row.message_id,
                "channel_id": row.channel_id,
                "game_title": payload.get("game_title"),
                "game_scheduled_at": payload.get("game_scheduled_at"),
            }
        case "send_dm":
            return {
                "user_id": row.discord_id,
                "game_id": row.game_id,
                "notification_type": payload.get("notification_type"),
                "game_title": payload.get("game_title"),
                "game_time_unix": payload.get("game_time_unix"),
                "message": payload.get("message"),
            }
        case _:
            # Flows 5-7 (scheduler-generated) store all needed fields in payload.
            return {**payload, "game_id": row.game_id}


class BotActionListener:
    """
    Holds a dedicated asyncpg connection that listens for
    ``bot_action_queue_changed`` notifications from Postgres.

    When a NOTIFY arrives (or on startup to catch any rows written before
    the listener connected), it drains the ``bot_action_queue`` table one row
    at a time, dispatching each row to the appropriate ``EventHandlers`` method.

    Each row is deleted within the same transaction as the dispatch attempt.
    If dispatch raises, the error is logged and the row is still deleted to
    prevent infinite retry loops. Crash safety is provided by Postgres atomicity:
    rows that were not yet committed as deleted survive a bot restart.

    Args:
        bot_db_url: PostgreSQL connection URL (``postgresql+asyncpg://…`` or
            ``postgresql://…`` are both accepted).
        event_handlers: ``EventHandlers`` instance whose handler methods are
            called for each action type.
    """

    def __init__(
        self,
        bot_db_url: str,
        event_handlers: "EventHandlers",
    ) -> None:
        self._bot_db_url = bot_db_url
        self._event_handlers = event_handlers
        self._drain_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Maintain the LISTEN connection, reconnecting automatically on loss.

        Drains any pending bot_action_queue rows on every (re)connect, not
        just the first one, so rows written while the connection was down
        (or before the listener started) are picked up once LISTEN resumes.
        """
        await listen_with_reconnect(
            self._bot_db_url,
            "bot_action_queue_changed",
            self._on_notify,
            on_connected=lambda _conn: self._spawn_drain(),
        )

    def _on_notify(
        self,
        _conn: asyncpg.Connection,
        _pid: int,
        _channel: str,
        _payload: str,
    ) -> None:
        """Spawn a drain task when Postgres delivers a NOTIFY."""
        self._spawn_drain()

    def _spawn_drain(self) -> None:
        """Spawn _drain_queue as a task unless one is already running."""
        if self._drain_task is None or self._drain_task.done():
            self._drain_task = asyncio.create_task(self._drain_queue())

    async def _drain_queue(self) -> None:
        """Process rows until the queue is empty."""
        while True:
            processed = await self._process_one()
            if not processed:
                break

    async def _process_one(self) -> bool:
        """Fetch and process one pending row.

        Returns True if a row was processed, False if the queue was empty.
        The row is always deleted (within the same db transaction) even if
        dispatch raises, to prevent infinite retry loops.
        """
        async with get_db_session() as db:
            result = await db.execute(
                select(BotActionQueue)
                .order_by(BotActionQueue.enqueued_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return False

            try:
                await self._dispatch(row)
            except Exception:
                logger.exception(
                    "Error dispatching action_type=%r row=%s; deleting to prevent retry loop",
                    row.action_type,
                    row.id,
                )

            await db.delete(row)
            await db.commit()
            return True

    async def _dispatch(self, row: BotActionQueue) -> None:
        """Route a queue row to the appropriate EventHandlers method."""
        data = _build_handler_data(row)
        match row.action_type:
            case "game_created":
                await self._event_handlers._handle_game_created(data)
            case "game_cancelled":
                await self._event_handlers._handle_game_cancelled(data)
            case "player_removed":
                await self._event_handlers._handle_player_removed(data)
            case "send_dm":
                await self._event_handlers._handle_send_notification(data)
            case "notification_due":
                await self._event_handlers._handle_notification_due(data)
            case "status_transition_due":
                await self._event_handlers._handle_status_transition_due(data)
            case "participant_drop_due":
                await self._event_handlers._handle_participant_drop_due(data)
            case _:
                logger.warning(
                    "Unknown action_type %r in bot_action_queue row %s", row.action_type, row.id
                )

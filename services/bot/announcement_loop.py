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


"""Async announcement loop for deferred game announcements."""

from __future__ import annotations

import asyncio
import contextlib
import datetime
import logging
from typing import TYPE_CHECKING

import discord
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from shared.database import get_db_session
from shared.models import participant as participant_model
from shared.models.game import GameSession
from shared.pg_listen import listen_with_reconnect
from shared.services.game_schedules import setup_game_schedules
from shared.utils.status_transitions import GameStatus

if TYPE_CHECKING:
    import asyncpg

    from services.bot.bot import GameSchedulerBot

logger = logging.getLogger(__name__)


class AnnouncementLoop:
    """Polls for deferred game announcements and posts them when their post_at time arrives.

    Maintains a dedicated asyncpg connection listening for
    ``game_announcement_changed`` notifications from Postgres to wake up early
    when a game's ``post_at`` changes.
    """

    MAX_TIMEOUT = 3600

    def __init__(self, db_url: str, bot: GameSchedulerBot) -> None:
        self._db_url = db_url
        self._bot = bot
        self._wake_event = asyncio.Event()

    async def start(self) -> None:
        """Maintain the LISTEN connection and run the announcement loop concurrently.

        Connection lifecycle (including reconnect-on-loss) is delegated to
        listen_with_reconnect; the due-item loop runs independently since it
        only depends on the _wake_event set by _on_notify, not on the
        connection object itself.
        """
        async with asyncio.TaskGroup() as tg:
            tg.create_task(
                listen_with_reconnect(self._db_url, "game_announcement_changed", self._on_notify)
            )
            tg.create_task(self._run_loop())

    async def _run_loop(self) -> None:
        """Poll for and post due announcements, surviving per-iteration errors."""
        while True:
            try:
                await self._process_due()
                next_due = await self._next_due_time()
                if next_due is not None:
                    wait = max(
                        0.0,
                        (
                            next_due - datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
                        ).total_seconds(),
                    )
                else:
                    wait = float(self.MAX_TIMEOUT)
                wait = min(wait, float(self.MAX_TIMEOUT))
                logger.debug(
                    "AnnouncementLoop sleeping %.1fs (next_due=%s)",
                    wait,
                    next_due,
                )
                self._wake_event.clear()
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(self._wake_event.wait(), timeout=wait)
                logger.debug(
                    "AnnouncementLoop woke up (reason=%s)",
                    "notify" if self._wake_event.is_set() else "timeout",
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("AnnouncementLoop: error in loop iteration, retrying")

    def _on_notify(
        self, _conn: asyncpg.Connection, _pid: int, _channel: str, _payload: str
    ) -> None:
        """Wake the loop when a game_announcement_changed NOTIFY arrives."""
        logger.debug("AnnouncementLoop: NOTIFY received (payload=%s)", _payload)
        self._wake_event.set()

    async def _next_due_time(self) -> datetime.datetime | None:
        """Return the earliest future post_at among unannounced scheduled games."""
        async with get_db_session() as db:
            result = await db.execute(
                select(func.min(GameSession.post_at)).where(
                    GameSession.post_at.isnot(None),
                    GameSession.post_at > datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                    GameSession.message_id.is_(None),
                    GameSession.status == GameStatus.SCHEDULED.value,
                )
            )
            return result.scalar_one_or_none()

    async def _process_due(self) -> None:
        """Find all due unannounced games and announce each one."""
        logger.debug("AnnouncementLoop: checking for due games")
        async with get_db_session() as db:
            result = await db.execute(
                select(GameSession.id)
                .where(
                    GameSession.post_at.isnot(None),
                    GameSession.post_at <= datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
                    GameSession.message_id.is_(None),
                    GameSession.status == GameStatus.SCHEDULED.value,
                )
                .with_for_update(skip_locked=True)
            )
            game_ids = list(result.scalars().all())

        logger.debug("AnnouncementLoop: found %d due game(s): %s", len(game_ids), game_ids)
        for game_id in game_ids:
            await self._announce(game_id)

    async def _announce(self, game_id: str) -> None:
        """Post the Discord announcement for a single game and set up its schedules."""
        logger.debug("AnnouncementLoop: announcing game=%s", game_id)
        async with get_db_session() as db:
            result = await db.execute(
                select(GameSession)
                .where(
                    GameSession.id == game_id,
                    GameSession.message_id.is_(None),
                )
                .with_for_update(skip_locked=True)
                .options(
                    selectinload(GameSession.host),
                    selectinload(GameSession.guild),
                    selectinload(GameSession.channel),
                    selectinload(GameSession.template),
                    selectinload(GameSession.participants).selectinload(
                        participant_model.GameParticipant.user
                    ),
                )
            )
            game = result.scalar_one_or_none()
            if game is None:
                return

            handlers = self._bot.event_handlers
            channel = await handlers._get_bot_channel(game.channel.channel_id)
            if channel is None:
                logger.error("Channel not found for deferred game announcement: game=%s", game_id)
                return

            content, embed, view = await handlers._create_game_announcement(game)
            allowed_mentions = discord.AllowedMentions(roles=True, everyone=True)
            message = await channel.send(
                content=content,
                embed=embed,
                view=view,
                allowed_mentions=allowed_mentions,
            )
            message_id = str(message.id)
            game.message_id = message_id
            await db.commit()

            # Set up reminders and join notifications now that the announcement is live.
            await setup_game_schedules(
                db=db,
                game=game,
                reminder_minutes=game.reminder_minutes or [],
            )
            await db.commit()

            logger.info(
                "Posted deferred game announcement: game=%s, message=%s", game_id, message_id
            )

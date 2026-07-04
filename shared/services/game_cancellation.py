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


"""Game cancellation service."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.messaging.deferred_publisher import DeferredEventPublisher
from shared.messaging.events import Event, EventType
from shared.models.game import GameSession
from shared.services.image_storage import release_image

logger = logging.getLogger(__name__)


async def cancel_game(
    db: AsyncSession,
    game: GameSession,
    event_publisher: DeferredEventPublisher | None = None,
) -> None:
    """
    Cancel a game: release image refs, delete the row, and optionally enqueue notification.

    Captures message_id and channel_id from the game object *before* db.delete so
    the GAME_CANCELLED payload has valid IDs even after the row is gone.

    Args:
        db: Async database session (caller must commit).
        game: Game session to cancel.
        event_publisher: Optional DeferredEventPublisher. When provided, a
            GAME_CANCELLED event is queued for publishing after the transaction
            commits so the bot can clean up the Discord message.
    """
    message_id = game.message_id or ""
    # Use the Discord snowflake channel_id (from the relationship) so the bot can
    # locate the correct Discord channel to delete the embed from.
    channel_discord_id = game.channel.channel_id if game.channel else ""

    await release_image(db, game.thumbnail_id)
    await release_image(db, game.banner_image_id)

    await db.delete(game)

    if event_publisher is not None:
        event = Event(
            event_type=EventType.GAME_CANCELLED,
            data={
                "game_id": game.id,
                "message_id": message_id,
                "channel_id": channel_discord_id,
            },
        )
        event_publisher.publish_deferred(event=event)
        logger.info("Deferred game.cancelled event for game %s", game.id)

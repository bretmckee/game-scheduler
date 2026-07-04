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

from shared.models.bot_action_queue import BotActionQueue
from shared.models.game import GameSession
from shared.services.image_storage import release_image

logger = logging.getLogger(__name__)


async def cancel_game(
    db: AsyncSession,
    game: GameSession,
    enqueue_cancellation: bool = True,
) -> None:
    """
    Cancel a game: release image refs, delete the row, and optionally enqueue notification.

    Captures message_id and channel_id from the game object *before* db.delete so
    the GAME_CANCELLED payload has valid IDs even after the row is gone.

    Args:
        db: Async database session (caller must commit).
        game: Game session to cancel.
        enqueue_cancellation: When True (default), inserts a 'game_cancelled' row
            into bot_action_queue so the bot deletes the Discord embed. Pass False
            when the Discord message is already gone (e.g. bot-initiated cancel).
    """
    game_id = game.id
    message_id = game.message_id or ""

    await release_image(db, game.thumbnail_id)
    await release_image(db, game.banner_image_id)

    await db.delete(game)

    if enqueue_cancellation:
        # Access channel relationship only when needed for the bot notification.
        channel_discord_id = game.channel.channel_id if game.channel else ""
        db.add(
            BotActionQueue(
                action_type="game_cancelled",
                game_id=game_id,
                message_id=message_id,
                channel_id=channel_discord_id,
            )
        )
        logger.info("Enqueued game_cancelled action for game %s", game_id)

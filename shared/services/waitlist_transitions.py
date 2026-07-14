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


"""Waitlist promotion/demotion detection and notification."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.message_formats import DMFormats
from shared.models.bot_action_queue import BotActionQueue
from shared.models.game import GameSession
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import PartitionedParticipants, partition_participants

logger = logging.getLogger(__name__)


def _build_jump_url(game: GameSession) -> str | None:
    if game.message_id and game.guild and game.channel:
        return (
            f"https://discord.com/channels/"
            f"{game.guild.guild_id}/{game.channel.channel_id}/{game.message_id}"
        )
    logger.warning("Cannot build jump URL for waitlist notification on game %s", game.id)
    return None


async def _notify_promoted_users(
    db: AsyncSession, game: GameSession, promoted_discord_ids: set[str]
) -> None:
    scheduled_at_unix = int(game.scheduled_at.timestamp())
    jump_url = _build_jump_url(game)
    message = DMFormats.promotion(game.title, scheduled_at_unix, jump_url=jump_url)

    for discord_id in promoted_discord_ids:
        db.add(
            BotActionQueue(
                action_type="send_dm",
                game_id=game.id,
                discord_id=discord_id,
                payload={
                    "notification_type": "waitlist_promotion",
                    "game_title": game.title,
                    "game_time_unix": scheduled_at_unix,
                    "message": message,
                },
            )
        )
        logger.info("Enqueued send_dm (promotion) for user %s in game %s", discord_id, game.id)


async def _notify_demoted_users(
    db: AsyncSession, game: GameSession, demoted_discord_ids: set[str]
) -> None:
    scheduled_at_unix = int(game.scheduled_at.timestamp())
    jump_url = _build_jump_url(game)
    message = DMFormats.waitlist_demotion(game.title, jump_url=jump_url)

    for discord_id in demoted_discord_ids:
        db.add(
            BotActionQueue(
                action_type="send_dm",
                game_id=game.id,
                discord_id=discord_id,
                payload={
                    "notification_type": "waitlist_demotion",
                    "game_title": game.title,
                    "game_time_unix": scheduled_at_unix,
                    "message": message,
                },
            )
        )
        logger.info("Enqueued send_dm (demotion) for user %s in game %s", discord_id, game.id)


async def detect_and_notify_transitions(
    db: AsyncSession,
    game: GameSession,
    old_partitioned: PartitionedParticipants,
) -> tuple[set[str], set[str]]:
    """Detect waitlist promotions/demotions and enqueue send_dm notifications.

    Compares the game's current participant state against a previously captured
    partitioned state, enqueuing a BotActionQueue 'send_dm' row for every user
    who was promoted (overflow -> confirmed) or demoted (confirmed -> overflow).

    Args:
        db: Async database session (caller must commit).
        game: Game session with the current (post-mutation) participant list.
        old_partitioned: Partitioned participants captured before the mutation.

    Returns:
        Tuple of (promoted_discord_ids, demoted_discord_ids).
    """
    new_max_players = resolve_max_players(game.max_players)
    new_partitioned = partition_participants(
        game.participants, new_max_players, signup_method=game.signup_method
    )
    promoted_discord_ids = new_partitioned.cleared_waitlist(old_partitioned)
    demoted_discord_ids = new_partitioned.entered_waitlist(old_partitioned)

    if promoted_discord_ids:
        logger.info(
            "Notifying %s promoted users for game %s: %s",
            len(promoted_discord_ids),
            game.id,
            promoted_discord_ids,
        )
        await _notify_promoted_users(db, game, promoted_discord_ids)

    if demoted_discord_ids:
        logger.info(
            "Notifying %s demoted users for game %s: %s",
            len(demoted_discord_ids),
            game.id,
            demoted_discord_ids,
        )
        await _notify_demoted_users(db, game, demoted_discord_ids)

    return promoted_discord_ids, demoted_discord_ids

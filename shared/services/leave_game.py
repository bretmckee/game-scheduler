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


"""Shared leave-game core: delete participant, detect transitions, and notify."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.message_formats import DMFormats
from shared.models.bot_action_queue import BotActionQueue
from shared.models.game import GameSession
from shared.models.participant import GameParticipant, ParticipantType
from shared.services import waitlist_transitions
from shared.utils.games import resolve_max_players
from shared.utils.participant_sorting import partition_participants

logger = logging.getLogger(__name__)


async def _notify_host_added_dropout(
    db: AsyncSession, game: GameSession, participant: GameParticipant, host_discord_id: str
) -> None:
    scheduled_unix = int(game.scheduled_at.timestamp())
    jump_url = (
        f"https://discord.com/channels/{game.guild.guild_id}/"
        f"{game.channel.channel_id}/{game.message_id}"
        if game.message_id
        else None
    )
    message = DMFormats.host_added_dropout(
        player_mention=f"<@{participant.user.discord_id}>",
        game_title=game.title,
        game_time_unix=scheduled_unix,
        jump_url=jump_url,
    )
    db.add(
        BotActionQueue(
            action_type="send_dm",
            game_id=game.id,
            discord_id=host_discord_id,
            payload={
                "notification_type": "host_added_dropout",
                "game_title": game.title,
                "game_time_unix": scheduled_unix,
                "message": message,
            },
        )
    )
    logger.info("Enqueued send_dm (host_added_dropout) for game %s", game.id)


async def leave_game_and_notify(
    db: AsyncSession,
    game: GameSession,
    participant: GameParticipant,
) -> GameSession:
    """Remove a participant, detect waitlist transitions, and notify affected users.

    Precondition: `game` must have `participants` (with `.user`), `host`, `guild`, and
    `channel` relationships already loaded (e.g. via GameService.get_game()'s selectinload
    chain). Does not commit; caller must commit.

    Args:
        db: Async database session (caller must commit).
        game: Game session the participant is leaving.
        participant: The participant row to delete.

    Returns:
        The game with its `participants` relationship refreshed after the delete.
    """
    position_type = participant.position_type
    host_discord_id = game.host.discord_id if game.host else None
    old_partitioned = partition_participants(
        game.participants, resolve_max_players(game.max_players), signup_method=game.signup_method
    )

    await db.delete(participant)
    await db.flush()
    await db.refresh(game, ["participants"])

    await waitlist_transitions.detect_and_notify_transitions(db, game, old_partitioned)

    if position_type == ParticipantType.HOST_ADDED and host_discord_id:
        await _notify_host_added_dropout(db, game, participant, host_discord_id)

    return game

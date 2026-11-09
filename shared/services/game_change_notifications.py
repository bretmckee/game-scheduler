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


"""Participant DM notifications when an announced game's details change."""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from shared.message_formats import DMFormats
from shared.models.bot_action_queue import BotActionQueue
from shared.models.game import GameSession
from shared.utils.games import build_jump_url
from shared.utils.timezone import to_unix_timestamp

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GameNotifySnapshot:
    """Pre-edit values of the fields whose changes participants are told about."""

    scheduled_at: datetime
    expected_duration_minutes: int | None
    where: str | None
    signup_instructions: str | None


def capture_notify_snapshot(game: GameSession) -> GameNotifySnapshot:
    """Capture the game's current notify-field values before an edit.

    Args:
        game: Game session before any fields are mutated.

    Returns:
        Snapshot of scheduled_at, expected_duration_minutes, where and
        signup_instructions.
    """
    return GameNotifySnapshot(
        scheduled_at=game.scheduled_at,
        expected_duration_minutes=game.expected_duration_minutes,
        where=game.where,
        signup_instructions=game.signup_instructions,
    )


def _format_time(dt: datetime) -> str:
    return f"<t:{to_unix_timestamp(dt)}:F>"


def _format_duration(minutes: int | None) -> str:
    return "not set" if minutes is None else f"{minutes} min"


def _format_text(text: str | None) -> str:
    return text or "(none)"


def _collect_changes(old: GameNotifySnapshot, game: GameSession) -> list[tuple[str, str, str]]:
    changes: list[tuple[str, str, str]] = []
    if old.scheduled_at != game.scheduled_at:
        changes.append(("Time", _format_time(old.scheduled_at), _format_time(game.scheduled_at)))
    if old.expected_duration_minutes != game.expected_duration_minutes:
        changes.append((
            "Duration",
            _format_duration(old.expected_duration_minutes),
            _format_duration(game.expected_duration_minutes),
        ))
    if (old.where or None) != (game.where or None):
        changes.append(("Location", _format_text(old.where), _format_text(game.where)))
    if (old.signup_instructions or None) != (game.signup_instructions or None):
        changes.append((
            "Signup Instructions",
            _format_text(old.signup_instructions),
            _format_text(game.signup_instructions),
        ))
    return changes


async def notify_participants_of_changes(
    db: AsyncSession, game: GameSession, old: GameNotifySnapshot
) -> set[str]:
    """Enqueue one send_dm per participant listing each changed notify field.

    Confirmed and waitlisted participants are both notified; placeholder
    participants (no Discord user) are skipped.

    Args:
        db: Async database session (caller must commit).
        game: Game session holding the post-edit values and participants.
        old: Snapshot captured before the edit.

    Returns:
        Discord IDs of the participants a DM was enqueued for.
    """
    changes = _collect_changes(old, game)
    if not changes:
        return set()

    game_time_unix = to_unix_timestamp(game.scheduled_at)
    message = DMFormats.game_updated(game.title, changes, jump_url=build_jump_url(game))

    notified: set[str] = set()
    for participant in game.participants:
        if participant.user is None:
            continue
        discord_id = participant.user.discord_id
        db.add(
            BotActionQueue(
                action_type="send_dm",
                game_id=game.id,
                discord_id=discord_id,
                payload={
                    "notification_type": "game_updated",
                    "game_title": game.title,
                    "game_time_unix": game_time_unix,
                    "message": message,
                },
            )
        )
        notified.add(discord_id)
        logger.info("Enqueued send_dm (game_updated) for user %s in game %s", discord_id, game.id)

    return notified

# Copyright 2025-2026 Bret McKee
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


"""
Event builder functions for scheduler daemon.

Each builder function constructs a BotActionQueue row from a schedule
model instance for insertion into the bot_action_queue table.
"""

import logging

from shared.models import GameStatusSchedule, NotificationSchedule
from shared.models.bot_action_queue import BotActionQueue

logger = logging.getLogger(__name__)


def build_notification_event(notification: NotificationSchedule) -> BotActionQueue:
    """
    Build a BotActionQueue row for a NOTIFICATION_DUE action.

    Args:
        notification: NotificationSchedule record

    Returns:
        BotActionQueue instance with action_type="notification_due"
    """
    return BotActionQueue(
        action_type="notification_due",
        game_id=str(notification.game_id),
        payload={
            "notification_type": notification.notification_type,
            "participant_id": notification.participant_id,
        },
    )


def build_status_transition_event(transition: GameStatusSchedule) -> BotActionQueue:
    """
    Build a BotActionQueue row for a GAME_STATUS_TRANSITION_DUE action.

    Status transitions never expire — they must eventually succeed to
    maintain database consistency.

    Args:
        transition: GameStatusSchedule record

    Returns:
        BotActionQueue instance with action_type="status_transition_due"
    """
    return BotActionQueue(
        action_type="status_transition_due",
        game_id=str(transition.game_id),
        payload={
            "target_status": transition.target_status,
            "transition_time": transition.transition_time.isoformat(),
        },
    )

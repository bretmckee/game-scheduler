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


"""Event builder for participant action scheduler daemon."""

from shared.models.bot_action_queue import BotActionQueue
from shared.models.participant_action_schedule import ParticipantActionSchedule


def build_participant_action_event(
    record: ParticipantActionSchedule,
) -> BotActionQueue:
    """
    Build a BotActionQueue row for a PARTICIPANT_DROP_DUE action.

    Args:
        record: ParticipantActionSchedule record with a pending "drop" action

    Returns:
        BotActionQueue instance with action_type="participant_drop_due"
    """
    return BotActionQueue(
        action_type="participant_drop_due",
        game_id=str(record.game_id),
        payload={
            "participant_id": record.participant_id,
        },
    )

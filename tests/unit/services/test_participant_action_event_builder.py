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


"""Unit tests for participant action event builder."""

from unittest.mock import MagicMock

from shared.models.bot_action_queue import BotActionQueue
from shared.services.participant_action_event_builder import (
    build_participant_action_event,
)


class TestBuildParticipantActionEvent:
    def test_returns_bot_action_queue_instance(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        result = build_participant_action_event(record)

        assert isinstance(result, BotActionQueue)

    def test_participant_drop_due_action_type(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        result = build_participant_action_event(record)

        assert result.action_type == "participant_drop_due"

    def test_game_id_stored_on_row(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        result = build_participant_action_event(record)

        assert result.game_id == "game-abc"

    def test_payload_contains_participant_id(self):
        record = MagicMock()
        record.game_id = "game-abc"
        record.participant_id = "participant-xyz"

        result = build_participant_action_event(record)

        assert result.payload["participant_id"] == "participant-xyz"

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


"""Tests for shared game-participation metrics."""

from unittest.mock import MagicMock, patch

from shared.services.game_metrics import record_game_joined, record_game_left


def test_record_game_joined_labels_action_and_source() -> None:
    """record_game_joined adds 1 with action='join' and the given source."""
    mock_counter = MagicMock()

    with patch("shared.services.game_metrics._game_participation_counter", mock_counter):
        record_game_joined("bot")

    mock_counter.add.assert_called_once_with(1, {"action": "join", "source": "bot"})


def test_record_game_left_labels_action_and_source() -> None:
    """record_game_left adds 1 with action='leave' and the given source."""
    mock_counter = MagicMock()

    with patch("shared.services.game_metrics._game_participation_counter", mock_counter):
        record_game_left("api")

    mock_counter.add.assert_called_once_with(1, {"action": "leave", "source": "api"})

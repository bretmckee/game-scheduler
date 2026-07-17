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


"""Shared game-participation metrics for join/leave actions.

Both the Discord bot (button interactions) and the API (frontend requests) let
users join and leave games through independent code paths. This module gives
both a single metric name and label taxonomy to record against, so the two
paths roll up to one queryable signal instead of drifting apart.
"""

from opentelemetry import metrics

_meter = metrics.get_meter(__name__)

_game_participation_counter = _meter.create_counter(
    name="game.participant.change",
    description="Number of game join/leave actions, labeled by action and source",
    unit="1",
)


def record_game_joined(source: str) -> None:
    """Record a successful game join.

    Args:
        source: Where the join originated — "bot" (Discord button) or "api"
            (frontend/direct API request).
    """
    _game_participation_counter.add(1, {"action": "join", "source": source})


def record_game_left(source: str) -> None:
    """Record a successful game leave.

    Args:
        source: Where the leave originated — "bot" (Discord button) or "api"
            (frontend/direct API request).
    """
    _game_participation_counter.add(1, {"action": "leave", "source": source})

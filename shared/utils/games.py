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


"""Game-related utilities and constants."""

DEFAULT_MAX_PLAYERS = 10
"""Default maximum number of players when max_players is not specified."""


def resolve_max_players(max_players_value: int | None) -> int:
    """
    Resolve max_players value, defaulting to DEFAULT_MAX_PLAYERS if None.

    This utility function provides a single place to handle the common pattern
    of: max_players = value or DEFAULT_MAX_PLAYERS

    Args:
        max_players_value: The max_players value to resolve (may be None)

    Returns:
        The max_players value if provided, otherwise DEFAULT_MAX_PLAYERS

    Example:
        >>> resolve_max_players(5)
        5
        >>> resolve_max_players(None)
        10
    """
    return max_players_value or DEFAULT_MAX_PLAYERS

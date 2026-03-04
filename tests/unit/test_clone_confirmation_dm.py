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


"""Unit tests for DMFormats.clone_confirmation message text."""

from shared.message_formats import DMFormats

GAME_TITLE = "Weekend Dungeon Crawl"
DEADLINE_UNIX = 1777777777


def test_clone_confirmation_includes_game_title():
    """Message must include the game title."""
    msg = DMFormats.clone_confirmation(GAME_TITLE, DEADLINE_UNIX)
    assert GAME_TITLE in msg


def test_clone_confirmation_includes_deadline():
    """Message must reference the deadline as a Discord timestamp."""
    msg = DMFormats.clone_confirmation(GAME_TITLE, DEADLINE_UNIX)
    assert str(DEADLINE_UNIX) in msg


def test_clone_confirmation_includes_confirm_prompt():
    """Message must prompt the participant to confirm their spot."""
    msg = DMFormats.clone_confirmation(GAME_TITLE, DEADLINE_UNIX)
    assert "confirm" in msg.lower()

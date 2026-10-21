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


"""Tests pinning the project's length limits to Discord's embed limits."""

from shared.utils.limits import (
    DISCORD_EMBED_DESCRIPTION_LIMIT,
    DISCORD_EMBED_TOTAL_LIMIT,
    DISCORD_EMBED_TOTAL_SAFE_LIMIT,
    MAX_DESCRIPTION_LENGTH,
)


def test_max_description_length_fits_in_an_embed_description():
    """The description is posted verbatim as the embed description, which Discord caps."""
    assert MAX_DESCRIPTION_LENGTH <= DISCORD_EMBED_DESCRIPTION_LIMIT


def test_discord_embed_description_limit_value():
    """Discord's documented embed description limit."""
    assert DISCORD_EMBED_DESCRIPTION_LIMIT == 4096


def test_safe_total_limit_leaves_headroom_below_discord_total():
    """The trim budget must sit below Discord's whole-embed cap."""
    assert DISCORD_EMBED_TOTAL_SAFE_LIMIT < DISCORD_EMBED_TOTAL_LIMIT

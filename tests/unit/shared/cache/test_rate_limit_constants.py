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


"""Unit tests for Discord rate limit constants in shared.cache.ttl."""


class TestDiscordRateLimitConstants:
    """Verify Discord rate limit budget constants are present and correct."""

    def test_background_constant_value(self) -> None:
        """DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND matches the existing Lua default of 25."""
        from shared.cache.ttl import DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND  # noqa: PLC0415

        assert DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND == 25

    def test_interactive_constant_value(self) -> None:
        """DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE allows up to 45 req/s for user-facing requests."""
        from shared.cache.ttl import DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE  # noqa: PLC0415

        assert DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE == 45

    def test_interactive_exceeds_background(self) -> None:
        """Interactive budget is higher than background to prioritise user-facing requests."""
        from shared.cache.ttl import (  # noqa: PLC0415
            DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND,
            DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE,
        )

        assert DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE > DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND

    def test_constants_are_integers(self) -> None:
        """Both constants are plain int values."""
        from shared.cache.ttl import (  # noqa: PLC0415
            DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND,
            DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE,
        )

        assert isinstance(DISCORD_GLOBAL_RATE_LIMIT_BACKGROUND, int)
        assert isinstance(DISCORD_GLOBAL_RATE_LIMIT_INTERACTIVE, int)

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


"""Unit tests for EmojiResolver service."""

from unittest.mock import AsyncMock

import pytest

from services.api.services.emoji_resolver import EmojiResolver, render_emoji_for_display
from shared.discord.client import DiscordAPIClient, DiscordAPIError


def _make_client(emojis: list[dict]) -> DiscordAPIClient:
    client = DiscordAPIClient.__new__(DiscordAPIClient)
    client.get_guild_emojis = AsyncMock(return_value=emojis)
    return client


class TestEmojiResolver:
    """Tests for EmojiResolver.resolve_emoji_mentions."""

    @pytest.mark.asyncio
    async def test_resolves_static_emoji(self) -> None:
        """Static :emoji_name: replaced with <:name:id>."""
        client = _make_client([{"id": "111", "name": "wave", "animated": False}])
        resolver = EmojiResolver(discord_client=client)

        result, errors = await resolver.resolve_emoji_mentions("Hello :wave: world", "guild1")

        assert result == "Hello <:wave:111> world"
        assert errors == []

    @pytest.mark.asyncio
    async def test_resolves_animated_emoji(self) -> None:
        """Animated :emoji_name: replaced with <a:name:id>."""
        client = _make_client([{"id": "222", "name": "dance", "animated": True}])
        resolver = EmojiResolver(discord_client=client)

        result, errors = await resolver.resolve_emoji_mentions(":dance: to the beat", "guild1")

        assert result == "<a:dance:222> to the beat"
        assert errors == []

    @pytest.mark.asyncio
    async def test_unknown_emoji_passes_through(self) -> None:
        """Unknown :emoji_name: passes through unchanged without error."""
        client = _make_client([{"id": "111", "name": "wave", "animated": False}])
        resolver = EmojiResolver(discord_client=client)

        result, errors = await resolver.resolve_emoji_mentions("no :unknown: here", "guild1")

        assert result == "no :unknown: here"
        assert errors == []

    @pytest.mark.asyncio
    async def test_text_without_emoji_patterns_returned_unchanged(self) -> None:
        """Text with no :word: patterns is returned unchanged."""
        client = _make_client([])
        resolver = EmojiResolver(discord_client=client)

        result, errors = await resolver.resolve_emoji_mentions("plain text", "guild1")

        assert result == "plain text"
        assert errors == []

    @pytest.mark.asyncio
    async def test_cache_miss_returns_text_unchanged(self) -> None:
        """When emoji cache is cold (503), text is returned unchanged without error."""
        client = DiscordAPIClient.__new__(DiscordAPIClient)
        client.get_guild_emojis = AsyncMock(side_effect=DiscordAPIError(503, "Bot not connected"))
        resolver = EmojiResolver(discord_client=client)

        result, errors = await resolver.resolve_emoji_mentions(":wave: hello", "guild1")

        assert result == ":wave: hello"
        assert errors == []


class TestRenderEmojiForDisplay:
    """Tests for render_emoji_for_display."""

    def test_static_emoji_converted_to_shorthand(self) -> None:
        """<:name:id> is replaced with :name:."""
        assert render_emoji_for_display("Hello <:wave:111> world") == "Hello :wave: world"

    def test_animated_emoji_converted_to_shorthand(self) -> None:
        """<a:name:id> is replaced with :name:."""
        assert render_emoji_for_display("<a:dance:222> to the beat") == ":dance: to the beat"

    def test_multiple_emojis_all_converted(self) -> None:
        """Multiple stored emoji tokens are all converted."""
        assert render_emoji_for_display("<:a:1> and <a:b:2>") == ":a: and :b:"

    def test_no_emoji_tokens_returned_unchanged(self) -> None:
        """Text with no stored tokens is returned unchanged."""
        assert render_emoji_for_display("plain text") == "plain text"

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert render_emoji_for_display(None) is None

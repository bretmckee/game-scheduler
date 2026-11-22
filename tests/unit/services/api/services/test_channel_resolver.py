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


"""Unit tests for channel resolver service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.services import channel_resolver as resolver_module
from services.api.services import participant_resolver as participant_resolver_module
from shared.discord import client as discord_client_module


@pytest.fixture
def mock_discord_client():
    """Create mock Discord API client."""
    client = MagicMock(spec=discord_client_module.DiscordAPIClient)
    client.bot_token = "test_bot_token"
    return client


@pytest.fixture
def resolver(mock_discord_client):
    """Create channel resolver instance."""
    return resolver_module.ChannelResolver(mock_discord_client)


@pytest.mark.asyncio
async def test_resolve_single_channel_match(resolver, mock_discord_client):
    """Test #channel mention with single channel match."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
            {"id": "987654321", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_multiple_channel_matches(resolver, mock_discord_client):
    """Test #channel mention with multiple matching channels (disambiguation needed)."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "General", "type": 0},
            {"id": "333333333", "name": "GENERAL", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #general"
    assert len(errors) == 1
    assert errors[0]["type"] == "ambiguous"
    assert errors[0]["input"] == "#general"
    assert len(errors[0]["suggestions"]) == 3
    assert any(s["name"] == "general" for s in errors[0]["suggestions"])


@pytest.mark.asyncio
async def test_resolve_channel_not_found(resolver, mock_discord_client):
    """Test #channel mention when channel doesn't exist."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
            {"id": "987654321", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #nonexistent",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #nonexistent"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#nonexistent"
    assert "suggestions" in errors[0]


@pytest.mark.asyncio
async def test_resolve_channel_with_special_characters(resolver, mock_discord_client):
    """Test #channel mention with hyphens and underscores."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "game-planning", "type": 0},
            {"id": "987654321", "name": "off_topic", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #game-planning",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_mixed_content_with_channel(resolver, mock_discord_client):
    """Test location text with plain text and channel mention."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "voice-lobby", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Join #voice-lobby at 7pm EST",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Join <#123456789> at 7pm EST"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_empty_location_text(resolver, mock_discord_client):
    """Test empty location text returns unchanged."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="",
        guild_discord_id="guild123",
    )

    assert resolved_text == ""
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_plain_text_without_mentions(resolver, mock_discord_client):
    """Test plain text without channel mentions returns unchanged."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet at Discord voice channel 2",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet at Discord voice channel 2"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_multiple_mentions_in_one_location(resolver, mock_discord_client):
    """Test multiple #channel mentions in single location string."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "voice-lobby", "type": 0},
            {"id": "333333333", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Start in #general then move to #voice-lobby",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Start in <#111111111> then move to <#222222222>"


# ---------------------------------------------------------------------------
# Discord channel URL detection tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_discord_url_same_guild(resolver, mock_discord_client):
    """Valid same-guild discord.com channel URL is replaced with <#channel_id>."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/406583674453098496",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "<#406583674453098496>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_wrong_guild_passes_through(resolver, mock_discord_client):
    """discord.com URL from a different guild is left unchanged with no error."""
    url = "https://discord.com/channels/999999999999999999/406583674453098496"
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=url,
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == url
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_channel_not_found(resolver, mock_discord_client):
    """Same-guild discord.com URL for a non-existent text channel returns not_found error."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/999999999999999999",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "https://discord.com/channels/111222333444555666/999999999999999999"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert (
        errors[0]["input"] == "https://discord.com/channels/111222333444555666/999999999999999999"
    )
    assert errors[0]["reason"] == (
        "Your Location contains a link to a channel that is not a text channel or thread "
        "the bot can see in this server. The bot must have access to it; private "
        "threads and channels it cannot view cannot be linked."
    )
    assert errors[0]["field"] == "Location"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_discord_url_non_text_channel_not_found(resolver, mock_discord_client):
    """Same-guild discord.com URL for a non-text channel (type != 0) returns not_found."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "general", "type": 0},
            {"id": "777777777777777777", "name": "voice-chat", "type": 2},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/777777777777777777",
        guild_discord_id="111222333444555666",
    )

    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["suggestions"] == []


@pytest.mark.asyncio
async def test_resolve_discord_url_coexisting_with_hash_mention(resolver, mock_discord_client):
    """discord.com URL and a #channel mention in the same string both resolve correctly."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "406583674453098496", "name": "voice-lobby", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=(
            "Start at #general then https://discord.com/channels/GUILD/406583674453098496"
        ).replace("GUILD", "999999999999999999"),
        guild_discord_id="999999999999999999",
    )

    assert resolved_text == "Start at <#111111111> then <#406583674453098496>"
    assert len(errors) == 0
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_channel_at_text_start(resolver, mock_discord_client):
    """Test #channel mention at start of location text."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="#general at 7pm",
        guild_discord_id="guild123",
    )

    assert resolved_text == "<#123456789> at 7pm"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_channel_at_text_end(resolver, mock_discord_client):
    """Test #channel mention at end of location text."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet at #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet at <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_adjacent_channel_mentions(resolver, mock_discord_client):
    """Test adjacent #channel mentions without separator."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="#general #announcements",
        guild_discord_id="guild123",
    )

    assert resolved_text == "<#111111111> <#222222222>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_with_empty_guild_channel_list(resolver, mock_discord_client):
    """Test handling when guild has no channels."""
    mock_discord_client.get_guild_channels = AsyncMock(return_value=[])

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #general"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#general"
    assert len(errors[0]["suggestions"]) == 0


@pytest.mark.asyncio
async def test_resolve_filters_non_text_channels(resolver, mock_discord_client):
    """Test that only text channels (type=0) are considered."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "General Voice", "type": 2},
            {"id": "333333333", "name": "general-category", "type": 4},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_case_insensitive_matching(resolver, mock_discord_client):
    """Test case-insensitive channel name matching."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "General", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #GENERAL",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#123456789>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_mixed_valid_and_invalid_channels(resolver, mock_discord_client):
    """Test location with both valid and invalid channel mentions."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Start in #general then #nonexistent",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Start in <#123456789> then #nonexistent"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#nonexistent"


# ---------------------------------------------------------------------------
# Bug fix regression tests (xfail until fixed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_emoji_unicode_channel_name(resolver, mock_discord_client):
    """Emoji-prefixed channel name like #🍻tavern-generalchat should resolve correctly."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "🍻tavern-generalchat", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #🍻tavern-generalchat",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#406497579061215235>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_snowflake_token_valid_id(resolver, mock_discord_client):
    """<#id> token with a valid guild channel ID should pass through silently with no errors."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "🍻tavern-generalchat", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#406497579061215235>",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#406497579061215235>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_snowflake_token_unknown_id(resolver, mock_discord_client):
    """<#id> token with an ID not in the guild should produce a not_found error."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406497579061215235", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#999999999999999999>",
        guild_discord_id="guild123",
        field_label="Description",
    )

    assert resolved_text == "Meet in <#999999999999999999>"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "<#999999999999999999>"
    assert errors[0]["field"] == "Description"
    assert errors[0]["reason"] == (
        "Your Description contains <#999999999999999999>, which is not a text channel "
        "or thread the bot can see in this server. The bot must have access to it; "
        "private threads and channels it cannot view cannot be linked."
    )


# ---------------------------------------------------------------------------
# Markdown heading passthrough tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_markdown_h2_heading_passes_through_unchanged(resolver, mock_discord_client):
    """'## Heading' markdown is not parsed as a channel mention attempt."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="## Session Zero",
        guild_discord_id="guild123",
    )

    assert resolved_text == "## Session Zero"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_markdown_h3_heading_passes_through_unchanged(resolver, mock_discord_client):
    """'### Heading' markdown is not parsed as a channel mention attempt."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="### Rewards\nGold and a magic item",
        guild_discord_id="guild123",
    )

    assert resolved_text == "### Rewards\nGold and a magic item"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_markdown_heading_mid_text_passes_through_unchanged(resolver, mock_discord_client):
    """A markdown heading later in multi-line text is also left alone."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    text = "Welcome!\n## What to bring\nDice and a character sheet"
    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=text,
        guild_discord_id="guild123",
    )

    assert resolved_text == text
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_double_hash_immediately_followed_by_channel_name_still_resolves(
    resolver, mock_discord_client
):
    """A stray leading '#' before a real channel mention still resolves the channel."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="##general",
        guild_discord_id="guild123",
    )

    assert resolved_text == "#<#123456789>"
    assert len(errors) == 0


# ---------------------------------------------------------------------------
# Integer token passthrough tests (Task 2.1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_integer_hash_token_passes_through_unchanged(resolver, mock_discord_client):
    """#<integer> tokens pass through without error when no channel with that name exists."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="See step #1 for details",
        guild_discord_id="guild123",
    )

    assert resolved_text == "See step #1 for details"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_multiple_integer_hash_tokens_pass_through(resolver, mock_discord_client):
    """Multiple #<integer> tokens all pass through without errors."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Steps: #1 then #42 then #100",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Steps: #1 then #42 then #100"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_non_integer_unknown_channel_still_errors(resolver, mock_discord_client):
    """#<non-integer> tokens that don't match a channel name still produce not_found errors."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "general", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #unknown-channel",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in #unknown-channel"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#unknown-channel"


# ---------------------------------------------------------------------------
# Stray '<' bug-fix regression tests (mirrors participant_resolver's @mention fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_malformed_stray_angle_bracket_mention_is_still_scanned(
    resolver, mock_discord_client
):
    """
    A stray '<' glued to a genuine #channel_name mention must not hide it from scanning.

    The scanner must skip a '#' only when it is part of a genuine already-resolved
    <#digits> token, not merely because some '<' precedes it. Malformed input like
    "<#general" (a stray '<' immediately before a genuine #channel_name, with no
    digits/'>' to close it) does not form a valid <#digits> token, so "#general"
    must still be scanned as a real candidate mention -- and since no channel named
    "general" exists here, it is reported as not_found, exactly like a normal
    standalone unknown #mention elsewhere in this file.
    """
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "123456789", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#general more",
        guild_discord_id="guild123",
    )

    # "#general" is left unresolved in the text (no match found) but is now
    # actually scanned and reported, unlike before the fix.
    assert resolved_text == "Meet in <#general more"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "#general"


@pytest.mark.asyncio
async def test_resolve_snowflake_token_adjacent_to_new_hash_mention(resolver, mock_discord_client):
    """A resolved <#id> token abutting a new #channel_name mention: both handled independently."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "111111111", "name": "general", "type": 0},
            {"id": "222222222", "name": "announcements", "type": 0},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="<#111111111>#announcements",
        guild_discord_id="guild123",
    )

    assert resolved_text == "<#111111111><#222222222>"
    assert errors == []


@pytest.mark.asyncio
async def test_resolve_angle_wrapped_channel_name_resolves_to_single_token(
    resolver, mock_discord_client
):
    """<#name> (name typed inside Discord's mention brackets) resolves to <#id>."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[{"id": "111111111", "name": "general", "type": 0}]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#general> tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111> tonight"
    assert errors == []


@pytest.mark.asyncio
async def test_unknown_angle_wrapped_channel_name_reports_typed_token(
    resolver, mock_discord_client
):
    """The error input is the exact typed token so the UI can substitute a suggestion."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[{"id": "123456789", "name": "announcements", "type": 0}]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#general> tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#general> tonight"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "<#general>"


@pytest.mark.asyncio
async def test_stray_open_bracket_before_known_channel_name_resolves_cleanly(
    resolver, mock_discord_client
):
    """An unclosed '<' glued to a known #name is consumed, not left doubled."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[{"id": "111111111", "name": "general", "type": 0}]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <#general more",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111> more"
    assert errors == []


def _guild_with_general(mock_discord_client) -> None:
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[{"id": "111111111", "name": "general", "type": 0}]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", ["<# 111111111>", "<#111111111 >", "<#  111111111  >"])
async def test_spaced_channel_id_token_is_normalized(resolver, mock_discord_client, typed):
    """Whitespace inside a <#id> token is removed so Discord renders the mention."""
    _guild_with_general(mock_discord_client)

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=f"Meet in {typed} tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111> tonight"
    assert errors == []


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", ["<# general>", "<#general >", "<#  general  >"])
async def test_spaced_channel_name_token_resolves_to_id(resolver, mock_discord_client, typed):
    """Whitespace inside a <#name> token is ignored and the name is resolved to <#id>."""
    _guild_with_general(mock_discord_client)

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text=f"Meet in {typed} tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#111111111> tonight"
    assert errors == []


@pytest.mark.asyncio
async def test_unknown_spaced_channel_id_reports_typed_token(resolver, mock_discord_client):
    """An unknown spaced ID is reported under the exact typed text, left unchanged."""
    _guild_with_general(mock_discord_client)

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <# 999999999> tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <# 999999999> tonight"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "<# 999999999>"


@pytest.mark.asyncio
async def test_unknown_spaced_channel_name_reports_typed_token(resolver, mock_discord_client):
    """An unknown spaced name is reported under the exact typed text, left unchanged."""
    _guild_with_general(mock_discord_client)

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in <# nowhere> tonight",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <# nowhere> tonight"
    assert len(errors) == 1
    assert errors[0]["type"] == "not_found"
    assert errors[0]["input"] == "<# nowhere>"


@pytest.mark.asyncio
async def test_angle_text_with_inner_spaces_is_not_a_channel_mention(resolver, mock_discord_client):
    """'<# 5 players>' is ordinary text, not a mention: no rewrite and no error."""
    _guild_with_general(mock_discord_client)

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Bring <# 5 players> along",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Bring <# 5 players> along"
    assert errors == []


# ---------------------------------------------------------------------------
# Thread link support (a link/mention to a Discord thread, not just a channel)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_discord_url_public_thread_resolves(resolver, mock_discord_client):
    """A discord.com URL pointing at a public thread resolves like a regular channel."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "session-zero-planning", "type": 11},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/406583674453098496",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "<#406583674453098496>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_private_thread_resolves(resolver, mock_discord_client):
    """A discord.com URL pointing at a private thread resolves like a regular channel."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098497", "name": "dm-thread", "type": 12},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/406583674453098497",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "<#406583674453098497>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_discord_url_announcement_thread_resolves(resolver, mock_discord_client):
    """A discord.com URL pointing at an announcement-channel thread also resolves."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098498", "name": "patch-notes-thread", "type": 10},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="https://discord.com/channels/111222333444555666/406583674453098498",
        guild_discord_id="111222333444555666",
    )

    assert resolved_text == "<#406583674453098498>"
    assert len(errors) == 0


@pytest.mark.asyncio
async def test_resolve_hash_mention_matches_thread_name(resolver, mock_discord_client):
    """A #name mention can also resolve to a thread, not just a top-level text channel."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[
            {"id": "406583674453098496", "name": "session-zero-planning", "type": 11},
        ]
    )

    resolved_text, errors = await resolver.resolve_channel_mentions(
        location_text="Meet in #session-zero-planning",
        guild_discord_id="guild123",
    )

    assert resolved_text == "Meet in <#406583674453098496>"
    assert len(errors) == 0


def test_render_where_display_none_input():
    """render_where_display returns None when where is None."""
    result = resolver_module.render_where_display(None, [{"id": "123", "name": "general"}])
    assert result is None


def test_render_where_display_plain_text_returns_none():
    """render_where_display returns None for plain text with no channel tokens."""
    result = resolver_module.render_where_display("The Rusty Flagon, table 3", [])
    assert result is None


def test_render_where_display_replaces_tokens():
    """render_where_display replaces <#id> tokens with #name using provided channel list."""
    channels = [
        {"id": "123", "name": "foo", "type": 0},
        {"id": "456", "name": "bar", "type": 0},
    ]
    result = resolver_module.render_where_display("<#123> and <#456>", channels)
    assert result == "#foo and #bar"


# --- extract_user_mention_ids ---


def test_extract_user_mention_ids_none_input():
    """extract_user_mention_ids returns empty set for None."""
    assert resolver_module.extract_user_mention_ids(None) == set()


def test_extract_user_mention_ids_empty_string():
    """extract_user_mention_ids returns empty set for empty string."""
    assert resolver_module.extract_user_mention_ids("") == set()


def test_extract_user_mention_ids_no_tokens():
    """extract_user_mention_ids returns empty set when text has no <@id> tokens."""
    assert resolver_module.extract_user_mention_ids("hello world #general") == set()


def test_extract_user_mention_ids_finds_ids():
    """extract_user_mention_ids returns all snowflake IDs found in text."""
    text = "Thanks <@111> and <@222> for signing up"
    assert resolver_module.extract_user_mention_ids(text) == {"111", "222"}


def test_extract_user_mention_ids_deduplicates():
    """extract_user_mention_ids deduplicates repeated IDs."""
    text = "<@111> and again <@111>"
    assert resolver_module.extract_user_mention_ids(text) == {"111"}


# --- render_mention_tokens ---


def test_render_mention_tokens_none_input():
    """None text renders to None."""
    assert resolver_module.render_mention_tokens(None, {}, {}) is None


def test_render_mention_tokens_token_free_text_unchanged():
    """Text without tokens is returned byte-for-byte."""
    text = "Bring dice @bob #general <@notdigits> <#also-not>"
    assert resolver_module.render_mention_tokens(text, {}, {"1": "x"}) == text


def test_render_mention_tokens_live_member_and_channel():
    """Known member and channel IDs gain their label after a pipe."""
    result = resolver_module.render_mention_tokens(
        "Ask <@111> in <#222>", {"111": "Kallisti of the Ruby Rose"}, {"222": "lfg"}
    )
    assert result == "Ask <@111|Kallisti of the Ruby Rose> in <#222|lfg>"


def test_render_mention_tokens_departed_member_has_empty_label():
    """A member that maps to None renders the empty-label departed marker."""
    result = resolver_module.render_mention_tokens("Ask <@111>", {"111": None}, {})
    assert result == "Ask <@111|>"


def test_render_mention_tokens_unknown_channel_has_empty_label():
    """A channel ID missing from a known channel list renders the empty-label marker."""
    result = resolver_module.render_mention_tokens("Go to <#999>", {}, {"222": "lfg"})
    assert result == "Go to <#999|>"


def test_render_mention_tokens_strips_closing_angle_from_labels():
    """Every '>' is removed from labels so the token stays parseable."""
    result = resolver_module.render_mention_tokens(
        "<@111> <#222>", {"111": ">a>b>"}, {"222": "c>d"}
    )
    assert result == "<@111|ab> <#222|cd>"


# --- collapse_mention_tokens ---


class TestCollapseMentionTokens:
    """Labeled <@id|label> / <#id|label> tokens collapse to the stored bare form."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("<@123|Kallisti of the Ruby Rose>", "<@123>"),
            ("<@123|>", "<@123>"),
            ("<#456|lfg>", "<#456>"),
            ("<#456|>", "<#456>"),
        ],
    )
    def test_labeled_token_collapses_to_bare_token(self, text, expected):
        assert resolver_module.collapse_mention_tokens(text) == expected

    @pytest.mark.parametrize(
        "label",
        ["@alice", "Bob (GM)", "a|b", "Kallisti of the Ruby Rose", "\U0001f3b2 dice"],
    )
    def test_label_with_special_characters_collapses(self, label):
        text = f"Ask <@123|{label}> in <#456|{label}> now"
        assert resolver_module.collapse_mention_tokens(text) == "Ask <@123> in <#456> now"

    def test_multiple_tokens_in_text_all_collapse(self):
        text = "<@1|A> and <@2|B> meet in <#3|lfg> or <#4|>"
        assert resolver_module.collapse_mention_tokens(text) == "<@1> and <@2> meet in <#3> or <#4>"

    @pytest.mark.parametrize(
        "text",
        [
            "Ask <@123> in <#456>",
            "Ask @alice in #general",
            "Wave :wave: and <:wave:789>",
            "## Heading and <@abc|label>",
            "",
        ],
    )
    def test_text_without_labeled_tokens_is_unchanged(self, text):
        assert resolver_module.collapse_mention_tokens(text) == text

    def test_none_returns_none(self):
        assert resolver_module.collapse_mention_tokens(None) is None


@pytest.mark.asyncio
async def test_collapsed_user_token_is_skipped_by_mention_scanner():
    """A collapsed user token is a resolved <@id>, not an @<digits> username candidate."""
    text = resolver_module.collapse_mention_tokens("Ask <@123|Kallisti of the Ruby Rose> first")

    (
        resolved,
        errors,
    ) = await participant_resolver_module.ParticipantResolver().resolve_mentions_in_text(
        text, "guild123"
    )

    assert resolved == "Ask <@123> first"
    assert errors == []


@pytest.mark.asyncio
async def test_collapsed_channel_token_is_not_scanned_as_channel_name(
    resolver, mock_discord_client
):
    """A collapsed channel token validates by ID instead of matching "id|name" as a name."""
    mock_discord_client.get_guild_channels = AsyncMock(
        return_value=[{"id": "456", "name": "lfg", "type": 0}]
    )
    text = resolver_module.collapse_mention_tokens("Meet in <#456|lfg> tonight")

    resolved, errors = await resolver.resolve_channel_mentions(text, "guild123")

    assert resolved == "Meet in <#456> tonight"
    assert errors == []

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


"""Tests for Discord formatting utilities."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.bot.utils.discord_format import (
    _build_avatar_url,
    format_discord_mention,
    format_discord_timestamp,
    format_duration,
    format_game_status_emoji,
    format_participant_list,
    format_rules_section,
    format_user_or_placeholder,
    get_member_display_info,
)
from shared.discord.client import DiscordAPIError


class TestFormatUserOrPlaceholder:
    """Tests for format_user_or_placeholder function."""

    def test_formats_discord_id_as_mention(self):
        """Test that numeric Discord IDs are formatted as mentions."""
        result = format_user_or_placeholder("123456789012345678")
        assert result == "<@123456789012345678>"

    def test_returns_placeholder_name_unchanged(self):
        """Test that placeholder names are returned as-is."""
        result = format_user_or_placeholder("placeholder")
        assert result == "placeholder"

    def test_returns_alphanumeric_placeholder_unchanged(self):
        """Test that alphanumeric placeholders are returned as-is."""
        result = format_user_or_placeholder("Player123")
        assert result == "Player123"

    def test_handles_mixed_content_placeholder(self):
        """Test that strings with letters are treated as placeholders."""
        result = format_user_or_placeholder("Host-12abc")
        assert result == "Host-12abc"


class TestFormatDiscordMention:
    """Tests for format_discord_mention function."""

    def test_formats_mention_correctly(self):
        """Test that mention is formatted with proper syntax."""
        user_id = "123456789012345678"
        result = format_discord_mention(user_id)
        assert result == "<@123456789012345678>"

    def test_handles_different_id_lengths(self):
        """Test formatting with various ID lengths."""
        result = format_discord_mention("12345")
        assert result == "<@12345>"


class TestFormatDiscordTimestamp:
    """Tests for format_discord_timestamp function."""

    def test_formats_timestamp_with_default_style(self):
        """Test timestamp formatting with default Full style."""
        dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        result = format_discord_timestamp(dt)
        assert result == "<t:1763233200:F>"

    def test_formats_timestamp_with_relative_style(self):
        """Test timestamp formatting with Relative style."""
        dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        result = format_discord_timestamp(dt, style="R")
        assert result == "<t:1763233200:R>"

    def test_formats_timestamp_with_short_date_style(self):
        """Test timestamp formatting with short date style."""
        dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        result = format_discord_timestamp(dt, style="d")
        assert result == "<t:1763233200:d>"

    def test_formats_timestamp_with_time_only_style(self):
        """Test timestamp formatting with time only style."""
        dt = datetime(2025, 11, 15, 19, 0, 0, tzinfo=UTC)
        result = format_discord_timestamp(dt, style="T")
        assert result == "<t:1763233200:T>"


class TestFormatParticipantList:
    """Tests for format_participant_list function."""

    def test_formats_single_participant(self):
        """Test formatting a single participant."""
        participants = ["123456789012345678"]
        result = format_participant_list(participants)
        assert result == "1. <@123456789012345678>"

    def test_formats_multiple_participants(self):
        """Test formatting multiple participants."""
        participants = [
            "111111111111111111",
            "222222222222222222",
            "333333333333333333",
        ]
        result = format_participant_list(participants)
        expected = "1. <@111111111111111111>\n2. <@222222222222222222>\n3. <@333333333333333333>"
        assert result == expected

    def test_handles_empty_list(self):
        """Test handling empty participant list."""
        result = format_participant_list([])
        assert result == "No participants yet"

    def test_truncates_long_list(self):
        """Test truncation of long participant lists."""
        participants = [f"{i:018d}" for i in range(15)]
        result = format_participant_list(participants, max_display=10)
        assert "... and 5 more" in result
        assert result.count("<@") == 10

    def test_truncates_without_count_when_disabled(self):
        """Test truncation without count suffix."""
        participants = [f"{i:018d}" for i in range(15)]
        result = format_participant_list(participants, max_display=10, include_count=False)
        assert "... and" not in result
        assert result.count("<@") == 10

    def test_custom_start_number(self):
        """Test numbering starts from custom start_number."""
        participants = ["111111111111111111", "222222222222222222"]
        result = format_participant_list(participants, start_number=5)
        assert "5. <@111111111111111111>" in result
        assert "6. <@222222222222222222>" in result
        assert "1." not in result

    def test_start_number_for_waitlist_continuation(self):
        """Test waitlist numbering continues from signup count."""
        waitlist = ["999999999999999999"]
        result = format_participant_list(waitlist, start_number=4)
        assert "4. <@999999999999999999>" in result


class TestFormatGameStatusEmoji:
    """Tests for format_game_status_emoji function."""

    def test_scheduled_status(self):
        """Test emoji for scheduled status."""
        result = format_game_status_emoji("SCHEDULED")
        assert result == "📅"

    def test_in_progress_status(self):
        """Test emoji for in progress status."""
        result = format_game_status_emoji("IN_PROGRESS")
        assert result == "🎮"

    def test_completed_status(self):
        """Test emoji for completed status."""
        result = format_game_status_emoji("COMPLETED")
        assert result == "✅"

    def test_cancelled_status(self):
        """Test emoji for cancelled status."""
        result = format_game_status_emoji("CANCELLED")
        assert result == "❌"

    def test_unknown_status(self):
        """Test emoji for unknown status."""
        result = format_game_status_emoji("UNKNOWN")
        assert result == "❓"


class TestFormatDuration:
    """Tests for format_duration function."""

    def test_formats_hours_and_minutes(self):
        """Test formatting duration with both hours and minutes."""
        result = format_duration(150)
        assert result == "2h 30m"

    def test_formats_hours_only(self):
        """Test formatting duration with only hours."""
        result = format_duration(120)
        assert result == "2h"

    def test_formats_minutes_only(self):
        """Test formatting duration with only minutes."""
        result = format_duration(45)
        assert result == "45m"

    def test_formats_one_hour(self):
        """Test formatting duration of exactly one hour."""
        result = format_duration(60)
        assert result == "1h"

    def test_handles_none(self):
        """Test handling None value."""
        result = format_duration(None)
        assert result == ""

    def test_handles_zero(self):
        """Test handling zero minutes."""
        result = format_duration(0)
        assert result == ""

    def test_handles_negative(self):
        """Test handling negative minutes."""
        result = format_duration(-30)
        assert result == ""

    def test_formats_large_duration(self):
        """Test formatting large duration."""
        result = format_duration(390)
        assert result == "6h 30m"


class TestBuildAvatarUrl:
    """Tests for _build_avatar_url function."""

    def test_member_avatar_static(self):
        """Test building URL for static guild-specific member avatar."""
        result = _build_avatar_url("123", "456", "abc123", None)
        assert "guilds/456/users/123/avatars/abc123.png" in result

    def test_member_avatar_animated(self):
        """Test building URL for animated (gif) guild-specific member avatar."""
        result = _build_avatar_url("123", "456", "a_abc123", None)
        assert ".gif" in result

    def test_user_avatar_static(self):
        """Test building URL for static user global avatar."""
        result = _build_avatar_url("123", "456", None, "def456")
        assert "avatars/123/def456.png" in result

    def test_user_avatar_animated(self):
        """Test building URL for animated user global avatar."""
        result = _build_avatar_url("123", "456", None, "a_def456")
        assert ".gif" in result

    def test_default_avatar_fallback(self):
        """Test fallback to default Discord embed avatar when no avatar set."""
        result = _build_avatar_url("123456789012345678", "456", None, None)
        assert "embed/avatars/" in result
        assert result is not None

    def test_invalid_user_id_returns_none(self):
        """Test that non-numeric user_id returns None when no avatar set."""
        result = _build_avatar_url("not-a-number", "456", None, None)
        assert result is None

    def test_member_avatar_takes_priority(self):
        """Test that member avatar takes priority over user avatar."""
        result = _build_avatar_url("123", "456", "member_hash", "user_hash")
        assert "guilds/" in result
        assert "avatars/123/user_hash" not in result


class TestFormatRulesSection:
    """Tests for format_rules_section function."""

    def test_returns_placeholder_for_none(self):
        """Test that None rules returns no-rules placeholder."""
        result = format_rules_section(None)
        assert result == "No rules specified"

    def test_returns_placeholder_for_empty_string(self):
        """Test that empty string returns no-rules placeholder."""
        result = format_rules_section("")
        assert result == "No rules specified"

    def test_returns_placeholder_for_whitespace(self):
        """Test that whitespace-only string returns no-rules placeholder."""
        result = format_rules_section("   ")
        assert result == "No rules specified"

    def test_returns_short_rules_unchanged(self):
        """Test that short rules text is returned unchanged."""
        rules = "No cell phones."
        result = format_rules_section(rules)
        assert result == rules

    def test_truncates_long_rules(self):
        """Test that rules longer than max_length are truncated with ellipsis."""
        rules = "x" * 600
        result = format_rules_section(rules)
        assert len(result) == 500
        assert result.endswith("...")

    def test_custom_max_length(self):
        """Test truncation respects custom max_length."""
        rules = "x" * 200
        result = format_rules_section(rules, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")


class TestGetMemberDisplayInfo:
    """Tests for get_member_display_info async function."""

    @pytest.mark.asyncio
    async def test_returns_nick_and_avatar_when_found(self):
        """Test successful member lookup returns nick and avatar URL."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.return_value = {
            "nick": "CoolNick",
            "avatar": None,
            "user": {"username": "user123", "global_name": None, "avatar": "abc"},
        }
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name == "CoolNick"
        assert avatar is not None

    @pytest.mark.asyncio
    async def test_returns_global_name_when_no_nick(self):
        """Test fallback to global_name when nick is absent."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.return_value = {
            "nick": None,
            "avatar": None,
            "user": {
                "username": "user123",
                "global_name": "GlobalUser",
                "avatar": None,
            },
        }
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name == "GlobalUser"

    @pytest.mark.asyncio
    async def test_returns_none_when_member_not_found(self):
        """Test that None is returned when member lookup returns empty."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.return_value = None
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name is None
        assert avatar is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        """Test that None is returned when Discord API raises DiscordAPIError."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.side_effect = DiscordAPIError(403, "Forbidden")
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name is None
        assert avatar is None

    @pytest.mark.asyncio
    async def test_returns_none_on_key_error(self):
        """Test that None is returned when member data is missing expected keys."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.return_value = {"unexpected": "data"}
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name is None
        assert avatar is None

    @pytest.mark.asyncio
    async def test_returns_none_on_unexpected_exception(self):
        """Test that None is returned on any unexpected exception."""
        mock_api = AsyncMock()
        mock_api.get_guild_member.side_effect = RuntimeError("unexpected")
        with patch(
            "services.bot.utils.discord_format.get_discord_client",
            return_value=mock_api,
        ):
            name, avatar = await get_member_display_info(MagicMock(), "guild1", "user1")
        assert name is None
        assert avatar is None

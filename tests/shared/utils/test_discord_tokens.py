# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for Discord token utilities."""

import base64

import pytest

from shared.utils.discord_tokens import extract_bot_discord_id


def test_extract_bot_discord_id_valid_token():
    """Test extracting bot ID from valid Discord bot token."""
    bot_id = "1234567890"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    token = f"{bot_id_base64}.timestamp.hmac"

    result = extract_bot_discord_id(token)
    assert result == bot_id


def test_extract_bot_discord_id_with_padding():
    """Test extraction handles base64 padding correctly."""
    bot_id = "123456789"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    # Remove padding to test automatic padding addition
    bot_id_base64 = bot_id_base64.rstrip("=")
    token = f"{bot_id_base64}.timestamp.hmac"

    result = extract_bot_discord_id(token)
    assert result == bot_id


def test_extract_bot_discord_id_invalid_format_too_few_parts():
    """Test error handling for token with too few parts."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("invalid.token")


def test_extract_bot_discord_id_invalid_format_too_many_parts():
    """Test error handling for token with too many parts."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("part1.part2.part3.part4")


def test_extract_bot_discord_id_invalid_base64():
    """Test error handling for invalid base64 encoding."""
    with pytest.raises(ValueError, match="Failed to decode bot ID"):
        extract_bot_discord_id("!!!invalid_base64!!!.timestamp.hmac")


def test_extract_bot_discord_id_empty_token():
    """Test error handling for empty token."""
    with pytest.raises(ValueError, match="Invalid bot token format"):
        extract_bot_discord_id("")


def test_extract_bot_discord_id_snowflake_id():
    """Test extracting real Discord snowflake ID format."""
    # Typical Discord snowflake is 17-19 digits
    bot_id = "1234567890123456789"
    bot_id_base64 = base64.b64encode(bot_id.encode("utf-8")).decode("utf-8")
    token = f"{bot_id_base64}.MTYxNjM2NjQ2Mg.abc123"

    result = extract_bot_discord_id(token)
    assert result == bot_id
    assert len(result) == 19

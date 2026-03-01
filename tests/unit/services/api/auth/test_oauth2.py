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


"""Unit tests for oauth2 module."""

from unittest.mock import AsyncMock, patch

import pytest

from services.api.auth import oauth2


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_true_for_owner():
    """Test that an application owner is identified as a maintainer."""
    app_info = {"owner": {"id": "111"}, "team": None}
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("111")

    assert result is True


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_true_for_team_member():
    """Test that a team member is identified as a maintainer."""
    app_info = {
        "owner": {"id": "999"},
        "team": {
            "members": [
                {"user": {"id": "222"}},
                {"user": {"id": "333"}},
            ]
        },
    }
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("222")

    assert result is True


@pytest.mark.asyncio
async def test_is_app_maintainer_returns_false_for_non_member():
    """Test that a non-owner, non-team-member returns False."""
    app_info = {
        "owner": {"id": "999"},
        "team": {
            "members": [
                {"user": {"id": "222"}},
            ]
        },
    }
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        result = await oauth2.is_app_maintainer("444")

    assert result is False


@pytest.mark.asyncio
async def test_is_app_maintainer_falls_back_to_owner_when_no_team():
    """Test that when team is absent, only the owner is a maintainer."""
    app_info = {"owner": {"id": "111"}}
    mock_discord = AsyncMock()
    mock_discord.get_application_info = AsyncMock(return_value=app_info)

    with patch("services.api.auth.oauth2.get_discord_client", return_value=mock_discord):
        owner_result = await oauth2.is_app_maintainer("111")
        other_result = await oauth2.is_app_maintainer("999")

    assert owner_result is True
    assert other_result is False

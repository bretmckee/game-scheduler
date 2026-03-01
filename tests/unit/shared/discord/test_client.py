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


"""Unit tests for DiscordAPIClient."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL
from shared.discord.client import DISCORD_API_BASE, DiscordAPIClient


@pytest.fixture
def discord_client():
    """Return a DiscordAPIClient with test credentials."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="Bot.test.bot_token",
    )


@pytest.fixture(autouse=True)
def mock_redis_cache_miss():
    """Mock Redis as a cache miss so tests exercise the _make_api_request path."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    with patch(
        "shared.discord.client.cache_client.get_redis_client",
        AsyncMock(return_value=mock_redis),
    ):
        yield mock_redis


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_url(discord_client):
    """Test that get_application_info calls the Discord applications/@me endpoint."""
    expected_url = f"{DISCORD_API_BASE}/oauth2/applications/@me"
    mock_request = AsyncMock(return_value={"id": "123", "name": "TestBot"})

    with patch.object(discord_client, "_make_api_request", mock_request):
        await discord_client.get_application_info()

    call_kwargs = mock_request.call_args
    assert call_kwargs.kwargs.get("url") == expected_url or (
        len(call_kwargs.args) > 1 and call_kwargs.args[1] == expected_url
    )


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_cache_key(discord_client):
    """Test that get_application_info uses the app_info() cache key."""
    mock_request = AsyncMock(return_value={"id": "123", "name": "TestBot"})

    with patch.object(discord_client, "_make_api_request", mock_request):
        await discord_client.get_application_info()

    call_kwargs = mock_request.call_args
    actual_cache_key = call_kwargs.kwargs.get("cache_key") or next(
        (a for a in call_kwargs.args if a == CacheKeys.app_info()), None
    )
    assert actual_cache_key == CacheKeys.app_info()


@pytest.mark.asyncio
async def test_get_application_info_uses_correct_ttl(discord_client):
    """Test that get_application_info uses the APP_INFO TTL."""
    mock_request = AsyncMock(return_value={"id": "123", "name": "TestBot"})

    with patch.object(discord_client, "_make_api_request", mock_request):
        await discord_client.get_application_info()

    call_kwargs = mock_request.call_args
    actual_ttl = call_kwargs.kwargs.get("cache_ttl") or next(
        (a for a in call_kwargs.args if a == CacheTTL.APP_INFO), None
    )
    assert actual_ttl == CacheTTL.APP_INFO


@pytest.mark.asyncio
async def test_get_application_info_returns_dict(discord_client):
    """Test that get_application_info returns the application info dict."""
    app_data = {"id": "123", "name": "TestBot", "owner": {"id": "456"}}
    mock_request = AsyncMock(return_value=app_data)

    with patch.object(discord_client, "_make_api_request", mock_request):
        result = await discord_client.get_application_info()

    assert result == app_data


@pytest.mark.asyncio
async def test_get_application_info_returns_cached_data(discord_client, mock_redis_cache_miss):
    """Test that get_application_info returns cached data without calling Discord."""
    app_data = {"id": "123", "name": "TestBot", "owner": {"id": "456"}}
    mock_redis_cache_miss.get.return_value = json.dumps(app_data)
    mock_request = AsyncMock()

    with patch.object(discord_client, "_make_api_request", mock_request):
        result = await discord_client.get_application_info()

    assert result == app_data
    mock_request.assert_not_awaited()

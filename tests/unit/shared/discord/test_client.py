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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.cache.keys import CacheKeys
from shared.cache.ttl import CacheTTL
from shared.discord.client import DiscordAPIClient


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
    expected_url = "https://discord.com/api/v10/oauth2/applications/@me"
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


# ---------------------------------------------------------------------------
# Task 1.2 (RED): Verify api_base_url controls request URLs
# ---------------------------------------------------------------------------


@pytest.fixture
def discord_client_fake_base():
    """Return a DiscordAPIClient with a fake api_base_url."""
    return DiscordAPIClient(
        client_id="test_client_id",
        client_secret="test_client_secret",
        bot_token="Bot.test.bot_token",
        api_base_url="http://fake:9999",
    )


def _mock_session_returning(response_data: object) -> MagicMock:
    """Return a mock aiohttp session whose .get() yields a successful response.

    aiohttp's session.get() is called synchronously and used as an async context
    manager, so the outer mock must be a plain MagicMock, not AsyncMock.
    """
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=response_data)
    mock_response.headers = MagicMock()
    mock_response.headers.get = MagicMock(return_value="N/A")

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_response)
    ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get.return_value = ctx
    return mock_session


@pytest.mark.asyncio
async def test_exchange_code_uses_api_base_url(discord_client_fake_base: DiscordAPIClient) -> None:
    """exchange_code must POST to api_base_url/oauth2/token, not the hardcoded Discord URL."""
    fake_token = {
        "access_token": "tok",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "ref",
        "scope": "identify",
    }
    mock_request = AsyncMock(return_value=fake_token)

    with patch.object(discord_client_fake_base, "_make_api_request", mock_request):
        await discord_client_fake_base.exchange_code("code123", "http://redirect")

    url_used = mock_request.call_args.kwargs.get("url")
    assert url_used == "http://fake:9999/oauth2/token"


@pytest.mark.asyncio
async def test_refresh_token_uses_api_base_url(discord_client_fake_base: DiscordAPIClient) -> None:
    """refresh_token must POST to api_base_url/oauth2/token, not the hardcoded Discord URL."""
    fake_token = {
        "access_token": "tok2",
        "token_type": "Bearer",
        "expires_in": 604800,
        "refresh_token": "ref2",
        "scope": "identify",
    }
    mock_request = AsyncMock(return_value=fake_token)

    with patch.object(discord_client_fake_base, "_make_api_request", mock_request):
        await discord_client_fake_base.refresh_token("old_refresh_token.abc")

    url_used = mock_request.call_args.kwargs.get("url")
    assert url_used == "http://fake:9999/oauth2/token"


@pytest.mark.asyncio
async def test_get_user_info_uses_api_base_url(discord_client_fake_base: DiscordAPIClient) -> None:
    """get_user_info must GET api_base_url/users/@me, not the hardcoded Discord URL."""
    mock_session = _mock_session_returning({"id": "user123", "username": "testuser"})
    session_patch = patch.object(
        discord_client_fake_base, "_get_session", AsyncMock(return_value=mock_session)
    )
    with session_patch:
        await discord_client_fake_base.get_user_info("oauth_token.abc")

    actual_url = mock_session.get.call_args[0][0]
    assert actual_url == "http://fake:9999/users/@me"


@pytest.mark.asyncio
async def test_get_guilds_uses_api_base_url(discord_client_fake_base: DiscordAPIClient) -> None:
    """get_guilds must GET api_base_url/users/@me/guilds, not the hardcoded Discord URL."""
    mock_session = _mock_session_returning([{"id": "guild1", "name": "Test Guild"}])
    session_patch = patch.object(
        discord_client_fake_base, "_get_session", AsyncMock(return_value=mock_session)
    )
    with session_patch:
        await discord_client_fake_base.get_guilds()

    actual_url = mock_session.get.call_args[0][0]
    assert actual_url == "http://fake:9999/users/@me/guilds"

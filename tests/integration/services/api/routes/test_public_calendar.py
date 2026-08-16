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


"""Integration tests for the public calendar export endpoint."""

import pytest
from httpx import AsyncClient

from services.api.auth.tokens import mint_calendar_export_token
from shared.cache.keys import CacheKeys

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_get_calendar_export_returns_ics_without_auth(
    async_client: AsyncClient,
    test_game_environment,
) -> None:
    """Public endpoint serves the .ics export without authentication."""
    env = test_game_environment(title="Integration Calendar Game")
    game = env["game"]
    token = await mint_calendar_export_token(game["id"])

    response = await async_client.get(f"/api/v1/public/calendar/{token}.ics")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/calendar; charset=utf-8"
    assert "inline" in response.headers["content-disposition"]
    assert "filename=" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_get_calendar_export_unknown_token_returns_404(
    async_client: AsyncClient,
) -> None:
    """Unknown token returns 404."""
    response = await async_client.get("/api/v1/public/calendar/not-a-real-token.ics")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_calendar_export_expired_token_returns_404(
    async_client: AsyncClient,
    redis_client_async,
    test_game_environment,
) -> None:
    """A token removed from Redis (simulating TTL expiry) returns 404."""
    env = test_game_environment(title="Expired Token Game")
    game = env["game"]
    token = await mint_calendar_export_token(game["id"])

    # Simulate expiry by deleting the token's Redis key directly
    await redis_client_async.delete(CacheKeys.calendar_export_token(token))

    response = await async_client.get(f"/api/v1/public/calendar/{token}.ics")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

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


"""Integration tests for channel configuration write endpoints.

Covers create_channel_config and update_channel_config paths in
services/api/routes/channels.py (lines 73-84, 104-118) that were
previously uncovered.
"""

import httpx
import pytest

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_create_channel_config_success(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/channels creates a channel configuration."""
    guild = create_guild()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    discord_channel_id = "111222333444555666"

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/channels",
                json={
                    "guild_id": guild["id"],
                    "channel_id": discord_channel_id,
                    "is_active": True,
                },
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 201, (
            f"Expected 201, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["channel_id"] == discord_channel_id
        assert data["guild_id"] == guild["id"]
        assert data["is_active"] is True
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_channel_config_conflict(
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/channels returns 409 when channel config already exists."""
    guild = create_guild()
    discord_channel_id = "222333444555666777"
    create_channel(guild_id=guild["id"], discord_channel_id=discord_channel_id)
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/channels",
                json={
                    "guild_id": guild["id"],
                    "channel_id": discord_channel_id,
                    "is_active": True,
                },
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 409, (
            f"Expected 409, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_channel_config_success(
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/channels/{channel_id} updates channel configuration."""
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                f"/api/v1/channels/{channel['id']}",
                json={"is_active": False},
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["is_active"] is False
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_channel_config_not_found(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/channels/{channel_id} returns 404 for nonexistent channel."""
    guild = create_guild()
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.put(
                "/api/v1/channels/00000000-0000-0000-0000-000000000999",
                json={"is_active": False},
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 404, (
            f"Expected 404, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)

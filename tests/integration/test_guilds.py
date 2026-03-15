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


"""Integration tests for guild admin API endpoints.

Covers create_guild_config conflict, update_guild_config, and
validate_mention paths in services/api/routes/guilds.py (lines 158,
242, 255, 377-415) that were previously uncovered.
"""

import httpx
import pytest

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_create_guild_config_conflict(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/guilds returns 409 when guild configuration already exists."""
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
            response = await client.post(
                "/api/v1/guilds",
                json={"guild_id": guild["guild_id"]},
                params={"guild_id": guild["id"]},
            )

        assert response.status_code == 409, (
            f"Expected 409, got {response.status_code}: {response.text}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_guild_config_success(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/guilds/{guild_id} updates guild configuration."""
    new_role_id = "987654321098765432"
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
                f"/api/v1/guilds/{guild['id']}",
                json={"bot_manager_role_ids": [new_role_id]},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert new_role_id in data["bot_manager_role_ids"]
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_validate_mention_empty(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/guilds/{id}/validate-mention returns invalid for an empty mention."""
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
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/validate-mention",
                json={"mention": ""},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["valid"] is False
        assert data["error"] == "Mention cannot be empty"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_validate_mention_non_at_symbol(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/guilds/{id}/validate-mention returns valid for a non-@ placeholder."""
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
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/validate-mention",
                json={"mention": "here"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        assert data["valid"] is True
        assert data["error"] is None
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_validate_mention_at_symbol(
    create_guild,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """POST /api/v1/guilds/{id}/validate-mention validates an @mention via Discord API."""
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
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/validate-mention",
                json={"mention": "@unknown_user"},
            )

        assert response.status_code == 200, (
            f"Expected 200, got {response.status_code}: {response.text}"
        )
        data = response.json()
        # Fake guild/token means Discord can't resolve this mention
        assert data["valid"] is False
        assert data["error"] is not None
    finally:
        await cleanup_test_session(session_token)

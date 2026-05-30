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


"""Integration tests for mention and emoji resolution in game text fields.

Verifies that GET /api/v1/games/{id} renders custom emoji tokens, channel
mention tokens, and user mention tokens back to human-readable form in
title, description, and signup_instructions.
"""

import json
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "123456789012345678"

LOCATION_CHANNEL_DISCORD_ID = "406497579061215235"
LOCATION_CHANNEL_NAME = "test-general"
TEST_USER_DISCORD_ID = "987654321098765432"
TEST_USER_DISPLAY_NAME = "Test Player"
TEST_USER_USERNAME = "testplayer"


async def _seed_guild_emojis(guild_discord_id: str, emojis: list[dict]) -> None:
    """Seed the discord:guild_emojis Redis key with the given emoji list."""
    redis = RedisClient()
    await redis.connect()
    try:
        await redis.set_json(
            CacheKeys.discord_guild_emojis(guild_discord_id),
            emojis,
            ttl=300,
        )
    finally:
        await redis.disconnect()


async def _seed_guild_channels(guild_discord_id: str, channels: list[dict]) -> None:
    """Seed the discord:guild_channels Redis key with the given channel list."""
    redis = RedisClient()
    await redis.connect()
    try:
        await redis.set_json(
            CacheKeys.discord_guild_channels(guild_discord_id),
            channels,
            ttl=300,
        )
    finally:
        await redis.disconnect()


async def _seed_member_for_display(
    guild_discord_id: str,
    user_discord_id: str,
    display_name: str,
    username: str,
) -> None:
    """Seed a proj:member projection key so user mention reverse-render can resolve a name."""
    redis = RedisClient()
    await redis.connect()
    try:
        member_data = {
            "roles": [],
            "nick": None,
            "global_name": display_name,
            "username": username,
            "avatar_url": None,
        }
        await redis.set(
            CacheKeys.proj_member("1", guild_discord_id, user_discord_id),
            json.dumps(member_data),
            ttl=300,
        )
    finally:
        await redis.disconnect()


@pytest.mark.asyncio
async def test_custom_emoji_round_trip_in_all_text_fields(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} renders stored emoji tokens back to :name: in all text fields.

    When a game is created with :emoji_name: in title, description, and
    signup_instructions, the API resolves the custom emoji to a stored Discord
    token on POST. GET must reverse-render all three fields back to :emoji_name:
    and must never expose the raw <:name:id> storage format to the caller.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    await _seed_guild_emojis(
        guild["guild_id"],
        [{"id": LOCATION_CHANNEL_DISCORD_ID, "name": "testwave", "animated": False}],
    )
    await _seed_guild_channels(
        guild["guild_id"],
        [{"id": posting_channel["channel_id"], "name": "general", "type": 0}],
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_resp = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": ":testwave: :thumbsup: Game Night",
                    "scheduled_at": scheduled_at,
                    "description": "Join us :testwave: with :thumbsup: vibes",
                    "signup_instructions": "React with :testwave: or :thumbsup: to sign up",
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200, (
            f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        )
        data = get_resp.json()

        for field in ("title", "description", "signup_instructions"):
            value = data[field]
            assert ":testwave:" in value, (
                f"{field} should contain ':testwave:' (rendered), got: {value!r}"
            )
            assert ":thumbsup:" in value, (
                f"{field} should contain ':thumbsup:' (standard emoji unchanged), got: {value!r}"
            )
            assert "<:testwave:" not in value, (
                f"{field} must not expose raw storage token '<:testwave:...>', got: {value!r}"
            )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_channel_mention_in_description_renders_as_name(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} renders stored <#id> token in description back to #channel-name.

    When a game is created with #channel-name in description, the API resolves
    it to a stored <#snowflake> token on POST. GET must reverse-render description
    to show the human-readable #channel-name and must not expose the raw token.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    await _seed_guild_channels(
        guild["guild_id"],
        [
            {"id": posting_channel["channel_id"], "name": "general", "type": 0},
            {"id": LOCATION_CHANNEL_DISCORD_ID, "name": LOCATION_CHANNEL_NAME, "type": 0},
        ],
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_resp = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": "Game Night",
                    "scheduled_at": scheduled_at,
                    "description": f"Meet us in #{LOCATION_CHANNEL_NAME} before the game",
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200, (
            f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        )
        data = get_resp.json()
        description = data["description"]

        assert f"#{LOCATION_CHANNEL_NAME}" in description, (
            f"description should contain '#{LOCATION_CHANNEL_NAME}' (rendered), "
            f"got: {description!r}"
        )
        assert f"<#{LOCATION_CHANNEL_DISCORD_ID}>" not in description, (
            f"description must not expose raw '<#{LOCATION_CHANNEL_DISCORD_ID}>' token, "
            f"got: {description!r}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_user_mention_in_description_renders_as_display_name(
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} renders stored <@id> token in description back to @display-name.

    When a game's description contains a stored <@snowflake> mention token (injected
    directly to bypass forward resolution), GET must reverse-render description to
    show the human-readable @Display Name and must not expose the raw token.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    await _seed_member_for_display(
        guild["guild_id"],
        TEST_USER_DISCORD_ID,
        TEST_USER_DISPLAY_NAME,
        TEST_USER_USERNAME,
    )

    game = create_game(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        host_id=user["id"],
        template_id=template["id"],
        title="Game Night",
        description=f"Ping <@{TEST_USER_DISCORD_ID}> for details",
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            get_resp = await client.get(f"/api/v1/games/{game['id']}")

        assert get_resp.status_code == 200, (
            f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        )
        data = get_resp.json()
        description = data["description"]

        assert f"@{TEST_USER_DISPLAY_NAME}" in description, (
            f"description should contain '@{TEST_USER_DISPLAY_NAME}' (rendered), "
            f"got: {description!r}"
        )
        assert f"<@{TEST_USER_DISCORD_ID}>" not in description, (
            f"description must not expose raw '<@{TEST_USER_DISCORD_ID}>' token, "
            f"got: {description!r}"
        )
    finally:
        await cleanup_test_session(session_token)

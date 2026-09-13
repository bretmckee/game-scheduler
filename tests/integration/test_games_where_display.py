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


"""Integration tests for where_display field in game API responses.

Verifies that GET /api/v1/games/{id} populates where_display by resolving
<#snowflake> tokens via the guild channels Redis cache, and that the field
is absent (null) when where is not a channel token.
"""

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

# A realistic 18-digit Discord snowflake for the location channel
LOCATION_CHANNEL_DISCORD_ID = "406497579061215235"
LOCATION_CHANNEL_NAME = "🍻tavern-generalchat"


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


@pytest.mark.asyncio
async def test_get_game_where_display_resolves_snowflake_token(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns where_display with resolved channel name.

    When a game's where field contains a <#snowflake> token and the channel
    exists in the guild channels Redis cache, where_display should be the
    human-readable #channel-name string.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        where=f"<#{LOCATION_CHANNEL_DISCORD_ID}>",
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )

    # Seed the guild channels list so render_where_display can resolve the ID
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
                    "title": "Tavern Night",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200, (
            f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        )
        data = get_resp.json()
        assert data["where"] == f"<#{LOCATION_CHANNEL_DISCORD_ID}>", (
            "where should retain the raw token"
        )
        assert data["where_display"] == f"#{LOCATION_CHANNEL_NAME}", (
            f"where_display should be '#{LOCATION_CHANNEL_NAME}', got {data.get('where_display')}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_with_untouched_location_survives_channel_rename(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with the raw <#id> token succeeds even if the channel
    was renamed after the edit page loaded.

    This is the round trip the frontend now relies on (EditGame.tsx's
    resolveWherePayload): when Location is untouched, the client resends the stored
    <#id> token -- not the where_display string reconstructed from the channel's name
    at GET time. Validating an <#id> token only checks the ID still resolves to a text
    channel (see ChannelResolver._check_snowflake_tokens), so a rename in between never
    blocks an unrelated save.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        where=f"<#{LOCATION_CHANNEL_DISCORD_ID}>",
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
                    "title": "Tavern Night",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")
            assert get_resp.json()["where_display"] == f"#{LOCATION_CHANNEL_NAME}"

            # Simulate the host renaming the channel on Discord between page load and save.
            renamed_channel_name = f"{LOCATION_CHANNEL_NAME}-renamed"
            await _seed_guild_channels(
                guild["guild_id"],
                [
                    {"id": posting_channel["channel_id"], "name": "general", "type": 0},
                    {"id": LOCATION_CHANNEL_DISCORD_ID, "name": renamed_channel_name, "type": 0},
                ],
            )

            # Unrelated edit, submitted with the stored raw token rather than the
            # (now stale) where_display text -- exactly what EditGame.tsx now sends.
            update_resp = await client.put(
                f"/api/v1/games/{game_id}",
                data={
                    "title": "Tavern Night (updated)",
                    "where": f"<#{LOCATION_CHANNEL_DISCORD_ID}>",
                },
            )

        assert update_resp.status_code == 200, (
            f"Expected 200, got {update_resp.status_code}: {update_resp.text}"
        )
        data = update_resp.json()
        assert data["where"] == f"<#{LOCATION_CHANNEL_DISCORD_ID}>"
        assert data["where_display"] == f"#{renamed_channel_name}"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_game_resubmitting_stale_display_text_after_rename_fails(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """PUT /api/v1/games/{id} with the stale where_display text (the old channel name)
    is rejected as an invalid channel reference once the channel has been renamed.

    This is the exact failure the reported bug hit: the pre-fix frontend resubmitted
    where_display verbatim on every save, so an unrelated edit (e.g. removing a
    participant) failed with a spurious "not a valid channel name" error whenever the
    channel had been renamed since the edit page loaded. This test documents that the
    backend's by-name resolution is legitimately strict -- the fix belongs in what the
    client resubmits (see test_update_game_with_untouched_location_survives_channel_rename),
    not in loosening this validation.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        where=f"<#{LOCATION_CHANNEL_DISCORD_ID}>",
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
                    "title": "Tavern Night",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")
            stale_display = get_resp.json()["where_display"]
            assert stale_display == f"#{LOCATION_CHANNEL_NAME}"

            await _seed_guild_channels(
                guild["guild_id"],
                [
                    {"id": posting_channel["channel_id"], "name": "general", "type": 0},
                    {
                        "id": LOCATION_CHANNEL_DISCORD_ID,
                        "name": f"{LOCATION_CHANNEL_NAME}-renamed",
                        "type": 0,
                    },
                ],
            )

            update_resp = await client.put(
                f"/api/v1/games/{game_id}",
                data={
                    "title": "Tavern Night (updated)",
                    "where": stale_display,
                },
            )

        assert update_resp.status_code == 422, (
            f"Expected 422, got {update_resp.status_code}: {update_resp.text}"
        )
        detail = update_resp.json()["detail"]
        assert detail["error"] == "invalid_mentions"
        assert any(m["input"] == stale_display for m in detail["invalid_mentions"])
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_get_game_where_display_null_when_no_token(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """GET /api/v1/games/{id} returns where_display as null when where is plain text.

    When a game's where field is free-form text (not a channel token),
    where_display should be null.
    """
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        where="The Rusty Flagon, table 3",
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
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
                    "title": "In-Person Game",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201, f"Game creation failed: {create_resp.text}"
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200, (
            f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        )
        data = get_resp.json()
        assert data["where"] == "The Rusty Flagon, table 3"
        assert data["where_display"] is None, (
            f"where_display should be null for plain text where, got {data.get('where_display')}"
        )
    finally:
        await cleanup_test_session(session_token)

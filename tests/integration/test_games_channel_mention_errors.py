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


"""Integration tests for channel-mention validation error reporting.

Exercises the full POST /api/v1/games round trip (real route, real GameService,
real ChannelResolver, real Redis-backed guild-channels cache) to verify the
error payload a browser actually receives — not just the mocked-out unit-level
behavior. Covers two regressions:

1. A field-context bug where the API told the user their "Location" was
   invalid regardless of which free-text field the bad reference was in.
2. A false-positive bug where Markdown headings ("## Section") in description
   text were misparsed as channel-mention attempts.
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


async def _setup_game_context(
    create_user, create_guild, create_channel, create_template, seed_redis_cache
) -> dict:
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    # Only "general" exists — anything else referenced by #name is unresolvable.
    await _seed_guild_channels(
        guild["guild_id"],
        [{"id": channel["channel_id"], "name": "general", "type": 0}],
    )

    return {"guild": guild, "channel": channel, "template": template}


@pytest.mark.asyncio
async def test_create_game_reports_field_and_markdown_hint_for_unspaced_heading(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """A forgotten-space heading in Description surfaces a field-labeled, markdown-aware error.

    Regression coverage for the real end-to-end response body: the field/reason
    wiring across channel_resolver.py -> games.py -> routes/games.py is only
    exercised here with a real ChannelResolver; other tests mock it out.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template"]["id"],
                    "title": "Session Zero",
                    "scheduled_at": scheduled_at,
                    "description": "#session1 recap notes",
                },
            )

        assert response.status_code == 422, (
            f"Expected 422, got {response.status_code}: {response.text}"
        )
        detail = response.json()["detail"]
        assert detail["error"] == "invalid_mentions"
        assert len(detail["invalid_mentions"]) == 1
        error = detail["invalid_mentions"][0]
        assert error["type"] == "not_found"
        assert error["field"] == "Description"
        assert error["input"] == "#session1"
        assert error["reason"] == (
            "Your Description contains '#session1', which is not a valid channel name "
            "in this server. If you meant this as a Markdown heading, Discord requires "
            "a space after the '#' — use '# session1' instead of '#session1'."
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_create_game_accepts_markdown_heading_in_description(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """A properly-spaced Markdown heading ("## Section") is not treated as a channel mention.

    Regression coverage for the original bug report: users writing normal
    Markdown in the description field were getting spurious "channel not
    found" errors.
    """
    ctx = await _setup_game_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": ctx["template"]["id"],
                    "title": "Session Zero",
                    "scheduled_at": scheduled_at,
                    "description": "## What to bring\nDice and a character sheet",
                },
            )

        assert response.status_code == 201, f"Game creation failed: {response.text}"
        assert response.json()["description"] == "## What to bring\nDice and a character sheet"
    finally:
        await cleanup_test_session(session_token)

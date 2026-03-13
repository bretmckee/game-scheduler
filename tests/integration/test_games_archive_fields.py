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


"""Integration tests for game archive field propagation from templates."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


async def _setup_archive_game_test_context(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
) -> dict[str, str]:
    """Create shared guild/template data and Redis state for game creation tests."""
    bot_manager_role_id = "999888777666555444"
    guild_discord_id = "123456789012345678"

    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id="987654321098765432")
    archive_channel = create_channel(guild_id=guild["id"], discord_channel_id="111222333444555666")
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="INT_TEST Archive Template",
    )

    return {
        "guild_id": guild["id"],
        "template_id": template["id"],
        "archive_channel_id": archive_channel["id"],
    }


@pytest.mark.asyncio
async def test_game_creation_copies_archive_fields_from_template(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Verify game creation copies template archive fields to game session."""
    context = await _setup_archive_game_test_context(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
    )

    admin_db_sync.execute(
        text(
            "UPDATE game_templates "
            "SET archive_delay_seconds = :delay, archive_channel_id = :archive_channel_id "
            "WHERE id = :template_id"
        ),
        {
            "delay": 3600,
            "archive_channel_id": context["archive_channel_id"],
            "template_id": context["template_id"],
        },
    )
    admin_db_sync.commit()

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": context["template_id"],
                    "title": "INT_TEST Archive Copy",
                    "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                },
            )

        assert response.status_code in (200, 201), response.text
        game_id = response.json()["id"]

        row = admin_db_sync.execute(
            text(
                "SELECT archive_delay_seconds, archive_channel_id "
                "FROM game_sessions WHERE id = :game_id"
            ),
            {"game_id": game_id},
        ).fetchone()

        assert row is not None
        assert row[0] == 3600
        assert row[1] == context["archive_channel_id"]

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_game_creation_keeps_archive_fields_null_when_template_unset(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Verify game archive fields remain NULL when template does not set them."""
    context = await _setup_archive_game_test_context(
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": context["template_id"],
                    "title": "INT_TEST Archive Null",
                    "scheduled_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                },
            )

        assert response.status_code in (200, 201), response.text
        game_id = response.json()["id"]

        row = admin_db_sync.execute(
            text(
                "SELECT archive_delay_seconds, archive_channel_id "
                "FROM game_sessions WHERE id = :game_id"
            ),
            {"game_id": game_id},
        ).fetchone()

        assert row is not None
        assert row[0] is None
        assert row[1] is None

    finally:
        await cleanup_test_session(session_token)

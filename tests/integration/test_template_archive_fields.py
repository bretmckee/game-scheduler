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


"""Integration tests for template archive field behavior."""

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_create_template_with_archive_fields(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify template archive fields persist through API create."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id="111111111111111111")
    archive_channel = create_channel(guild_id=guild["id"], discord_channel_id="222222222222222222")
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Archive Template",
                    "archive_delay_seconds": 3600,
                    "archive_channel_id": archive_channel["id"],
                },
            )

        assert response.status_code == 201, response.text
        response_data = response.json()

        assert response_data["archive_delay_seconds"] == 3600
        assert response_data["archive_channel_id"] == archive_channel["id"]

        template_id = response_data["id"]

        db_row = admin_db_sync.execute(
            text(
                "SELECT archive_delay_seconds, archive_channel_id "
                "FROM game_templates WHERE id = :template_id"
            ),
            {"template_id": template_id},
        ).fetchone()

        assert db_row is not None
        assert db_row[0] == 3600
        assert db_row[1] == archive_channel["id"]

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_template_archive_fields_round_trip(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify update supports setting and clearing archive fields."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id="333333333333333333")
    archive_channel = create_channel(guild_id=guild["id"], discord_channel_id="444444444444444444")
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
        user_roles=[bot_manager_role_id],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Archive Update Template",
                },
            )
            assert create_response.status_code == 201, create_response.text
            template_id = create_response.json()["id"]

            set_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "archive_delay_seconds": 0,
                    "archive_channel_id": archive_channel["id"],
                },
            )
            assert set_response.status_code == 200, set_response.text
            set_data = set_response.json()
            assert set_data["archive_delay_seconds"] == 0
            assert set_data["archive_channel_id"] == archive_channel["id"]

            clear_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "archive_delay_seconds": None,
                    "archive_channel_id": None,
                },
            )
            assert clear_response.status_code == 200, clear_response.text
            clear_data = clear_response.json()
            assert clear_data["archive_delay_seconds"] is None
            assert clear_data["archive_channel_id"] is None

        db_row = admin_db_sync.execute(
            text(
                "SELECT archive_delay_seconds, archive_channel_id "
                "FROM game_templates WHERE id = :template_id"
            ),
            {"template_id": template_id},
        ).fetchone()

        assert db_row is not None
        assert db_row[0] is None
        assert db_row[1] is None

    finally:
        await cleanup_test_session(session_token)

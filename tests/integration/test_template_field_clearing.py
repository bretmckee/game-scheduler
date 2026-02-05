# Copyright 2025-2026 Bret McKee
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


"""Integration tests for template optional field clearing.

Tests verify that users can clear optional text fields (description, where,
signup_instructions) in template updates by sending explicit null values,
and that the database correctly reflects these changes.

Bug fix verification for double-filtering anti-pattern that prevented
clearing optional fields.
"""

import httpx
import pytest
from sqlalchemy import select

from shared.models.template import GameTemplate
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_clear_description_field_to_null(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify clearing description field sets it to NULL in database.

    Tests complete workflow: create template with description, update to clear it
    with explicit null, verify database contains NULL.
    """
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
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
            # Create template with description
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Test Template",
                    "description": "Initial description",
                },
            )
            assert create_response.status_code == 201
            template_data = create_response.json()
            template_id = template_data["id"]

            # Verify description was set
            assert template_data["description"] == "Initial description"

            # Clear description by sending explicit null
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "name": "Test Template",
                    "description": None,
                },
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Verify API returns null
            assert updated_data["description"] is None

        # Verify database contains NULL
        result = await admin_db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        db_template = result.scalar_one()
        assert db_template.description is None

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_clear_where_and_signup_instructions(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify clearing where and signup_instructions fields."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
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
            # Create template with all optional fields set
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Test Template",
                    "description": "Test description",
                    "where": "Discord Voice",
                    "signup_instructions": "React to join",
                },
            )
            assert create_response.status_code == 201
            template_data = create_response.json()
            template_id = template_data["id"]

            # Clear where and signup_instructions
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "name": "Test Template",
                    "where": None,
                    "signup_instructions": None,
                },
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Verify API returns null for cleared fields
            assert updated_data["where"] is None
            assert updated_data["signup_instructions"] is None
            # Description should remain unchanged
            assert updated_data["description"] == "Test description"

        # Verify database state
        result = await admin_db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        db_template = result.scalar_one()
        assert db_template.where is None
        assert db_template.signup_instructions is None
        assert db_template.description == "Test description"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_update_field_to_new_value(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify updating a field to a new non-null value works correctly."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
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
            # Create template with description
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Test Template",
                    "description": "Original description",
                },
            )
            assert create_response.status_code == 201
            template_id = create_response.json()["id"]

            # Update description to new value
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "name": "Test Template",
                    "description": "Updated description",
                },
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            assert updated_data["description"] == "Updated description"

        # Verify database
        result = await admin_db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        db_template = result.scalar_one()
        assert db_template.description == "Updated description"

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_clear_already_null_field(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify clearing an already-null field keeps it null."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
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
            # Create template without optional fields (they default to null)
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Test Template",
                },
            )
            assert create_response.status_code == 201
            template_id = create_response.json()["id"]

            # Send explicit null for already-null field
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "name": "Test Template",
                    "description": None,
                },
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            assert updated_data["description"] is None

        # Verify database
        result = await admin_db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        db_template = result.scalar_one()
        assert db_template.description is None

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_omitted_fields_remain_unchanged(
    admin_db,
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    seed_redis_cache,
    api_base_url,
):
    """Verify that fields not included in update request remain unchanged."""
    bot_manager_role_id = "123456789012345678"
    guild = create_guild(bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"])
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
            # Create template with all fields set
            create_response = await client.post(
                f"/api/v1/guilds/{guild['id']}/templates",
                json={
                    "guild_id": guild["id"],
                    "channel_id": channel["id"],
                    "name": "Test Template",
                    "description": "Keep this",
                    "where": "Keep this too",
                    "signup_instructions": "And this",
                },
            )
            assert create_response.status_code == 201
            template_id = create_response.json()["id"]

            # Update only name, omitting other fields
            update_response = await client.put(
                f"/api/v1/templates/{template_id}",
                json={
                    "name": "Updated Name",
                },
            )
            assert update_response.status_code == 200
            updated_data = update_response.json()

            # Verify omitted fields unchanged
            assert updated_data["name"] == "Updated Name"
            assert updated_data["description"] == "Keep this"
            assert updated_data["where"] == "Keep this too"
            assert updated_data["signup_instructions"] == "And this"

        # Verify database
        result = await admin_db.execute(select(GameTemplate).where(GameTemplate.id == template_id))
        db_template = result.scalar_one()
        assert db_template.name == "Updated Name"
        assert db_template.description == "Keep this"
        assert db_template.where == "Keep this too"
        assert db_template.signup_instructions == "And this"

    finally:
        await cleanup_test_session(session_token)

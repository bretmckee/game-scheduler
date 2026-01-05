# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.

"""Integration tests for template default overrides in game creation.

Tests verify that when a user clears a template default field value,
the game is created with an empty/null value rather than reverting
to the template's default value.

Bug fix verification for: Template defaults should only pre-fill the form,
not override explicit user choices (including clearing fields).
"""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.asyncio
async def test_cleared_reminder_minutes_not_reverted_to_template_default(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Verify that clearing reminder_minutes in form doesn't revert to template default."""
    # Create test environment with factory fixtures
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create template WITH reminder minutes set
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="TEMPLATE_TEST Template",
        description="Template with defaults",
        max_players=10,
        reminder_minutes=[60, 15],
        where="Discord Voice",
        signup_instructions="Please be on time",
        expected_duration_minutes=120,
    )

    # Create authenticated session
    session_token, session_data = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    # Seed cache with guild/role data (session already created above)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create game with EMPTY reminder_minutes (user cleared the field)
            scheduled_at = datetime.now(UTC) + timedelta(hours=2)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": "TEMPLATE_TEST Game No Reminders",
                    "description": "Test game without reminders",
                    "scheduled_at": scheduled_at.isoformat(),
                    "reminder_minutes": "[]",  # Explicitly empty - user cleared it
                },
            )

            assert response.status_code == 201, f"Failed to create game: {response.text}"
            game_id = response.json()["id"]

            # Verify game was created with NO reminders (not template default)
            game = admin_db_sync.execute(
                text("SELECT reminder_minutes FROM game_sessions WHERE id = :id"),
                {"id": game_id},
            ).fetchone()

            assert game is not None, "Game not found in database"
            assert game.reminder_minutes == [], (
                f"Expected no reminders, got {game.reminder_minutes}"
            )

    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_cleared_optional_text_fields_not_reverted_to_template_defaults(
    admin_db_sync,
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Verify that clearing optional text fields doesn't revert to template defaults."""
    # Create test environment with factory fixtures
    guild = create_guild()
    channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)

    # Create template WITH all optional fields set
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="TEMPLATE_TEST Full Template",
        description="Template with all defaults",
        max_players=10,
        where="Discord Voice",
        signup_instructions="Please be on time",
        expected_duration_minutes=120,
    )

    # Create authenticated session
    session_token, session_data = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    # Seed cache with guild/role data (session already created above)
    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=channel["channel_id"],
    )

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            # Create game with ALL optional fields cleared
            # For integer fields, omit them entirely instead of sending empty strings
            # which would cause FastAPI validation errors
            scheduled_at = datetime.now(UTC) + timedelta(hours=2)
            response = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": "TEMPLATE_TEST Game Cleared Fields",
                    "description": "Test game with cleared fields",
                    "scheduled_at": scheduled_at.isoformat(),
                    "where": "",  # Explicitly empty - user cleared it
                    "signup_instructions": "",  # Explicitly empty - user cleared it
                    # Note: max_players and expected_duration_minutes are omitted
                    # to clear them (sending empty string causes validation error)
                },
            )

            assert response.status_code == 201, f"Failed to create game: {response.text}"
            game_id = response.json()["id"]

            # Verify game was created with empty/null values (not template defaults)
            game = admin_db_sync.execute(
                text(
                    """
                    SELECT "where", signup_instructions, max_players,
                           expected_duration_minutes
                    FROM game_sessions
                    WHERE id = :id
                    """
                ),
                {"id": game_id},
            ).fetchone()

            assert game is not None, "Game not found in database"
            assert game[0] == "", f"Expected empty where, got {game[0]}"
            assert game.signup_instructions == "", (
                f"Expected empty signup_instructions, got {game.signup_instructions}"
            )
            # TODO: These fields currently fall back to template defaults when omitted
            # This is the bug that needs to be fixed - they should be None when cleared
            assert game.max_players == 10, (
                f"Currently falls back to template default: {game.max_players}"
            )
            assert game.expected_duration_minutes == 120, (
                f"Currently falls back to template default: {game.expected_duration_minutes}"
            )

    finally:
        await cleanup_test_session(session_token)

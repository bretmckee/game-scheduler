# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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


"""Integration tests for route-level transaction atomicity.

Tests verify that FastAPI's Depends(get_db()) properly manages transactions
by using database-level failures (constraints, FK violations) to trigger
rollback during multi-step operations.

Approach:
1. Make HTTP request that performs multi-step operation
2. Operation partially succeeds then hits database constraint violation
3. Database error propagates to get_db() which rolls back transaction
4. Verify all changes rolled back (no partial data)

This tests the actual production code path through HTTP → FastAPI → get_db() → Service.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text

from shared.models.game import GameSession
from shared.utils.discord_tokens import extract_bot_discord_id

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


@pytest.mark.integration
def test_game_update_rolls_back_on_database_constraint(
    admin_db_sync,
    create_guild,
    create_channel,
    create_template,
    create_user,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """Verify game update rolls back when database constraint fails.

    Multi-step operation:
    1. Update game title (succeeds)
    2. Update description to trigger CHECK constraint (fails)
    3. Database rejects UPDATE → exception → get_db() rolls back
    4. Game title update should be rolled back (original title remains)
    """
    guild_discord_id = "123456789012345678"
    channel_discord_id = "987654321098765432"
    bot_manager_role_id = "999888777666555444"

    host_user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    guild = create_guild(
        discord_guild_id=guild_discord_id,
        bot_manager_roles=[bot_manager_role_id],
    )
    channel = create_channel(
        guild_id=guild["id"],
        discord_channel_id=channel_discord_id,
    )
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    original_title = "Original Game Title"
    original_description = "Original Description"
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        template_id=template["id"],
        host_id=host_user["id"],
        status="SCHEDULED",
        title=original_title,
        description=original_description,
    )

    seed_redis_cache(
        user_discord_id=host_user["discord_id"],
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    # Add temporary CHECK constraint that rejects specific description
    admin_db_sync.execute(
        text(
            "ALTER TABLE game_sessions ADD CONSTRAINT test_reject_update_failure "
            "CHECK (description != 'TRIGGER_UPDATE_FAILURE')"
        )
    )
    admin_db_sync.commit()

    try:
        # Update both title and description, description triggers constraint
        response = client.put(
            f"/api/v1/games/{game['id']}",
            data={
                "title": "Updated Title",
                "description": "TRIGGER_UPDATE_FAILURE",
            },
        )

        # Expect error due to constraint violation
        assert response.status_code in [
            400,
            500,
        ], f"Expected error, got {response.status_code}: {response.text}"

        # Verify rollback: both title and description should be unchanged
        admin_db_sync.expire_all()
        result = admin_db_sync.execute(select(GameSession).where(GameSession.id == game["id"]))
        game_after = result.scalar_one()
        assert game_after.title == original_title, (
            f"Title should be '{original_title}', got '{game_after.title}'"
        )
        assert game_after.description == original_description, (
            f"Description should be '{original_description}', got '{game_after.description}'"
        )

    finally:
        # Clean up constraint
        admin_db_sync.execute(
            text("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS test_reject_update_failure")
        )
        admin_db_sync.commit()


@pytest.mark.integration
def test_game_creation_rolls_back_on_database_constraint(
    admin_db_sync,
    create_guild,
    create_channel,
    create_template,
    create_user,
    seed_redis_cache,
    create_authenticated_client,
):
    """Verify game creation rolls back when database constraint fails.

    Adds temporary CHECK constraint that rejects specific title values,
    then creates game with that title. Game creation partially succeeds
    but constraint violation triggers rollback.
    """
    guild_discord_id = "123456789012345678"
    channel_discord_id = "987654321098765432"
    bot_manager_role_id = "999888777666555444"

    host_user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    guild = create_guild(
        discord_guild_id=guild_discord_id,
        bot_manager_roles=[bot_manager_role_id],
    )
    channel = create_channel(
        guild_id=guild["id"],
        discord_channel_id=channel_discord_id,
    )
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    seed_redis_cache(
        user_discord_id=host_user["discord_id"],
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    # Add temporary constraint that rejects specific title
    admin_db_sync.execute(
        text(
            "ALTER TABLE game_sessions ADD CONSTRAINT test_reject_failure_title "
            "CHECK (title != 'TRIGGER_DATABASE_FAILURE')"
        )
    )
    admin_db_sync.commit()

    try:
        client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

        scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

        # Create game with title that violates constraint
        response = client.post(
            "/api/v1/games",
            data={
                "template_id": template["id"],
                "title": "TRIGGER_DATABASE_FAILURE",
                "description": "Test",
                "scheduled_at": scheduled_at,
                "reminder_minutes": "[60]",
            },
        )

        # Expect error due to constraint violation
        assert response.status_code in [
            400,
            500,
        ], f"Expected error, got {response.status_code}"

        # Verify rollback: no game created (including schedules, etc)
        admin_db_sync.expire_all()
        result = admin_db_sync.execute(
            select(GameSession).where(GameSession.template_id == template["id"])
        )
        assert len(result.scalars().all()) == 0, "No game should exist after rollback"

    finally:
        # Clean up test constraint
        admin_db_sync.execute(
            text("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS test_reject_failure_title")
        )
        admin_db_sync.commit()


@pytest.mark.integration
def test_game_update_multiple_fields_rolls_back_on_constraint(
    admin_db_sync,
    create_guild,
    create_channel,
    create_template,
    create_user,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """Verify game update with multiple fields rolls back when constraint fails.

    Multi-step operation:
    1. Update title (succeeds)
    2. Update max_players to trigger CHECK constraint (fails)
    3. Database rejects UPDATE → exception → get_db() rolls back
    4. Title update should be rolled back (original title remains)
    """
    guild_discord_id = "123456789012345678"
    channel_discord_id = "987654321098765432"
    bot_manager_role_id = "999888777666555444"

    host_user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    guild = create_guild(
        discord_guild_id=guild_discord_id,
        bot_manager_roles=[bot_manager_role_id],
    )
    channel = create_channel(
        guild_id=guild["id"],
        discord_channel_id=channel_discord_id,
    )
    template = create_template(guild_id=guild["id"], channel_id=channel["id"])

    original_title = "Original Title"
    game = create_game(
        guild_id=guild["id"],
        channel_id=channel["id"],
        template_id=template["id"],
        host_id=host_user["id"],
        status="SCHEDULED",
        title=original_title,
    )

    seed_redis_cache(
        user_discord_id=host_user["discord_id"],
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    # Add temporary CHECK constraint on max_players
    admin_db_sync.execute(
        text(
            "ALTER TABLE game_sessions ADD CONSTRAINT test_reject_max_players "
            "CHECK (max_players != 999)"
        )
    )
    admin_db_sync.commit()

    try:
        # Update both title and max_players, max_players triggers constraint
        response = client.put(
            f"/api/v1/games/{game['id']}",
            data={
                "title": "Updated Title",
                "max_players": "999",
            },
        )

        # Expect error due to constraint violation
        assert response.status_code in [
            400,
            500,
        ], f"Expected error, got {response.status_code}: {response.text}"

        # Verify rollback: title should be unchanged
        admin_db_sync.expire_all()
        result = admin_db_sync.execute(select(GameSession).where(GameSession.id == game["id"]))
        game_after = result.scalar_one()
        assert game_after.title == original_title, (
            f"Title should be '{original_title}', got '{game_after.title}'"
        )
        assert game_after.max_players != 999, (
            f"max_players should not be 999, got '{game_after.max_players}'"
        )

    finally:
        # Clean up constraint
        admin_db_sync.execute(
            text("ALTER TABLE game_sessions DROP CONSTRAINT IF EXISTS test_reject_max_players")
        )
        admin_db_sync.commit()

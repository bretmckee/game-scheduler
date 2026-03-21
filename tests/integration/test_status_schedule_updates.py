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


"""Integration tests for status schedule update correctness on game edits.

Covers three bug scenarios:
1. Changing expected_duration_minutes does not update the COMPLETED schedule
2. Editing an IN_PROGRESS game deletes its COMPLETED schedule
3. Editing a COMPLETED game deletes its ARCHIVED schedule (or doesn't create one)
"""

import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import text

from shared.utils.discord_tokens import extract_bot_discord_id
from tests.shared.auth_helpers import cleanup_test_session, create_test_session

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "223344556677889900"


async def _setup_context(
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
) -> dict:
    """Create guild/channel/user/template and seed Redis for status schedule tests."""
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

    return {
        "template_id": template["id"],
    }


async def _create_game(client: httpx.AsyncClient, template_id: str, **extra) -> dict:
    """Create a game via the API and return the response JSON."""
    scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    payload = {
        "template_id": template_id,
        "title": "INT_TEST Status Schedule Game",
        "scheduled_at": scheduled_at,
        **extra,
    }
    response = await client.post("/api/v1/games", data=payload)
    assert response.status_code == 201, f"Game creation failed: {response.text}"
    return response.json()


def _get_schedule_row(admin_db_sync, game_id: str, target_status: str):
    """Fetch a single status schedule row for a game and target status."""
    return admin_db_sync.execute(
        text(
            "SELECT id, transition_time FROM game_status_schedule "
            "WHERE game_id = :game_id AND target_status = :target_status"
        ),
        {"game_id": game_id, "target_status": target_status},
    ).fetchone()


@pytest.mark.asyncio
async def test_expected_duration_change_updates_completed_schedule_for_scheduled_game(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Changing expected_duration_minutes on a SCHEDULED game updates the COMPLETED schedule.

    Bug 1: status_schedule_needs_update is never set when expected_duration_minutes changes,
    so _update_status_schedules() is never called and the schedule stays stale.
    """
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"], expected_duration_minutes=60)
            game_id = game["id"]

            initial_row = _get_schedule_row(admin_db_sync, game_id, "COMPLETED")
            assert initial_row is not None, "No COMPLETED schedule after game creation"

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"expected_duration_minutes": "90"},
            )
            assert response.status_code == 200, response.text

        scheduled_at_str = game["scheduled_at"]
        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
        expected_completion = scheduled_at + timedelta(minutes=90)

        row = _get_schedule_row(admin_db_sync, game_id, "COMPLETED")
        assert row is not None, "COMPLETED schedule deleted after duration update"

        actual_time = row[1]
        if actual_time.tzinfo is None:
            actual_time = actual_time.replace(tzinfo=UTC)
        assert abs((actual_time - expected_completion).total_seconds()) < 5, (
            f"COMPLETED schedule not updated: got {actual_time}, expected ~{expected_completion}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_expected_duration_change_updates_completed_schedule_for_in_progress_game(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Changing expected_duration_minutes on an IN_PROGRESS game updates the COMPLETED schedule.

    Bug 1: flag not set → _update_status_schedules() never called.
    Bug 2: even if called, the else branch deletes all schedules for IN_PROGRESS games.
    """
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"], expected_duration_minutes=60)
            game_id = game["id"]

            assert _get_schedule_row(admin_db_sync, game_id, "COMPLETED") is not None

            admin_db_sync.execute(
                text("UPDATE game_sessions SET status = 'IN_PROGRESS' WHERE id = :id"),
                {"id": game_id},
            )
            admin_db_sync.commit()

            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"expected_duration_minutes": "90"},
            )
            assert response.status_code == 200, response.text

        scheduled_at_str = game["scheduled_at"]
        scheduled_at = datetime.fromisoformat(scheduled_at_str.replace("Z", "+00:00"))
        expected_completion = scheduled_at + timedelta(minutes=90)

        row = _get_schedule_row(admin_db_sync, game_id, "COMPLETED")
        assert row is not None, (
            "COMPLETED schedule deleted after duration update on IN_PROGRESS game"
        )

        actual_time = row[1]
        if actual_time.tzinfo is None:
            actual_time = actual_time.replace(tzinfo=UTC)
        assert abs((actual_time - expected_completion).total_seconds()) < 5, (
            f"COMPLETED schedule not updated: got {actual_time}, expected ~{expected_completion}"
        )
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_api_update_in_progress_game_preserves_completed_schedule(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating an IN_PROGRESS game does not delete its COMPLETED schedule.

    Bug 2: when status_schedule_needs_update=True and game is IN_PROGRESS,
    the else branch deletes all schedules including the COMPLETED row.
    """
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            assert _get_schedule_row(admin_db_sync, game_id, "COMPLETED") is not None

            admin_db_sync.execute(
                text("UPDATE game_sessions SET status = 'IN_PROGRESS' WHERE id = :id"),
                {"id": game_id},
            )
            admin_db_sync.commit()

            # Pass status='IN_PROGRESS' (same value) to trigger status_schedule_needs_update=True
            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"status": "IN_PROGRESS"},
            )
            assert response.status_code == 200, response.text

        row = _get_schedule_row(admin_db_sync, game_id, "COMPLETED")
        assert row is not None, "COMPLETED schedule was deleted when updating an IN_PROGRESS game"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_api_update_completed_game_preserves_archived_schedule(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a COMPLETED game does not delete its pending ARCHIVED schedule.

    Bug 2: the else branch deletes all schedules for COMPLETED games.
    """
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text(
                    "UPDATE game_sessions "
                    "SET status = 'COMPLETED', archive_delay_seconds = 3600 "
                    "WHERE id = :id"
                ),
                {"id": game_id},
            )
            admin_db_sync.commit()

            archived_schedule_id = str(uuid.uuid4())
            archive_time = datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1)
            admin_db_sync.execute(
                text(
                    "INSERT INTO game_status_schedule "
                    "(id, game_id, target_status, transition_time, executed) "
                    "VALUES (:id, :game_id, 'ARCHIVED', :transition_time, false)"
                ),
                {"id": archived_schedule_id, "game_id": game_id, "transition_time": archive_time},
            )
            admin_db_sync.commit()

            # Pass status='COMPLETED' (same value) to trigger status_schedule_needs_update=True
            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"status": "COMPLETED"},
            )
            assert response.status_code == 200, response.text

        row = _get_schedule_row(admin_db_sync, game_id, "ARCHIVED")
        assert row is not None, "ARCHIVED schedule was deleted when updating a COMPLETED game"
    finally:
        await cleanup_test_session(session_token)


@pytest.mark.asyncio
async def test_api_update_completed_game_creates_archived_schedule(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    api_base_url,
):
    """Updating a COMPLETED game with archive_delay_seconds creates an ARCHIVED schedule.

    Before fix: no _ensure_archived_schedule_if_configured() helper exists, so no
    ARCHIVED schedule is created even when archive_delay_seconds is configured.
    """
    ctx = await _setup_context(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    try:
        async with httpx.AsyncClient(
            base_url=api_base_url,
            timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            game = await _create_game(client, ctx["template_id"])
            game_id = game["id"]

            admin_db_sync.execute(
                text(
                    "UPDATE game_sessions "
                    "SET status = 'COMPLETED', archive_delay_seconds = 3600 "
                    "WHERE id = :id"
                ),
                {"id": game_id},
            )
            admin_db_sync.commit()

            assert _get_schedule_row(admin_db_sync, game_id, "ARCHIVED") is None, (
                "Unexpected ARCHIVED schedule before update"
            )

            # Pass status='COMPLETED' (same value) to trigger status_schedule_needs_update=True
            response = await client.put(
                f"/api/v1/games/{game_id}",
                data={"status": "COMPLETED"},
            )
            assert response.status_code == 200, response.text

        row = _get_schedule_row(admin_db_sync, game_id, "ARCHIVED")
        assert row is not None, (
            "ARCHIVED schedule was not created for COMPLETED game with archive_delay_seconds"
        )
    finally:
        await cleanup_test_session(session_token)

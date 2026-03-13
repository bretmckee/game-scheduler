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


"""End-to-end tests for game announcement archive behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.models import GameStatus
from tests.e2e.conftest import TimeoutType, wait_for_db_condition, wait_for_game_message_id
from tests.e2e.helpers.discord import wait_for_condition

pytestmark = pytest.mark.e2e


async def _get_guild_and_template_ids(admin_db, discord_guild_id: str) -> tuple[str, str]:
    """Fetch guild config ID and default template ID for the Discord guild."""
    result = await admin_db.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": discord_guild_id},
    )
    guild_row = result.fetchone()
    assert guild_row, f"Test guild {discord_guild_id} not found"

    result = await admin_db.execute(
        text("SELECT id FROM game_templates WHERE guild_id = :guild_id AND is_default = true"),
        {"guild_id": guild_row[0]},
    )
    template_row = result.fetchone()
    assert template_row, f"Default template not found for guild {guild_row[0]}"

    return guild_row[0], template_row[0]


async def _ensure_archive_channel_config(
    admin_db,
    guild_db_id: str,
    archive_channel_discord_id: str,
) -> str:
    """Ensure the archive channel exists in channel_configurations."""
    result = await admin_db.execute(
        text(
            "SELECT id FROM channel_configurations "
            "WHERE guild_id = :guild_id AND channel_id = :channel_id"
        ),
        {"guild_id": guild_db_id, "channel_id": archive_channel_discord_id},
    )
    row = result.fetchone()
    if row:
        return row[0]

    channel_config_id = str(uuid4())
    now = datetime.now(UTC).replace(tzinfo=None)
    await admin_db.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_config_id,
            "channel_id": archive_channel_discord_id,
            "guild_id": guild_db_id,
            "created_at": now,
            "updated_at": now,
        },
    )
    await admin_db.commit()
    return channel_config_id


@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_game_archived_reposts_to_archive_channel(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_archive_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """E2E: ARCHIVED transition deletes original message and reposts to archive channel."""
    guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)
    archive_channel_config_id = await _ensure_archive_channel_config(
        admin_db, guild_db_id, discord_archive_channel_id
    )

    await admin_db.execute(
        text(
            "UPDATE game_templates SET archive_delay_seconds = :delay, "
            "archive_channel_id = :archive_channel_id WHERE id = :template_id"
        ),
        {"delay": 0, "archive_channel_id": archive_channel_config_id, "template_id": template_id},
    )
    await admin_db.commit()

    game_title = f"E2E Archive Repost {uuid4().hex[:8]}"
    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "description": "Archive repost behavior",
            "scheduled_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            "expected_duration_minutes": "1",
            "max_players": "4",
        },
    )
    assert response.status_code == 201, response.text
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.ARCHIVED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 120,
        interval=5,
        description="game status transition to ARCHIVED",
    )

    archive_schedule_result = await admin_db.execute(
        text(
            "SELECT COUNT(*) FROM game_status_schedule "
            "WHERE game_id = :game_id AND target_status = 'ARCHIVED'"
        ),
        {"game_id": game_id},
    )
    assert archive_schedule_result.scalar_one() == 1

    await discord_helper.wait_for_message_deleted(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 30,
        interval=2.0,
    )

    async def check_archive_message():
        message = await discord_helper.find_message_by_embed_title(
            discord_archive_channel_id,
            game_title,
            limit=25,
        )
        if message is None:
            return (False, None)
        return (True, message)

    archive_message = await wait_for_condition(
        check_archive_message,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 30,
        interval=2.0,
        description="archived announcement in archive channel",
    )

    assert len(archive_message.embeds) == 1
    assert archive_message.embeds[0].footer is not None
    assert GameStatus.ARCHIVED.display_name in archive_message.embeds[0].footer.text
    assert not archive_message.components, "Archived repost should not contain interactive controls"


@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_game_archived_delete_only_mode(
    authenticated_admin_client,
    admin_db,
    discord_helper,
    discord_channel_id,
    discord_archive_channel_id,
    discord_guild_id,
    synced_guild,
    test_timeouts,
):
    """E2E: ARCHIVED transition in delete-only mode removes active announcement only."""
    _guild_db_id, template_id = await _get_guild_and_template_ids(admin_db, discord_guild_id)

    await admin_db.execute(
        text(
            "UPDATE game_templates SET archive_delay_seconds = :delay, "
            "archive_channel_id = NULL WHERE id = :template_id"
        ),
        {"delay": 0, "template_id": template_id},
    )
    await admin_db.commit()

    game_title = f"E2E Archive Delete Only {uuid4().hex[:8]}"
    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": template_id,
            "title": game_title,
            "description": "Archive delete-only behavior",
            "scheduled_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat(),
            "expected_duration_minutes": "1",
            "max_players": "4",
        },
    )
    assert response.status_code == 201, response.text
    game_id = response.json()["id"]

    message_id = await wait_for_game_message_id(
        admin_db, game_id, timeout=test_timeouts[TimeoutType.DB_WRITE]
    )

    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        lambda row: row[0] == GameStatus.ARCHIVED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 120,
        interval=5,
        description="game status transition to ARCHIVED in delete-only mode",
    )

    await discord_helper.wait_for_message_deleted(
        channel_id=discord_channel_id,
        message_id=message_id,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION] + 30,
        interval=2.0,
    )

    archive_match = await discord_helper.find_message_by_embed_title(
        discord_archive_channel_id,
        game_title,
        limit=25,
    )
    assert archive_match is None, "Delete-only archive mode should not repost to archive channel"

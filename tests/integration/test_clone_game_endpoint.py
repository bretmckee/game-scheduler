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


"""Integration tests for the POST /{game_id}/clone endpoint.

Verifies the complete HTTP → API → Database → RabbitMQ flow for game cloning.
Tests that:
- A cloned game appears in the database with correct fields
- Participants are carried over when requested
- A GAME_CREATED event is published to RabbitMQ
- Non-host users receive 403 Forbidden
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.cache.client import RedisClient
from shared.cache.keys import CacheKeys
from shared.models import GameStatus
from shared.models.participant import ParticipantType
from shared.utils.discord_tokens import extract_bot_discord_id

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)

OTHER_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzYxMQ.Hxyzab.other_fake_token_for_tests"
OTHER_BOT_DISCORD_ID = extract_bot_discord_id(OTHER_DISCORD_TOKEN)


def _seed_guild_member(guild_discord_id: str, user_discord_id: str) -> None:
    """Seed a minimal member-projection entry for one Discord user.

    Phase 5's carryover tests submit a clone request's `participants` list
    using Discord internal mention format (`<@discord_id>`), which
    create_game's real participant-resolution pipeline resolves via the
    guild member projection cache rather than the database -- so the
    resubmitted source participant must exist there too.
    """

    async def _seed() -> None:
        redis_client = RedisClient()
        await redis_client.connect()
        try:
            gen = await redis_client.get(CacheKeys.proj_gen()) or "1"
            await redis_client.set_json(
                CacheKeys.proj_member(gen, guild_discord_id, user_discord_id),
                {
                    "roles": [],
                    "nick": None,
                    "global_name": None,
                    "username": user_discord_id,
                    "avatar_url": None,
                },
            )
        finally:
            await redis_client.disconnect()

    asyncio.run(_seed())


def _setup_environment(
    create_user, create_guild, create_channel, create_template, seed_redis_cache
):
    """Create guild, channel, user and Redis cache entries for one test."""
    guild_discord_id = "223456789012345678"
    channel_discord_id = "887654321098765432"
    bot_manager_role_id = "199888777666555444"

    test_user = create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)

    seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="Clone INT_TEST Template",
        description="Integration test template for clone tests",
    )

    return {
        "user": test_user,
        "guild": guild,
        "channel": channel,
        "template": template,
        "guild_discord_id": guild_discord_id,
        "channel_discord_id": channel_discord_id,
    }


def test_clone_game_endpoint_returns_201_with_new_game(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """POST /{game_id}/clone must return 201 with a new GameResponse in the DB."""
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game For Clone Test",
    )

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "NO",
            "waitlist_carryover": "NO",
        },
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    game_data = response.json()
    new_game_id = game_data["id"]

    assert new_game_id != source_game["id"], "Cloned game must have a different ID"
    assert game_data["title"] == source_game["title"]

    result = admin_db_sync.execute(
        text("SELECT id, title, status FROM game_sessions WHERE id = :game_id"),
        {"game_id": new_game_id},
    ).fetchone()

    assert result is not None, "Cloned game not found in database"
    assert result[1] == source_game["title"]
    assert result[2] == GameStatus.SCHEDULED


def test_clone_game_endpoint_non_host_receives_403(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """POST /{game_id}/clone by a non-host non-manager user must return 403."""
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game Forbidden Clone",
    )

    create_user(discord_user_id=OTHER_BOT_DISCORD_ID)
    # Seed cache with no bot_manager roles for the other user
    seed_redis_cache(
        user_discord_id=OTHER_BOT_DISCORD_ID,
        guild_discord_id=env["guild_discord_id"],
        channel_discord_id=env["channel_discord_id"],
        user_roles=[env["guild_discord_id"]],
        bot_manager_roles=[],
    )

    non_host_client = create_authenticated_client(OTHER_DISCORD_TOKEN, OTHER_BOT_DISCORD_ID)

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = non_host_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "NO",
            "waitlist_carryover": "NO",
        },
    )

    assert response.status_code == 403, (
        f"Expected 403 Forbidden, got {response.status_code}: {response.text}"
    )


def test_clone_game_endpoint_publishes_game_created_event(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """POST /{game_id}/clone must enqueue a game_created row in bot_action_queue."""
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game For Event Test",
    )

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "NO",
            "waitlist_carryover": "NO",
        },
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    cloned_game_id = response.json()["id"]
    bot_row = admin_db_sync.execute(
        text(
            "SELECT action_type, game_id FROM bot_action_queue "
            "WHERE action_type = 'game_created' AND game_id = :game_id"
        ),
        {"game_id": cloned_game_id},
    ).fetchone()

    assert bot_row is not None, "No game_created row found in bot_action_queue"
    assert bot_row[1] == cloned_game_id, "bot_action_queue must reference the new cloned game ID"


def test_clone_game_endpoint_yes_carryover_copies_new_game_participants(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """POST /{game_id}/clone with YES player carryover must copy participants to the new game.

    As of Phase 5, roster membership on the new game comes from the submitted
    `participants` list (create_game's own initial_participants pipeline);
    player_carryover=YES only determines whether the resubmitted source
    participant is *eligible* for deadline carryover, matched by discord_id
    against the source game's own confirmed/overflow partition.
    """
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game With Participants",
        max_players=4,
    )

    # Insert a participant directly into the source game
    participant_user = create_user(discord_user_id="321000000000000001")
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": "test-participant-uuid-clone",
            "game_id": source_game["id"],
            "user_id": participant_user["id"],
            "position": 1,
            "position_type": ParticipantType.HOST_ADDED,
        },
    )
    admin_db_sync.commit()
    _seed_guild_member(env["guild_discord_id"], participant_user["discord_id"])

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "YES",
            "waitlist_carryover": "NO",
            "participants": json.dumps([f"<@{participant_user['discord_id']}>"]),
        },
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    new_game_id = response.json()["id"]

    participants = admin_db_sync.execute(
        text(
            "SELECT user_id, position, position_type FROM game_participants "
            "WHERE game_session_id = :game_id ORDER BY position"
        ),
        {"game_id": new_game_id},
    ).fetchall()

    assert len(participants) == 1, f"Expected 1 carried-over participant, got {len(participants)}"
    assert participants[0][0] == participant_user["id"]
    assert participants[0][1] == 1
    assert participants[0][2] == ParticipantType.HOST_ADDED


def test_clone_game_endpoint_yes_with_deadline_creates_action_and_notification_schedules(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """YES_WITH_DEADLINE carryover creates ParticipantActionSchedule
    and clone_confirmation records.

    As of Phase 5, the resubmitted source participant must also appear in the
    clone request's `participants` list -- create_game's own
    initial_participants pipeline builds the new game's roster "for free",
    and _apply_deadline_carryover only fires for participants present in
    both that submission and the source game's matching carryover-eligible
    group (matched by discord_id).
    """
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game YES_WITH_DEADLINE",
        max_players=4,
    )

    participant_user = create_user(discord_user_id="329000000000000007")
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type)"
        ),
        {
            "id": "test-participant-uuid-deadline",
            "game_id": source_game["id"],
            "user_id": participant_user["id"],
            "position": 1,
            "position_type": ParticipantType.HOST_ADDED,
        },
    )
    admin_db_sync.commit()
    _seed_guild_member(env["guild_discord_id"], participant_user["discord_id"])

    deadline = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "YES_WITH_DEADLINE",
            "player_deadline": deadline,
            "waitlist_carryover": "NO",
            "participants": json.dumps([f"<@{participant_user['discord_id']}>"]),
        },
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    new_game_id = response.json()["id"]

    # Verify participant was carried over
    new_participant = admin_db_sync.execute(
        text(
            "SELECT id, user_id FROM game_participants "
            "WHERE game_session_id = :game_id AND user_id = :user_id"
        ),
        {"game_id": new_game_id, "user_id": participant_user["id"]},
    ).fetchone()
    assert new_participant is not None, "Carried-over participant must exist in the new game"
    new_participant_id = new_participant[0]

    # Verify ParticipantActionSchedule created
    action_schedule = admin_db_sync.execute(
        text(
            "SELECT action, action_time FROM participant_action_schedule "
            "WHERE participant_id = :participant_id"
        ),
        {"participant_id": new_participant_id},
    ).fetchone()
    assert action_schedule is not None, "ParticipantActionSchedule must be created"
    assert action_schedule[0] == "drop", "Action must be 'drop'"

    # Verify clone_confirmation NotificationSchedule created
    notif_schedule = admin_db_sync.execute(
        text(
            "SELECT notification_type FROM notification_schedule "
            "WHERE game_id = :game_id AND participant_id = :participant_id "
            "AND notification_type = 'clone_confirmation'"
        ),
        {"game_id": new_game_id, "participant_id": new_participant_id},
    ).fetchone()
    assert notif_schedule is not None, "NotificationSchedule must be created"
    assert notif_schedule[0] == "clone_confirmation", (
        "Notification type must be 'clone_confirmation'"
    )


def test_clone_game_endpoint_unresolvable_mention_in_override_returns_422(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    create_game,
    seed_redis_cache,
    create_authenticated_client,
):
    """An unresolvable @mention in an overridden free-text field must surface as a 422
    with error: "invalid_mentions", now that clone_game delegates free-text resolution
    to create_game's own _resolve_free_text_fields_for_create pipeline.
    """
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_game = create_game(
        guild_id=env["guild"]["id"],
        channel_id=env["channel"]["id"],
        host_id=env["user"]["id"],
        template_id=env["template"]["id"],
        title="Source Game For Invalid Mention Test",
    )

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "NO",
            "waitlist_carryover": "NO",
            "description": "Come play with @nonexistent_user_xyz",
        },
    )

    assert response.status_code == 422, (
        f"Expected 422 invalid_mentions, got {response.status_code}: {response.text}"
    )
    detail = response.json()["detail"]
    assert detail["error"] == "invalid_mentions", detail


def test_clone_game_endpoint_with_uploaded_thumbnail_uses_new_image_not_ref_copy(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """POST /{game_id}/clone with a real thumbnail file attached must store a freshly
    uploaded image on the new game rather than carrying over the source's thumbnail
    by reference.
    """
    env = _setup_environment(
        create_user, create_guild, create_channel, create_template, seed_redis_cache
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    source_scheduled_at = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    source_response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": env["template"]["id"],
            "title": "Source Game With Thumbnail",
            "scheduled_at": source_scheduled_at,
        },
        files={"thumbnail": ("source.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png")},
    )
    assert source_response.status_code == 201, (
        f"Expected 201, got {source_response.status_code}: {source_response.text}"
    )
    source_game = source_response.json()
    source_thumbnail_id = source_game["thumbnail_id"]
    assert source_thumbnail_id is not None, "Source game must have a stored thumbnail"

    clone_at = (datetime.now(UTC) + timedelta(days=14)).isoformat()

    response = authenticated_client.post(
        f"/api/v1/games/{source_game['id']}/clone",
        data={
            "scheduled_at": clone_at,
            "player_carryover": "NO",
            "waitlist_carryover": "NO",
        },
        files={"thumbnail": ("clone.png", b"\x89PNG\r\n\x1a\n" + b"\x11" * 16, "image/png")},
    )

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    new_game = response.json()
    new_thumbnail_id = new_game["thumbnail_id"]

    assert new_thumbnail_id is not None, "Cloned game must have a stored thumbnail"
    assert new_thumbnail_id != source_thumbnail_id, (
        "A new thumbnail upload must not be a reference copy of the source's thumbnail"
    )

    source_image_ref_count = admin_db_sync.execute(
        text("SELECT reference_count FROM game_images WHERE id = :id"),
        {"id": source_thumbnail_id},
    ).scalar_one()
    assert source_image_ref_count == 1, (
        "Source thumbnail's reference count must stay at 1 -- it was not ref-copied"
    )

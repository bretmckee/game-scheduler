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


"""Integration tests for game creation with signup methods.

Tests verify the complete API → Database → RabbitMQ flow for signup method
propagation. These tests ensure that signup_method values flow correctly
through the entire HTTP/auth/service/messaging stack.

Uses fake Discord credentials since integration tests don't connect to Discord.
"""

import json
import time
import uuid as _uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.messaging.infrastructure import QUEUE_BOT_EVENTS, QUEUE_NOTIFICATION
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.utils.discord_tokens import extract_bot_discord_id
from tests.integration.conftest import consume_one_message

pytestmark = pytest.mark.integration

# Test Discord token (format valid but doesn't need to work - no Discord connection)
TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)


def _create_test_user(create_user):
    """Helper to create test user for API requests."""
    return create_user(discord_user_id=TEST_BOT_DISCORD_ID)


def _create_test_template(
    create_guild, create_channel, create_template, seed_redis_cache, test_user
):
    """Helper to create test template with signup method configuration."""
    guild_discord_id = "123456789012345678"
    channel_discord_id = "987654321098765432"
    bot_manager_role_id = "999888777666555444"

    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)

    # Seed Redis cache with all test data
    seed_redis_cache(
        user_discord_id=test_user["discord_id"],
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="INT_TEST Template",
        description="Integration test template",
        allowed_signup_methods=[
            SignupMethod.SELF_SIGNUP.value,
            SignupMethod.HOST_SELECTED.value,
        ],
        default_signup_method=SignupMethod.HOST_SELECTED.value,
    )

    return {
        "id": template["id"],
        "guild_id": guild_discord_id,  # Discord guild ID
        "channel_id": channel_discord_id,  # Discord channel ID
        "guild_config_id": guild["id"],  # UUID FK
        "channel_config_id": channel["id"],  # UUID FK
    }


def test_api_creates_game_with_explicit_signup_method_in_rabbitmq_message(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify API game creation with explicit signup method produces correct RabbitMQ message.

    Flow: HTTP POST → API (authenticated) → Database → RabbitMQ → Bot Queue
    Validates that signup_method flows through entire stack including HTTP layer.
    """
    test_user = _create_test_user(create_user)
    test_template = _create_test_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Game with Self Signup",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.SELF_SIGNUP.value,
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.SELF_SIGNUP.value
    game_id = game_data["id"]

    # Verify database record
    result = admin_db_sync.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    ).fetchone()
    assert result is not None, "Game not found in database"
    assert result[0] == SignupMethod.SELF_SIGNUP.value

    # Verify RabbitMQ message
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None, "No message found in bot_events queue"
    assert body is not None, "Message body is None"
    message = json.loads(body)

    assert "data" in message, "Message missing 'data' field"
    assert "signup_method" in message["data"], "Message missing 'signup_method' in event data"
    assert message["data"]["signup_method"] == SignupMethod.SELF_SIGNUP.value


def test_api_uses_template_default_signup_method_when_not_specified(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify API game creation without explicit signup method uses template default.

    Template has default_signup_method=HOST_SELECTED, should be used automatically.
    """
    test_user = _create_test_user(create_user)
    test_template = _create_test_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Game with Template Default",
            "scheduled_at": scheduled_at,
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.HOST_SELECTED.value

    game_id = game_data["id"]

    # Verify database
    result = admin_db_sync.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    ).fetchone()
    assert result[0] == SignupMethod.HOST_SELECTED.value

    # Verify RabbitMQ message
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None
    assert body is not None, "Message body is None"
    message = json.loads(body)
    assert message["data"]["signup_method"] == SignupMethod.HOST_SELECTED.value


def _create_waitlist_template(
    create_guild, create_channel, create_template, seed_redis_cache, test_user
):
    """Helper to create a template allowing HOST_SELECTED_WITH_WAITLIST."""
    guild_discord_id = "111222333444555666"
    channel_discord_id = "666555444333222111"
    bot_manager_role_id = "777666555444333222"

    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[bot_manager_role_id])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)

    seed_redis_cache(
        user_discord_id=test_user["discord_id"],
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[bot_manager_role_id, guild_discord_id],
        bot_manager_roles=[bot_manager_role_id],
    )

    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        name="INT_TEST Waitlist Template",
        description="Integration test template with waitlist support",
        allowed_signup_methods=[SignupMethod.HOST_SELECTED_WITH_WAITLIST.value],
        default_signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
    )

    return {
        "id": template["id"],
        "guild_id": guild_discord_id,
        "channel_id": channel_discord_id,
        "guild_config_id": guild["id"],
        "channel_config_id": channel["id"],
    }


def _insert_user_participant(
    admin_db_sync,
    game_id: str,
    user_id: str,
    position: int,
    position_type: ParticipantType = ParticipantType.SELF_ADDED,
) -> str:
    """Insert a participant linked to a real user."""
    participant_id = str(_uuid.uuid4())
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type, joined_at) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type, :joined_at)"
        ),
        {
            "id": participant_id,
            "game_id": game_id,
            "user_id": user_id,
            "position": position,
            "position_type": position_type,
            "joined_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()
    return participant_id


def test_host_selected_with_waitlist_signup_method_db_roundtrip(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify HOST_SELECTED_WITH_WAITLIST signup method persists through the full API → DB stack.

    Flow: HTTP POST → API (authenticated) → Database → value survives round trip
    """
    test_user = _create_test_user(create_user)
    test_template = _create_waitlist_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST HOST_SELECTED_WITH_WAITLIST Roundtrip",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.HOST_SELECTED_WITH_WAITLIST.value
    game_id = game_data["id"]

    result = admin_db_sync.execute(
        text("SELECT signup_method FROM game_sessions WHERE id = :game_id"),
        {"game_id": game_id},
    ).fetchone()
    assert result is not None, "Game not found in database"
    assert result[0] == SignupMethod.HOST_SELECTED_WITH_WAITLIST.value


def test_update_prefilled_upserts_self_added_participant(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify that including a SELF_ADDED participant in the PUT participants list
    converts them to HOST_ADDED for HOST_SELECTED_WITH_WAITLIST games.

    Flow: create game → insert SELF_ADDED participant via SQL → PUT with participant_id
    → DB shows HOST_ADDED
    """
    test_user = _create_test_user(create_user)
    test_template = _create_waitlist_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    create_response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Prefilled Upsert",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
            "max_players": "2",
        },
    )
    assert create_response.status_code in (200, 201), f"Create error: {create_response.text}"
    game_id = create_response.json()["id"]

    player_user = create_user()
    participant_id = _insert_user_participant(admin_db_sync, game_id, player_user["id"], position=1)

    update_response = authenticated_client.put(
        f"/api/v1/games/{game_id}",
        data={
            "participants": json.dumps([{"participant_id": participant_id, "position": 1}]),
        },
    )
    assert update_response.status_code == 200, f"Update error: {update_response.text}"

    result = admin_db_sync.execute(
        text("SELECT position_type FROM game_participants WHERE id = :participant_id"),
        {"participant_id": participant_id},
    ).fetchone()
    assert result is not None, "Participant not found in database"
    assert result[0] == ParticipantType.HOST_ADDED, f"Expected HOST_ADDED but got {result[0]}"


def test_demotion_notification_published_when_participant_demoted(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify demotion notification is published to QUEUE_NOTIFICATION when max_players is reduced.

    Flow: create game (max_players=2) → add 2 SELF_ADDED participants → PUT max_players=1
    → assert waitlist_demotion event published to notification queue.
    """
    test_user = _create_test_user(create_user)
    test_template = _create_waitlist_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)
    rabbitmq_channel.queue_purge(QUEUE_NOTIFICATION)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    create_response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Demotion Notification",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
            "max_players": "2",
        },
    )
    assert create_response.status_code in (200, 201), f"Create error: {create_response.text}"
    game_id = create_response.json()["id"]

    user_a = create_user()
    user_b = create_user()
    _insert_user_participant(
        admin_db_sync, game_id, user_a["id"], position=1, position_type=ParticipantType.HOST_ADDED
    )
    _insert_user_participant(
        admin_db_sync, game_id, user_b["id"], position=2, position_type=ParticipantType.HOST_ADDED
    )

    rabbitmq_channel.queue_purge(QUEUE_NOTIFICATION)

    update_response = authenticated_client.put(
        f"/api/v1/games/{game_id}",
        data={"max_players": "1"},
    )
    assert update_response.status_code == 200, f"Update error: {update_response.text}"

    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_NOTIFICATION, timeout=5)

    assert method is not None, "No demotion notification found in notification_queue"
    assert body is not None, "Notification message body is None"
    message = json.loads(body)

    assert message.get("event_type") == "notification.send_dm", (
        f"Expected notification.send_dm but got {message.get('event_type')}"
    )
    assert message.get("data", {}).get("notification_type") == "waitlist_demotion", (
        f"Expected waitlist_demotion but got {message.get('data', {}).get('notification_type')}"
    )


def test_api_creates_host_selected_game_with_initial_participants(
    admin_db_sync,
    rabbitmq_channel,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """
    Verify HOST_SELECTED games can be created with pre-populated participants.

    Tests integration between signup_method and initial_participants features.
    Validates that HOST_SELECTED mode works correctly with participant pre-population.
    """
    test_user = _create_test_user(create_user)
    test_template = _create_test_template(
        create_guild, create_channel, create_template, seed_redis_cache, test_user
    )
    authenticated_client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)

    rabbitmq_channel.queue_purge(QUEUE_BOT_EVENTS)

    scheduled_at = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    # Create game with HOST_SELECTED and two placeholder participants
    # Using placeholders (not @mentions) to avoid Discord API calls
    response = authenticated_client.post(
        "/api/v1/games",
        data={
            "template_id": test_template["id"],
            "title": "INT_TEST Host Selected with Participants",
            "scheduled_at": scheduled_at,
            "signup_method": SignupMethod.HOST_SELECTED.value,
            "initial_participants": json.dumps(["Player One", "Player Two"]),
        },
    )

    assert response.status_code in (200, 201), f"API error: {response.text}"
    game_data = response.json()
    assert game_data["signup_method"] == SignupMethod.HOST_SELECTED.value
    assert game_data["participant_count"] == 2, "Should have 2 pre-populated participants"

    game_id = game_data["id"]

    # Verify database has participants with correct position_type
    results = admin_db_sync.execute(
        text(
            "SELECT position_type, position, display_name FROM game_participants "
            "WHERE game_session_id = :game_id ORDER BY position"
        ),
        {"game_id": game_id},
    ).fetchall()

    assert len(results) == 2, "Should have 2 participants in database"
    for result in results:
        assert result[0] == ParticipantType.HOST_ADDED, (
            "Participants should have HOST_ADDED position_type"
        )
        assert result[1] > 0, "Participants should have positive positions"
        assert result[2] in [
            "Player One",
            "Player Two",
        ], f"Unexpected participant: {result[2]}"

    # Verify RabbitMQ message has correct signup_method
    time.sleep(0.5)
    method, properties, body = consume_one_message(rabbitmq_channel, QUEUE_BOT_EVENTS, timeout=5)

    assert method is not None
    assert body is not None, "Message body is None"
    message = json.loads(body)
    assert message["data"]["signup_method"] == SignupMethod.HOST_SELECTED.value

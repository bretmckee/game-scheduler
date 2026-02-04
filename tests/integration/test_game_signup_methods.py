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
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.messaging.infrastructure import QUEUE_BOT_EVENTS
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

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


"""Integration tests: editing an announced game's details DMs its participants.

PUT /api/v1/games/{id} on an announced game must enqueue one game_updated
send_dm row per confirmed and waitlisted participant when the time changes,
and none when nothing it notifies about changed.
"""

import uuid as _uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.utils.discord_tokens import extract_bot_discord_id

pytestmark = pytest.mark.integration

TEST_DISCORD_TOKEN = "MTQ0NDA3ODM4NjM4MDAxMzY0OA.GvmbbW.fake_token_for_integration_tests"
TEST_BOT_DISCORD_ID = extract_bot_discord_id(TEST_DISCORD_TOKEN)
BOT_MANAGER_ROLE_ID = "761234567890123456"
ANNOUNCED_MESSAGE_ID = "765999999999999999"


def _make_context(
    create_guild,
    create_channel,
    create_user,
    create_template,
    seed_redis_cache,
    *,
    guild_discord_id: str,
    channel_discord_id: str,
):
    guild = create_guild(discord_guild_id=guild_discord_id, bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    channel = create_channel(guild_id=guild["id"], discord_channel_id=channel_discord_id)
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(
        guild_id=guild["id"],
        channel_id=channel["id"],
        allowed_signup_methods=[SignupMethod.HOST_SELECTED_WITH_WAITLIST.value],
        default_signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
    )
    seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
        user_roles=[BOT_MANAGER_ROLE_ID, guild_discord_id],
        bot_manager_roles=[BOT_MANAGER_ROLE_ID],
    )
    return {"template_id": template["id"]}


def _insert_participant(admin_db_sync, game_id: str, user_id: str, position: int) -> None:
    admin_db_sync.execute(
        text(
            "INSERT INTO game_participants "
            "(id, game_session_id, user_id, position, position_type, joined_at) "
            "VALUES (:id, :game_id, :user_id, :position, :position_type, :joined_at)"
        ),
        {
            "id": str(_uuid.uuid4()),
            "game_id": game_id,
            "user_id": user_id,
            "position": position,
            "position_type": ParticipantType.HOST_ADDED,
            "joined_at": datetime.now(UTC),
        },
    )
    admin_db_sync.commit()


def _create_announced_game(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
    *,
    guild_discord_id: str,
    channel_discord_id: str,
    scheduled_at: datetime,
):
    """Create a max_players=1 game with one confirmed and one waitlisted user, marked announced."""
    ctx = _make_context(
        create_guild,
        create_channel,
        create_user,
        create_template,
        seed_redis_cache,
        guild_discord_id=guild_discord_id,
        channel_discord_id=channel_discord_id,
    )
    confirmed_user = create_user()
    waitlisted_user = create_user()

    client = create_authenticated_client(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    create_resp = client.post(
        "/api/v1/games",
        data={
            "template_id": ctx["template_id"],
            "title": "INT_TEST Change Notification Game",
            "scheduled_at": scheduled_at.isoformat(),
            "signup_method": SignupMethod.HOST_SELECTED_WITH_WAITLIST.value,
            "max_players": "1",
        },
    )
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    game_id = create_resp.json()["id"]

    _insert_participant(admin_db_sync, game_id, confirmed_user["id"], position=1)
    _insert_participant(admin_db_sync, game_id, waitlisted_user["id"], position=2)

    admin_db_sync.execute(
        text("UPDATE game_sessions SET message_id = :message_id WHERE id = :id"),
        {"message_id": ANNOUNCED_MESSAGE_ID, "id": game_id},
    )
    admin_db_sync.commit()

    return client, game_id, [confirmed_user["discord_id"], waitlisted_user["discord_id"]]


def _game_updated_dms(admin_db_sync, game_id: str) -> list[tuple[str, dict]]:
    rows = admin_db_sync.execute(
        text(
            "SELECT discord_id, payload FROM bot_action_queue "
            "WHERE action_type = 'send_dm' AND game_id = :game_id"
        ),
        {"game_id": game_id},
    ).fetchall()
    return [(row[0], row[1]) for row in rows if row[1].get("notification_type") == "game_updated"]


def _scheduled_at() -> datetime:
    return (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0)


def test_time_change_dms_confirmed_and_waitlisted_participants(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """Moving an announced game's time enqueues one game_updated DM per participant."""
    original_time = _scheduled_at()
    client, game_id, participant_discord_ids = _create_announced_game(
        admin_db_sync,
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        create_authenticated_client,
        guild_discord_id="765111111111111111",
        channel_discord_id="765111111111111112",
        scheduled_at=original_time,
    )

    new_time = original_time + timedelta(hours=2)
    update_resp = client.put(
        f"/api/v1/games/{game_id}", data={"scheduled_at": new_time.isoformat()}
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    dms = _game_updated_dms(admin_db_sync, game_id)
    assert sorted(discord_id for discord_id, _ in dms) == sorted(participant_discord_ids), (
        f"Expected exactly one game_updated DM per participant, got: {dms}"
    )
    for _, payload in dms:
        assert f"<t:{int(original_time.timestamp())}:F>" in payload["message"]
        assert f"<t:{int(new_time.timestamp())}:F>" in payload["message"]
        assert payload["game_time_unix"] == int(new_time.timestamp())


def test_resubmitting_same_time_sends_no_dm(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """Saving an announced game with its unchanged time enqueues no game_updated DM."""
    original_time = _scheduled_at()
    client, game_id, _ = _create_announced_game(
        admin_db_sync,
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        create_authenticated_client,
        guild_discord_id="765222222222222222",
        channel_discord_id="765222222222222223",
        scheduled_at=original_time,
    )

    update_resp = client.put(
        f"/api/v1/games/{game_id}", data={"scheduled_at": original_time.isoformat()}
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    assert _game_updated_dms(admin_db_sync, game_id) == []


def test_title_only_change_sends_no_dm(
    admin_db_sync,
    create_user,
    create_guild,
    create_channel,
    create_template,
    seed_redis_cache,
    create_authenticated_client,
):
    """Changing only an announced game's title enqueues no game_updated DM."""
    client, game_id, _ = _create_announced_game(
        admin_db_sync,
        create_user,
        create_guild,
        create_channel,
        create_template,
        seed_redis_cache,
        create_authenticated_client,
        guild_discord_id="765333333333333333",
        channel_discord_id="765333333333333334",
        scheduled_at=_scheduled_at(),
    )

    update_resp = client.put(
        f"/api/v1/games/{game_id}", data={"title": "INT_TEST Renamed Change Notification Game"}
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    title_row = admin_db_sync.execute(
        text("SELECT title FROM game_sessions WHERE id = :id"), {"id": game_id}
    ).fetchone()
    assert title_row[0] == "INT_TEST Renamed Change Notification Game"
    assert _game_updated_dms(admin_db_sync, game_id) == []

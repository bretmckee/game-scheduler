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


"""End-to-end tests for recurring game lifecycle.

Tests the complete recurring game flow using a live Docker stack:
- COMPLETED transition triggers recurrence clone creation (bot EventHandlers)
- Host confirms clone via PUT with clear_post_at=true
- AnnouncementLoop posts the Discord message for the confirmed clone
- Zombie recurrence clones (post_at=NULL, never confirmed) are cancelled at IN_PROGRESS

Requires:
- PostgreSQL with migrations applied and E2E data seeded by init service
- RabbitMQ with exchanges/queues configured
- Discord bot connected to test guild (BOT_SKIP_STARTUP not set)
- Status transition daemon running to process transitions
- API service running on localhost:8000
- Full stack via compose.e2e.yaml profile
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from shared.models import GameStatus
from tests.e2e.conftest import (
    TimeoutType,
    wait_for_db_condition,
    wait_for_game_message_id,
)

pytestmark = pytest.mark.e2e

_RECUR_RULE = "FREQ=WEEKLY;BYDAY=SA"

# Seconds before scheduled_at; gives daemon polling time to catch the transition.
_SCHEDULED_DELAY_SECONDS = 30


@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_recurring_game_host_confirms_via_api(
    authenticated_admin_client,
    authenticated_player_a_client,
    admin_db,
    synced_guild,
    test_timeouts,
):
    """
    E2E: COMPLETED game with recur_rule → bot creates clone → host confirms via API.

    Verifies:
    - Parent game with recur_rule completes via status-transition daemon (~3 min)
    - Bot EventHandlers create a recurrence clone with post_at=NULL, message_id=NULL
    - PUT /{clone_id} with clear_post_at=true triggers AnnouncementLoop via NOTIFY
    - AnnouncementLoop posts Discord message (message_id populated within 60s)
    - Player A can see the announced clone via GET /api/v1/games
    """
    scheduled_time = datetime.now(UTC) + timedelta(seconds=_SCHEDULED_DELAY_SECONDS)
    game_title = f"E2E Recurrence Confirm Test {uuid4().hex[:8]}"

    response = await authenticated_admin_client.post(
        "/api/v1/games",
        data={
            "template_id": synced_guild.template_id,
            "title": game_title,
            "description": "E2E test: recurring game host confirmation flow",
            "scheduled_at": scheduled_time.isoformat(),
            "max_players": "4",
            "expected_duration_minutes": "1",
        },
    )
    assert response.status_code == 201, f"Failed to create game: {response.text}"
    parent_id = response.json()["id"]
    print(f"\n[TEST] Parent game created: {parent_id}")

    # Set recur_rule directly — the create endpoint does not expose it as a form field.
    await admin_db.execute(
        text("UPDATE game_sessions SET recur_rule = :recur_rule WHERE id = :game_id"),
        {"recur_rule": _RECUR_RULE, "game_id": parent_id},
    )
    await admin_db.commit()
    print(f"[TEST] recur_rule set to: {_RECUR_RULE}")

    print(
        "[TEST] Waiting for COMPLETED status "
        f"(~{_SCHEDULED_DELAY_SECONDS}s + 1min duration + daemon polling)..."
    )
    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": parent_id},
        lambda row: row[0] == GameStatus.COMPLETED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="parent game transition to COMPLETED",
    )
    print("[TEST] ✓ Parent game COMPLETED")

    print("[TEST] Waiting for bot to create recurrence clone...")
    await wait_for_db_condition(
        admin_db,
        (
            "SELECT COUNT(*) FROM game_sessions "
            "WHERE guild_id = :guild_id AND id != :parent_id AND recur_rule IS NOT NULL"
        ),
        {"guild_id": synced_guild.db_id, "parent_id": parent_id},
        lambda row: row[0] > 0,
        timeout=15,
        interval=2,
        description="recurrence clone creation by bot",
    )

    admin_db.expire_all()
    result = await admin_db.execute(
        text(
            "SELECT id, post_at, message_id FROM game_sessions "
            "WHERE guild_id = :guild_id AND id != :parent_id AND recur_rule IS NOT NULL "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"guild_id": synced_guild.db_id, "parent_id": parent_id},
    )
    clone_row = result.fetchone()
    assert clone_row is not None, "Recurrence clone not found after parent COMPLETED"
    clone_id, clone_post_at, clone_message_id = clone_row
    assert clone_post_at is None, f"Clone should have post_at=NULL, got {clone_post_at}"
    assert clone_message_id is None, f"Clone should have message_id=NULL, got {clone_message_id}"
    print(f"[TEST] ✓ Recurrence clone exists: {clone_id}, post_at=NULL, message_id=NULL")

    response = await authenticated_admin_client.put(
        f"/api/v1/games/{clone_id}",
        data={"clear_post_at": "true"},
    )
    assert response.status_code == 200, f"PUT clear_post_at failed: {response.text}"
    print("[TEST] ✓ Admin confirmed clone via PUT clear_post_at=true")

    print("[TEST] Waiting for Discord announcement (up to 60s)...")
    message_id = await wait_for_game_message_id(
        admin_db,
        clone_id,
        timeout=60,
    )
    assert message_id is not None, "Clone Discord message was never posted"
    print(f"[TEST] ✓ Clone announced, message_id={message_id}")

    response = await authenticated_player_a_client.get(
        f"/api/v1/games?guild_id={synced_guild.db_id}"
    )
    assert response.status_code == 200, f"Player A GET /api/v1/games failed: {response.text}"
    game_ids = [g["id"] for g in response.json()["games"]]
    assert clone_id in game_ids, f"Player A should see the confirmed clone {clone_id} in game list"
    print("[TEST] ✓ Player A can see confirmed clone in game list")


@pytest.mark.timeout(360)
@pytest.mark.asyncio
async def test_recurring_game_zombie_cancelled_when_unconfirmed(
    admin_db,
    synced_guild,
    test_user_a,
    test_timeouts,
):
    """
    E2E: Recurrence clone with post_at=NULL never confirmed → status daemon cancels it.

    Verifies:
    - A game with post_at=NULL and recur_rule set (zombie) is inserted directly in DB
    - Status transition daemon fires IN_PROGRESS transition at scheduled_at
    - Bot EventHandlers detect zombie (message_id=NULL + recur_rule IS NOT NULL) and cancel it
    - Clone status becomes CANCELLED and message_id remains NULL

    The zombie is inserted directly rather than waiting for a parent game to complete,
    because the parent's auto-clone would be scheduled a week out and not suitable
    for testing the cancellation path within a reasonable timeout.
    """
    scheduled_time = datetime.now(UTC) + timedelta(seconds=_SCHEDULED_DELAY_SECONDS)
    zombie_id = str(uuid4())
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    scheduled_naive = scheduled_time.replace(tzinfo=None)

    await admin_db.execute(
        text(
            "INSERT INTO game_sessions "
            "(id, guild_id, channel_id, host_id, title, description, "
            "scheduled_at, max_players, status, recur_rule, post_at, message_id, "
            "expected_duration_minutes, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :host_id, :title, :description, "
            ":scheduled_at, :max_players, :status, :recur_rule, :post_at, :message_id, "
            ":expected_duration_minutes, :created_at, :updated_at)"
        ),
        {
            "id": zombie_id,
            "guild_id": synced_guild.db_id,
            "channel_id": synced_guild.channel_db_id,
            "host_id": str(test_user_a.id),
            "title": f"E2E Zombie Clone Test {uuid4().hex[:8]}",
            "description": "E2E test: zombie recurrence clone cancellation",
            "scheduled_at": scheduled_naive,
            "max_players": 4,
            "status": GameStatus.SCHEDULED.value,
            "recur_rule": _RECUR_RULE,
            "post_at": None,
            "message_id": None,
            "expected_duration_minutes": 1,
            "created_at": now_naive,
            "updated_at": now_naive,
        },
    )
    await admin_db.execute(
        text(
            "INSERT INTO game_status_schedule "
            "(id, game_id, target_status, transition_time, executed) "
            "VALUES (:id, :game_id, :target_status, :transition_time, :executed)"
        ),
        {
            "id": str(uuid4()),
            "game_id": zombie_id,
            "target_status": GameStatus.IN_PROGRESS.value,
            "transition_time": scheduled_naive,
            "executed": False,
        },
    )
    await admin_db.execute(
        text(
            "INSERT INTO game_status_schedule "
            "(id, game_id, target_status, transition_time, executed) "
            "VALUES (:id, :game_id, :target_status, :transition_time, :executed)"
        ),
        {
            "id": str(uuid4()),
            "game_id": zombie_id,
            "target_status": GameStatus.COMPLETED.value,
            "transition_time": scheduled_naive + timedelta(minutes=1),
            "executed": False,
        },
    )
    await admin_db.commit()
    print(f"\n[TEST] Zombie clone inserted: {zombie_id}, scheduled_at={scheduled_naive}")

    print(
        f"[TEST] Waiting for status daemon to fire IN_PROGRESS transition "
        f"(~{_SCHEDULED_DELAY_SECONDS}s + daemon polling)..."
    )
    await wait_for_db_condition(
        admin_db,
        "SELECT status FROM game_sessions WHERE id = :game_id",
        {"game_id": zombie_id},
        lambda row: row[0] != GameStatus.SCHEDULED.value,
        timeout=test_timeouts[TimeoutType.STATUS_TRANSITION],
        interval=5,
        description="zombie clone transition from SCHEDULED",
    )

    admin_db.expire_all()
    result = await admin_db.execute(
        text("SELECT status, message_id FROM game_sessions WHERE id = :game_id"),
        {"game_id": zombie_id},
    )
    row = result.fetchone()
    assert row is not None, "Zombie game not found in DB"
    status, message_id = row
    assert status == GameStatus.CANCELLED.value, f"Zombie clone should be CANCELLED, got {status}"
    assert message_id is None, (
        f"Zombie clone should have no Discord message, got message_id={message_id}"
    )
    print("[TEST] ✓ Zombie clone correctly cancelled with message_id=NULL")

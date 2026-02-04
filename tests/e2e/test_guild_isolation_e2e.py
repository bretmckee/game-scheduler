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


"""
E2E tests for cross-guild isolation via Row-Level Security.

Verifies that users can only access games and templates from their own guilds.
These tests require Guild B infrastructure (see TESTING_E2E.md section 6).

Tests are marked with xfail until RLS is enabled in Phase 3.2+.
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.shared.polling import wait_for_db_condition_async

pytestmark = pytest.mark.e2e


@pytest.fixture
async def guild_a_game_id(
    admin_db,
    authenticated_admin_client,
    guild_a_template_id,
):
    """Create a game in Guild A for isolation testing."""
    game_time = datetime.now(UTC) + timedelta(hours=24)

    game_data = {
        "template_id": guild_a_template_id,
        "title": "Guild A Test Game",
        "scheduled_at": game_time.isoformat(),
    }

    response = await authenticated_admin_client.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create Guild A game: {response.text}"
    game_response = response.json()
    game_id = game_response["id"]

    # Wait for game to be fully created in database
    def check_game_exists(result):
        return result is not None

    await wait_for_db_condition_async(
        admin_db,
        "SELECT id FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        check_game_exists,
        timeout=10,
        description=f"Guild A game {game_id} to exist in database",
    )

    yield game_id

    # Cleanup
    await authenticated_admin_client.delete(f"/api/v1/games/{game_id}")


@pytest.fixture
async def guild_b_game_id(
    admin_db,
    authenticated_client_b,
    guild_b_template_id,
):
    """Create a game in Guild B for isolation testing."""
    game_time = datetime.now(UTC) + timedelta(hours=24)

    # First, sync Guild B
    sync_response = await authenticated_client_b.post("/api/v1/guilds/sync")
    assert sync_response.status_code == 200, f"Failed to sync Guild B: {sync_response.text}"

    # Create game in Guild B using template
    game_data = {
        "template_id": guild_b_template_id,
        "title": "Guild B Test Game",
        "scheduled_at": game_time.isoformat(),
    }

    response = await authenticated_client_b.post("/api/v1/games", data=game_data)
    assert response.status_code == 201, f"Failed to create Guild B game: {response.text}"
    game_response = response.json()
    game_id = game_response["id"]

    # Wait for game to be fully created in database
    def check_game_exists(result):
        return result is not None

    await wait_for_db_condition_async(
        admin_db,
        "SELECT id FROM game_sessions WHERE id = :game_id",
        {"game_id": game_id},
        check_game_exists,
        timeout=10,
        description=f"Guild B game {game_id} to exist in database",
    )

    yield game_id

    # Cleanup
    await authenticated_client_b.delete(f"/api/v1/games/{game_id}")


async def test_user_cannot_list_games_from_other_guilds(
    authenticated_admin_client,
    authenticated_client_b,
    guild_a_game_id,
    guild_b_game_id,
):
    """
    User A in Guild A cannot see games from Guild B in list endpoint.

    Expected behavior after RLS enabled:
    - User A lists games → sees only Guild A games
    - User B lists games → sees only Guild B games
    """
    # User A (admin client) lists games - should only see Guild A games
    response_a = await authenticated_admin_client.get("/api/v1/games")
    assert response_a.status_code == 200

    games_a = response_a.json()["games"]
    game_a_ids = {game["id"] for game in games_a}

    # After RLS enabled: Guild A game visible, Guild B game NOT visible
    assert guild_a_game_id in game_a_ids, "User A should see their own Guild A game"
    assert guild_b_game_id not in game_a_ids, (
        "User A should NOT see Guild B game (RLS should filter it out)"
    )

    # User B lists games - should only see Guild B games
    response_b = await authenticated_client_b.get("/api/v1/games")
    assert response_b.status_code == 200

    games_b = response_b.json()["games"]
    game_b_ids = {game["id"] for game in games_b}

    # After RLS enabled: Guild B game visible, Guild A game NOT visible
    assert guild_b_game_id in game_b_ids, "User B should see their own Guild B game"
    assert guild_a_game_id not in game_b_ids, (
        "User B should NOT see Guild A game (RLS should filter it out)"
    )


async def test_user_cannot_get_game_from_other_guild_by_id(
    authenticated_admin_client,
    guild_b_game_id,
):
    """
    User A cannot fetch Guild B's game by ID (RLS returns 404).

    Expected behavior after RLS enabled:
    - GET /api/v1/games/{guild_b_game_id} → 404 (game filtered by RLS)
    """
    response = await authenticated_admin_client.get(f"/api/v1/games/{guild_b_game_id}")

    # After RLS enabled: RLS filters game, query returns None, route returns 404
    assert response.status_code == 404, (
        "User A should get 404 when accessing Guild B game (RLS should filter it)"
    )


async def test_user_cannot_join_game_from_other_guild(
    authenticated_admin_client,
    guild_b_game_id,
):
    """
    User A cannot join Guild B's game.

    Expected behavior after RLS enabled:
    - POST /api/v1/games/{guild_b_game_id}/join → 404
    - RLS filters game in get_game() call (line 502 of games.py)
    - Route returns 404 before reaching authorization checks
    """
    response = await authenticated_admin_client.post(f"/api/v1/games/{guild_b_game_id}/join")

    # After RLS enabled: RLS filters game at DB level, get_game returns None → 404
    assert response.status_code == 404, (
        "User A should get 404 when joining Guild B game (RLS filters it from get_game)"
    )


async def test_user_cannot_update_game_from_other_guild(
    authenticated_admin_client,
    guild_b_game_id,
):
    """
    User A cannot update Guild B's game.

    Expected behavior after RLS enabled:
    - PUT /api/v1/games/{guild_b_game_id} → 404
    """
    response = await authenticated_admin_client.put(
        f"/api/v1/games/{guild_b_game_id}",
        data={"title": "Hacked Guild B Game"},
    )

    # After RLS enabled: RLS filters game, service returns 404
    assert response.status_code == 404, (
        "User A should get 404 when updating Guild B game (RLS should filter it)"
    )


async def test_user_cannot_delete_game_from_other_guild(
    authenticated_admin_client,
    guild_b_game_id,
):
    """
    User A cannot delete Guild B's game.

    Expected behavior after RLS enabled:
    - DELETE /api/v1/games/{guild_b_game_id} → 404
    """
    response = await authenticated_admin_client.delete(f"/api/v1/games/{guild_b_game_id}")

    # After RLS enabled: RLS filters game, service returns 404
    assert response.status_code == 404, (
        "User A should get 404 when deleting Guild B game (RLS should filter it)"
    )


async def test_templates_isolated_across_guilds(
    authenticated_admin_client,
    authenticated_client_b,
    admin_db,
    guild_a_db_id,
    guild_b_db_id,
    guild_b_template_id,
):
    """
    Template listing and access respects guild isolation.

    Expected behavior after RLS enabled:
    - User A lists templates for Guild A → sees only Guild A templates
    - User A attempts to access Guild B template → 404
    """
    # User A lists templates for Guild A (using database UUID)
    response = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_a_db_id}/templates")
    assert response.status_code == 200

    templates_a = response.json()
    template_a_ids = {template["id"] for template in templates_a}

    # After RLS enabled: Guild B template should NOT be visible in Guild A's list
    assert guild_b_template_id not in template_a_ids, (
        "User A should NOT see Guild B template in Guild A template list"
    )

    # User A attempts to access Guild B template directly → should get 404
    # Note: Using Guild B's database UUID in the path - this is what the endpoint expects
    response_cross = await authenticated_admin_client.get(
        f"/api/v1/guilds/{guild_b_db_id}/templates/{guild_b_template_id}"
    )

    # After RLS enabled: RLS filters template, route returns 404
    assert response_cross.status_code == 404, (
        "User A should get 404 when accessing Guild B template (RLS should filter it)"
    )


async def test_participants_isolated_across_guilds(
    admin_db,
    authenticated_admin_client,
    authenticated_client_b,
    guild_a_game_id,
    guild_b_game_id,
):
    """
    Game participants are isolated by guild via RLS policy.

    Expected behavior after RLS enabled:
    - User A joins Guild A game → participant record created
    - User B joins Guild B game → participant record created
    - User A lists Guild A game participants → sees only Guild A participants
    - User A cannot see Guild B participants (via game isolation)
    """
    # User A joins Guild A game
    response_a = await authenticated_admin_client.post(f"/api/v1/games/{guild_a_game_id}/join")
    assert response_a.status_code == 200

    # User B joins Guild B game
    response_b = await authenticated_client_b.post(f"/api/v1/games/{guild_b_game_id}/join")
    assert response_b.status_code == 200

    # Wait for participants to be created
    def check_participant_exists(result):
        return result is not None

    await wait_for_db_condition_async(
        admin_db,
        "SELECT id FROM game_participants WHERE game_session_id = :game_id",
        {"game_id": guild_a_game_id},
        check_participant_exists,
        timeout=10,
        description="Guild A participant to exist",
    )

    await wait_for_db_condition_async(
        admin_db,
        "SELECT id FROM game_participants WHERE game_session_id = :game_id",
        {"game_id": guild_b_game_id},
        check_participant_exists,
        timeout=10,
        description="Guild B participant to exist",
    )

    # User A gets Guild A game details (includes participants)
    response = await authenticated_admin_client.get(f"/api/v1/games/{guild_a_game_id}")
    assert response.status_code == 200

    game_data = response.json()
    participants = game_data.get("participants", [])

    # After RLS enabled: Should only see Guild A participants
    # (Guild B participants are in different game, so this is more about game isolation)
    assert len(participants) > 0, "Guild A game should have participants"

    # User A cannot access Guild B game (which would show Guild B participants)
    response_b = await authenticated_admin_client.get(f"/api/v1/games/{guild_b_game_id}")
    assert response_b.status_code == 404, (
        "User A should get 404 for Guild B game (and thus cannot see its participants)"
    )

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


"""
E2E tests for guild routes using require_guild_by_id.

Tests verify that migrated guild routes enforce authorization:
- Users can access guilds they belong to
- Users get 404 for guilds they don't belong to (cross-guild isolation)
- Non-existent guilds return 404

These tests verify the authorization enforcement in require_guild_by_id,
which provides defense-in-depth before full RLS is enabled.
"""

import pytest

pytestmark = pytest.mark.e2e


async def test_get_guild_returns_own_guild_info(
    authenticated_admin_client,
    guild_a_db_id,
):
    """User can retrieve basic info about guilds they belong to (positive test)."""
    response = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_a_db_id}")

    assert response.status_code == 200, f"Failed to get guild: {response.text}"
    guild = response.json()
    assert guild["id"] == guild_a_db_id
    assert "guild_name" in guild
    assert "created_at" in guild
    assert "updated_at" in guild


async def test_get_guild_enforces_authorization(
    authenticated_admin_client,
    authenticated_client_b,
    guild_b_db_id,
):
    """
    require_guild_by_id enforces authorization - users cannot access other guilds.

    Expected behavior:
    - User A tries to access Guild B → 404 (authorization check in require_guild_by_id)
    - User B can access Guild B → 200
    """
    # User B can access their own guild
    response_b = await authenticated_client_b.get(f"/api/v1/guilds/{guild_b_db_id}")
    assert response_b.status_code == 200, "User B should access Guild B successfully"

    # User A (admin, in Guild A only) cannot access Guild B
    response_a = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_b_db_id}")
    assert response_a.status_code == 404, (
        "User A should get 404 when accessing Guild B (not in their guild list)"
    )


async def test_get_guild_returns_404_for_nonexistent(
    authenticated_admin_client,
):
    """Returns 404 for non-existent guild UUIDs."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    response = await authenticated_admin_client.get(f"/api/v1/guilds/{fake_uuid}")

    assert response.status_code == 404, "Should return 404 for non-existent guild"


async def test_get_guild_config_returns_configuration(
    authenticated_admin_client,
    guild_a_db_id,
):
    """User with MANAGE_GUILD permission can retrieve configuration."""
    response = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_a_db_id}/config")

    assert response.status_code == 200, f"Failed to get guild config: {response.text}"
    config = response.json()
    assert config["id"] == guild_a_db_id
    assert "require_host_role" in config
    assert "bot_manager_role_ids" in config


async def test_get_guild_config_enforces_authorization(
    authenticated_admin_client,
    authenticated_client_b,
    guild_b_db_id,
):
    """
    Config routes require MANAGE_GUILD permission.

    Expected behavior:
    - User A tries to get Guild B config → 404 (not authorized - prevents info disclosure)
    - User B with permission can get Guild B config → 200
    """
    # User B can access their guild config
    response_b = await authenticated_client_b.get(f"/api/v1/guilds/{guild_b_db_id}/config")
    assert response_b.status_code == 200, "User B should access Guild B config"

    # User A gets 404 (not 403) to prevent information disclosure
    response_a = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_b_db_id}/config")
    assert response_a.status_code == 404, (
        "User A should get 404 for Guild B config (not authorized - prevents info disclosure)"
    )


async def test_update_guild_config_enforces_authorization(
    authenticated_admin_client,
    guild_b_db_id,
):
    """
    Config update requires MANAGE_GUILD permission.

    Expected behavior:
    - User A tries to update Guild B config → 404 (not authorized - prevents info disclosure)
    """
    update_data = {"require_host_role": True}
    response = await authenticated_admin_client.put(
        f"/api/v1/guilds/{guild_b_db_id}", json=update_data
    )

    assert response.status_code == 404, (
        "User A should get 404 when updating Guild B config "
        "(not authorized - prevents info disclosure)"
    )


async def test_list_guild_channels_enforces_authorization(
    authenticated_admin_client,
    authenticated_client_b,
    guild_b_db_id,
):
    """
    require_guild_by_id enforces authorization for channel listing.

    Expected behavior:
    - User A tries to list Guild B channels → 404
    - User B can list Guild B channels → 200
    """
    # User B can list their guild channels
    response_b = await authenticated_client_b.get(f"/api/v1/guilds/{guild_b_db_id}/channels")
    assert response_b.status_code == 200, "User B should list Guild B channels"
    assert isinstance(response_b.json(), list)

    # User A cannot list Guild B channels
    response_a = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_b_db_id}/channels")
    assert response_a.status_code == 404, (
        "User A should get 404 for Guild B channels (authorization check)"
    )


async def test_list_guild_roles_enforces_authorization(
    authenticated_admin_client,
    authenticated_client_b,
    guild_b_db_id,
):
    """
    require_guild_by_id enforces authorization for role listing.

    Expected behavior:
    - User A tries to list Guild B roles → 404
    - User B can list Guild B roles → 200
    """
    # User B can list their guild roles
    response_b = await authenticated_client_b.get(f"/api/v1/guilds/{guild_b_db_id}/roles")
    assert response_b.status_code == 200, "User B should list Guild B roles"
    assert isinstance(response_b.json(), list)

    # User A cannot list Guild B roles
    response_a = await authenticated_admin_client.get(f"/api/v1/guilds/{guild_b_db_id}/roles")
    assert response_a.status_code == 404, (
        "User A should get 404 for Guild B roles (authorization check)"
    )


async def test_validate_mention_enforces_authorization(
    authenticated_admin_client,
    authenticated_client_b,
    guild_b_db_id,
):
    """
    require_guild_by_id enforces authorization for mention validation.

    Expected behavior:
    - User A tries to validate mention for Guild B → 404
    - User B can validate mention for Guild B → 200
    """
    request_data = {"mention": "<@&123456789012345678>"}

    # User B can validate mentions for their guild
    response_b = await authenticated_client_b.post(
        f"/api/v1/guilds/{guild_b_db_id}/validate-mention",
        json=request_data,
    )
    assert response_b.status_code == 200, "User B should validate mentions for Guild B"
    assert "valid" in response_b.json()

    # User A cannot validate mentions for Guild B
    response_a = await authenticated_admin_client.post(
        f"/api/v1/guilds/{guild_b_db_id}/validate-mention",
        json=request_data,
    )
    assert response_a.status_code == 404, (
        "User A should get 404 for Guild B mention validation (authorization check)"
    )

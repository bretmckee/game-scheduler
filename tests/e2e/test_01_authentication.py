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


"""Test Phase 2: Bot authentication and guild sync fixtures."""

import pytest

pytestmark = pytest.mark.e2e


def test_bot_discord_id_extracted(bot_discord_id):
    """Verify bot Discord ID can be extracted from token."""
    assert bot_discord_id is not None
    assert len(bot_discord_id) > 0
    assert bot_discord_id.isdigit(), "Bot Discord ID should be numeric snowflake"


@pytest.mark.asyncio
async def test_authenticated_admin_client_has_session(authenticated_admin_client):
    """Verify authenticated admin client has session cookie."""
    assert "session_token" in authenticated_admin_client.cookies
    session_token = authenticated_admin_client.cookies.get("session_token")
    assert session_token is not None
    assert len(session_token) == 36, "Session token should be UUID4 format"


@pytest.mark.asyncio
async def test_authenticated_admin_client_can_call_api(authenticated_admin_client, discord_ids):
    """Verify authenticated admin client can make authenticated API calls."""
    response = await authenticated_admin_client.get(
        f"/api/v1/games?guild_id={discord_ids.guild_a_id}"
    )
    assert response.status_code == 200, f"Auth check failed: {response.text}"

    games_data = response.json()
    assert "games" in games_data


@pytest.mark.asyncio
async def test_synced_guild_creates_configs(synced_guild):
    """Verify guild sync creates necessary configurations."""
    assert synced_guild is not None
    assert synced_guild.db_id
    assert synced_guild.discord_id
    assert synced_guild.channel_db_id
    assert synced_guild.channel_discord_id
    assert synced_guild.template_id

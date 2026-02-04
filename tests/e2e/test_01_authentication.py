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

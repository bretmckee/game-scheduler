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


"""
E2E test for bot startup guild sync.

Uses pytest-order to ensure this runs first, before other E2E tests,
so we can verify bot startup automatic sync creates guilds correctly.
"""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.channel import ChannelConfiguration
from shared.models.guild import GuildConfiguration
from shared.models.template import GameTemplate
from tests.e2e.conftest import DiscordTestEnvironment

pytestmark = [pytest.mark.e2e, pytest.mark.order(0)]


@pytest.mark.asyncio
async def test_bot_startup_sync_creates_guilds(
    admin_db: AsyncSession,
    discord_ids: DiscordTestEnvironment,
) -> None:
    """
    Verify bot gateway sync creates guilds A and B.

    Calls POST /admin/sync-guilds on the bot test server to trigger
    sync_guilds_from_gateway, then verifies that guilds, channels, and
    default templates were created. This is the same code path used by
    bot.on_ready() at startup.

    Running this via the test server makes the test reliable whether the
    bot just started (fresh environment) or is already running (SKIP_STARTUP
    re-run where previous test fixtures may have deleted the guilds).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post("http://bot:8089/admin/sync-guilds", timeout=30.0)
        assert response.status_code == 200, f"sync-guilds returned {response.status_code}"

    # Query for guilds A and B
    result = await admin_db.execute(
        select(GuildConfiguration).where(
            GuildConfiguration.guild_id.in_([discord_ids.guild_a_id, discord_ids.guild_b_id])
        )
    )
    guilds = list(result.scalars().all())

    assert len(guilds) == 2, f"Expected 2 guilds, found {len(guilds)}"

    # Verify each guild has channels
    for guild in guilds:
        channels_result = await admin_db.execute(
            select(ChannelConfiguration).where(ChannelConfiguration.guild_id == guild.id)
        )
        channels = list(channels_result.scalars().all())
        assert len(channels) > 0, f"Guild {guild.guild_id} has no channels"

        # Verify each guild has default template
        templates_result = await admin_db.execute(
            select(GameTemplate).where(GameTemplate.guild_id == guild.id)
        )
        templates = list(templates_result.scalars().all())
        assert len(templates) > 0, f"Guild {guild.guild_id} has no default template"

        # Verify at least one template is marked as default
        has_default = any(t.is_default for t in templates)
        assert has_default, f"Guild {guild.guild_id} has no default template"

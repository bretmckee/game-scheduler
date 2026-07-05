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


"""Unit tests for repopulation triggered by reconnect and guild-available events."""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.bot import GameSchedulerBot


def _make_bot() -> GameSchedulerBot:
    cfg = MagicMock()
    cfg.discord_bot_client_id = "123456789"
    cfg.environment = "test"
    instance = GameSchedulerBot.__new__(GameSchedulerBot)
    instance.config = cfg
    instance.button_handler = None
    instance.event_handlers = None
    instance.api_cache = None
    instance._sweep_task = None
    instance._refresh_listener_started = True
    return instance


class TestOnResumedRepopulation:
    """on_resumed triggers repopulate_all after reconnect."""

    @pytest.mark.asyncio
    async def test_on_resumed_triggers_repopulate_all(self) -> None:
        """on_resumed calls guild_projection.repopulate_all with bot and redis."""
        bot = _make_bot()
        mock_redis = AsyncMock()

        with (
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch(
                "services.bot.bot.guild_projection.repopulate_all",
                new_callable=AsyncMock,
            ) as mock_repopulate,
            patch.object(bot, "_recover_pending_workers", new_callable=AsyncMock),
            patch.object(bot, "_trigger_sweep", new_callable=AsyncMock),
            patch.object(bot, "_sweep_orphaned_embeds", new_callable=AsyncMock),
        ):
            await bot.on_resumed()

        mock_repopulate.assert_awaited_once_with(bot=bot, redis=mock_redis)


class TestOnGuildAvailableRepopulation:
    """on_guild_available triggers repopulate_all when a guild recovers from an outage."""

    @pytest.mark.asyncio
    async def test_on_guild_available_triggers_repopulate_all(self) -> None:
        """on_guild_available calls guild_projection.repopulate_all with bot and redis."""
        bot = _make_bot()
        guild = MagicMock(spec=discord.Guild)
        guild.id = 111
        mock_redis = AsyncMock()

        with (
            patch(
                "services.bot.bot.get_redis_client",
                new_callable=AsyncMock,
                return_value=mock_redis,
            ),
            patch(
                "services.bot.bot.guild_projection.repopulate_all",
                new_callable=AsyncMock,
            ) as mock_repopulate,
        ):
            await bot.on_guild_available(guild)

        mock_repopulate.assert_awaited_once_with(bot=bot, redis=mock_redis)

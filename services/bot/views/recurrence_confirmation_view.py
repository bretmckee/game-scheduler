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


"""Discord UI view for recurrence confirmation DMs.

Sent to the game host when a recurring game completes. Confirm button
announces the next occurrence; decline button cancels it.
"""

import logging
from datetime import UTC, datetime
from typing import cast

import discord
from discord.ui import View
from sqlalchemy import select, text

from shared.database import get_db_session
from shared.models.game import GameSession
from shared.utils.status_transitions import GameStatus

logger = logging.getLogger(__name__)


class _ConfirmButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        view = cast("RecurrenceConfirmationView", self.view)
        await view.confirm(interaction)


class _DeclineButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        view = cast("RecurrenceConfirmationView", self.view)
        await view.decline(interaction)


class RecurrenceConfirmationView(View):
    """DM view with Confirm and Decline buttons for recurring game host confirmation."""

    def __init__(self, game_id: str) -> None:
        super().__init__(timeout=None)
        self.game_id = game_id

        self.confirm_button = _ConfirmButton(
            style=discord.ButtonStyle.success,
            label="Confirm",
            custom_id=f"recurrence_confirm_{game_id}",
        )
        self.decline_button = _DeclineButton(
            style=discord.ButtonStyle.danger,
            label="Decline",
            custom_id=f"recurrence_decline_{game_id}",
        )
        self.add_item(self.confirm_button)
        self.add_item(self.decline_button)

    async def confirm(self, interaction: discord.Interaction) -> None:
        """Handle confirm — sets post_at to now and wakes the announcement loop."""
        await interaction.response.defer(ephemeral=True)

        async with get_db_session() as db:
            result = await db.execute(select(GameSession).where(GameSession.id == self.game_id))
            game = result.scalar_one()
            game.post_at = datetime.now(UTC).replace(tzinfo=None)
            await db.execute(text("SELECT pg_notify('game_announcement_changed', '')"))
            await db.commit()
            logger.info("Recurrence confirmed: set post_at for game %s", self.game_id)

        await interaction.followup.send(
            "✅ Next session confirmed and will be announced!", ephemeral=True
        )
        await interaction.message.delete()

    async def decline(self, interaction: discord.Interaction) -> None:
        """Handle decline — cancels the cloned game immediately."""
        await interaction.response.defer(ephemeral=True)

        async with get_db_session() as db:
            result = await db.execute(select(GameSession).where(GameSession.id == self.game_id))
            game = result.scalar_one()
            game.status = GameStatus.CANCELLED.value
            await db.commit()
            logger.info("Recurrence declined: cancelled game %s", self.game_id)

        await interaction.followup.send("❌ Next session cancelled.", ephemeral=True)
        await interaction.message.delete()

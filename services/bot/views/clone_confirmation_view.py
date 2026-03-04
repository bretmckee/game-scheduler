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


"""Discord UI view for clone confirmation DMs.

Sent to carried-over participants when YES_WITH_DEADLINE carryover is used.
Confirm button clears the pending drop schedule; decline button triggers
the drop handler immediately.
"""

import logging
from typing import cast

import discord
from discord.ui import View
from sqlalchemy import select, text

from services.bot.events.publisher import BotEventPublisher
from services.bot.handlers.participant_drop import handle_participant_drop_due
from shared.database import get_db_session
from shared.models.participant_action_schedule import ParticipantActionSchedule

logger = logging.getLogger(__name__)


class _ConfirmButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        view = cast("CloneConfirmationView", self.view)
        await view._confirm_callback(interaction)


class _DeclineButton(discord.ui.Button):
    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        view = cast("CloneConfirmationView", self.view)
        await view._decline_callback(interaction)


class CloneConfirmationView(View):
    """Ephemeral DM view with Confirm and Decline buttons for clone carry-over.

    Attributes:
        schedule_id: ParticipantActionSchedule row to delete on confirm
        game_id: Game session UUID
        participant_id: GameParticipant UUID for the drop handler
        publisher: Bot event publisher
    """

    def __init__(
        self,
        schedule_id: str,
        game_id: str,
        participant_id: str,
        publisher: BotEventPublisher,
    ) -> None:
        """Initialise the view with confirm and decline button stubs.

        Args:
            schedule_id: ParticipantActionSchedule UUID to remove on confirm
            game_id: Game session UUID
            participant_id: GameParticipant UUID
            publisher: Bot event publisher for GAME_UPDATED notifications
        """
        super().__init__(timeout=None)
        self.schedule_id = schedule_id
        self.game_id = game_id
        self.participant_id = participant_id
        self.publisher = publisher

        self.confirm_button = _ConfirmButton(
            style=discord.ButtonStyle.success,
            label="Confirm",
            custom_id=f"clone_confirm_{schedule_id}",
        )

        self.decline_button = _DeclineButton(
            style=discord.ButtonStyle.danger,
            label="Decline",
            custom_id=f"clone_decline_{participant_id}",
        )

        self.add_item(self.confirm_button)
        self.add_item(self.decline_button)

    async def _confirm_callback(self, interaction: discord.Interaction) -> None:
        """Handle confirm button — clears the pending drop schedule."""
        await interaction.response.defer(ephemeral=True)

        async with get_db_session() as db:
            result = await db.execute(
                select(ParticipantActionSchedule).where(
                    ParticipantActionSchedule.id == self.schedule_id
                )
            )
            schedule = result.scalar_one_or_none()

            if schedule is not None:
                await db.delete(schedule)
                await db.execute(
                    text("SELECT pg_notify('participant_action_schedule_changed', '')")
                )
                await db.commit()
                logger.info(
                    "Confirmed clone spot: cleared schedule %s for participant %s",
                    self.schedule_id,
                    self.participant_id,
                )

        await interaction.followup.send("✅ You've confirmed your spot!", ephemeral=True)

    async def _decline_callback(self, interaction: discord.Interaction) -> None:
        """Handle decline button — immediately triggers the drop handler."""
        await interaction.response.defer(ephemeral=True)

        await handle_participant_drop_due(
            data={"game_id": self.game_id, "participant_id": self.participant_id},
            bot=interaction.client,
            publisher=self.publisher,
        )
        logger.info(
            "Declined clone spot: dropped participant %s from game %s",
            self.participant_id,
            self.game_id,
        )

        await interaction.followup.send("❌ You've declined your spot.", ephemeral=True)

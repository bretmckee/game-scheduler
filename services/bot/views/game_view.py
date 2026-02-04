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


"""Discord UI view for game session interactions.

This module provides the persistent button view for game sessions,
allowing players to join and leave games via Discord buttons.
"""

import discord
from discord.ui import Button, View

from shared.models.signup_method import SignupMethod


class GameView(View):
    """Persistent view with Join and Leave buttons for game sessions.

    This view persists across bot restarts by using timeout=None and
    custom_id patterns that encode the game session ID.

    Attributes:
        game_id: UUID of the game session
        is_full: Whether the game has reached max players
        is_started: Whether the game has started (IN_PROGRESS or COMPLETED)
        signup_method: Signup method controlling button behavior
    """

    def __init__(
        self,
        game_id: str,
        is_full: bool = False,
        is_started: bool = False,
        signup_method: str = SignupMethod.SELF_SIGNUP.value,
    ) -> None:
        """Initialize the game view with buttons.

        Args:
            game_id: Game session UUID
            is_full: Whether game is at capacity
            is_started: Whether game has started
            signup_method: Signup method (SELF_SIGNUP or HOST_SELECTED)
        """
        super().__init__(timeout=None)
        self.game_id = game_id
        self.is_full = is_full
        self.is_started = is_started
        self.signup_method = signup_method

        self.join_button: Button[GameView] = Button(
            style=discord.ButtonStyle.success,
            label="Join Game",
            custom_id=f"join_game_{game_id}",
            disabled=is_started or (signup_method == SignupMethod.HOST_SELECTED.value),
        )
        # Type ignore: discord.py's callback assignment pattern not fully typed
        self.join_button.callback = self._join_button_callback  # type: ignore[method-assign]

        self.leave_button: Button[GameView] = Button(
            style=discord.ButtonStyle.danger,
            label="Leave Game",
            custom_id=f"leave_game_{game_id}",
            disabled=is_started,
        )
        # Type ignore: discord.py's callback assignment pattern not fully typed
        self.leave_button.callback = self._leave_button_callback  # type: ignore[method-assign]

        self.add_item(self.join_button)
        self.add_item(self.leave_button)

    async def _join_button_callback(self, interaction: discord.Interaction) -> None:
        """Handle join button click.

        This is a placeholder that will be replaced by the actual handler
        when the view is registered with the bot.
        """
        await interaction.response.defer()

    async def _leave_button_callback(self, interaction: discord.Interaction) -> None:
        """Handle leave button click.

        This is a placeholder that will be replaced by the actual handler
        when the view is registered with the bot.
        """
        await interaction.response.defer()

    def update_button_states(
        self, is_full: bool, is_started: bool, signup_method: str | None = None
    ) -> None:
        """Update button enabled/disabled states.

        Args:
            is_full: Whether game is at capacity (unused since waitlists are supported)
            is_started: Whether game has started
            signup_method: Optional new signup method to apply
        """
        self.is_full = is_full
        self.is_started = is_started
        if signup_method is not None:
            self.signup_method = signup_method
        self.join_button.disabled = is_started or (
            self.signup_method == SignupMethod.HOST_SELECTED.value
        )
        self.leave_button.disabled = is_started

    @classmethod
    def from_game_data(
        cls,
        game_id: str,
        current_players: int,
        max_players: int,
        status: str,
        signup_method: str = SignupMethod.SELF_SIGNUP.value,
    ) -> "GameView":
        """Create a GameView from game session data.

        Args:
            game_id: Game session UUID
            current_players: Current participant count
            max_players: Maximum allowed participants
            status: Game status (SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED)
            signup_method: Signup method (SELF_SIGNUP or HOST_SELECTED)

        Returns:
            Configured GameView instance
        """
        is_full = current_players >= max_players
        is_started = status in ("IN_PROGRESS", "COMPLETED", "CANCELLED")
        return cls(game_id, is_full, is_started, signup_method)

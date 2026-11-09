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


"""Tests for the recurrence_confirmation notification handler."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.schemas.events import NotificationDueEvent


@pytest.mark.asyncio
async def test_recurrence_confirmation_treats_naive_scheduled_at_as_utc(
    event_handlers, mock_bot, sample_game, non_utc_local_timezone
):
    """The host DM shows the UTC instant of the stored naive next-session time."""
    sample_game.scheduled_at = datetime(2026, 8, 1, 18, 0)
    sample_game.host = MagicMock()
    sample_game.host.discord_id = "555000000000000009"
    mock_user = MagicMock()
    mock_user.send = AsyncMock()
    mock_bot.get_user.return_value = mock_user
    event = NotificationDueEvent(
        game_id=sample_game.id, notification_type="recurrence_confirmation"
    )

    with (
        patch("services.bot.events.handlers.get_db_session") as mock_db_session,
        patch.object(
            event_handlers,
            "_get_game_with_participants",
            new_callable=AsyncMock,
            return_value=sample_game,
        ),
        patch("services.bot.events.handlers.RecurrenceConfirmationView") as mock_view_cls,
        patch("services.bot.events.handlers.DMFormats") as mock_fmt,
    ):
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_fmt.recurrence_confirmation.return_value = "Recurrence DM text"

        await event_handlers._handle_recurrence_confirmation(event)

    mock_db_session.assert_called_once_with()
    mock_view_cls.assert_called_once_with(str(sample_game.id))
    mock_fmt.recurrence_confirmation.assert_called_once_with(sample_game.title, 1785607200)
    mock_user.send.assert_awaited_once_with("Recurrence DM text", view=mock_view_cls.return_value)

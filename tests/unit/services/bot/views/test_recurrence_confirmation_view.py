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


"""Unit tests for RecurrenceConfirmationView button interactions."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from services.bot.views.recurrence_confirmation_view import RecurrenceConfirmationView
from shared.models import GameStatus


@pytest.fixture
def game_id():
    return "a1b2c3d4-0000-0000-0000-000000000001"


@pytest.fixture
def mock_interaction():
    interaction = MagicMock(spec=discord.Interaction)
    interaction.response = AsyncMock()
    interaction.response.defer = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.followup.send = AsyncMock()
    return interaction


def _make_db_ctx(mock_session):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="RecurrenceConfirmationView.confirm not yet implemented")
async def test_confirm_sets_post_at_to_now(game_id, mock_interaction):
    """Confirm callback sets game.post_at to approximately now."""
    game = MagicMock()
    game.post_at = None

    mock_session = AsyncMock()
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=game)
    mock_session.execute = AsyncMock(return_value=result)
    mock_session.commit = AsyncMock()

    before = datetime.now(UTC)

    with patch(
        "services.bot.views.recurrence_confirmation_view.get_db_session",
        return_value=_make_db_ctx(mock_session),
        create=True,
    ):
        view = RecurrenceConfirmationView(game_id=game_id)
        await view.confirm(mock_interaction)

    after = datetime.now(UTC)
    assert game.post_at is not None
    assert before <= game.post_at <= after


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="RecurrenceConfirmationView.confirm not yet implemented")
async def test_confirm_sends_pg_notify(game_id, mock_interaction):
    """Confirm callback sends NOTIFY game_announcement_changed after updating post_at."""
    game = MagicMock()
    game.post_at = None

    notify_executed = []

    async def fake_execute(stmt, *args, **kwargs):
        compiled = str(stmt)
        if "game_announcement_changed" in compiled:
            notify_executed.append(compiled)
        result = MagicMock()
        result.scalar_one = MagicMock(return_value=game)
        return result

    mock_session = AsyncMock()
    mock_session.execute = fake_execute
    mock_session.commit = AsyncMock()

    with patch(
        "services.bot.views.recurrence_confirmation_view.get_db_session",
        return_value=_make_db_ctx(mock_session),
        create=True,
    ):
        view = RecurrenceConfirmationView(game_id=game_id)
        await view.confirm(mock_interaction)

    assert notify_executed, "pg_notify for game_announcement_changed was not called"


@pytest.mark.asyncio
@pytest.mark.xfail(strict=True, reason="RecurrenceConfirmationView.decline not yet implemented")
async def test_decline_cancels_game(game_id, mock_interaction):
    """Decline callback sets game.status to CANCELLED."""
    game = MagicMock()
    game.status = GameStatus.SCHEDULED.value

    mock_session = AsyncMock()
    result = MagicMock()
    result.scalar_one = MagicMock(return_value=game)
    mock_session.execute = AsyncMock(return_value=result)
    mock_session.commit = AsyncMock()

    with patch(
        "services.bot.views.recurrence_confirmation_view.get_db_session",
        return_value=_make_db_ctx(mock_session),
        create=True,
    ):
        view = RecurrenceConfirmationView(game_id=game_id)
        await view.decline(mock_interaction)

    assert game.status == GameStatus.CANCELLED.value

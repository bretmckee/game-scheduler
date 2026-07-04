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


"""Tests for cancel_game shared service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models.bot_action_queue import BotActionQueue
from shared.services.game_cancellation import cancel_game


def _make_game(
    game_id: str = "game-uuid-1",
    thumbnail_id: str | None = "thumb-id",
    banner_image_id: str | None = "banner-id",
    message_id: str | None = "msg-id-123",
    channel_discord_id: str | None = "111222333444555666",
) -> MagicMock:
    game = MagicMock()
    game.id = game_id
    game.thumbnail_id = thumbnail_id
    game.banner_image_id = banner_image_id
    game.message_id = message_id
    game.channel = MagicMock()
    game.channel.channel_id = channel_discord_id
    return game


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.delete = AsyncMock()
    db.add = MagicMock()
    return db


class TestCancelGame:
    """Tests for the cancel_game shared service function."""

    @pytest.mark.asyncio
    async def test_releases_thumbnail_image(self, mock_db: MagicMock) -> None:
        """Calls release_image for the thumbnail before deleting the game row."""
        game = _make_game(thumbnail_id="thumb-123", banner_image_id=None)
        with patch(
            "shared.services.game_cancellation.release_image",
            new_callable=AsyncMock,
        ) as mock_release:
            await cancel_game(mock_db, game)
        mock_release.assert_any_call(mock_db, "thumb-123")

    @pytest.mark.asyncio
    async def test_releases_banner_image(self, mock_db: MagicMock) -> None:
        """Calls release_image for the banner image before deleting the game row."""
        game = _make_game(thumbnail_id=None, banner_image_id="banner-456")
        with patch(
            "shared.services.game_cancellation.release_image",
            new_callable=AsyncMock,
        ) as mock_release:
            await cancel_game(mock_db, game)
        mock_release.assert_any_call(mock_db, "banner-456")

    @pytest.mark.asyncio
    async def test_deletes_game_row(self, mock_db: MagicMock) -> None:
        """Calls db.delete(game) to remove the game row."""
        game = _make_game(thumbnail_id=None, banner_image_id=None)
        with patch("shared.services.game_cancellation.release_image", new_callable=AsyncMock):
            await cancel_game(mock_db, game)
        mock_db.delete.assert_called_once_with(game)

    @pytest.mark.asyncio
    async def test_enqueues_bot_action_queue_row_by_default(self, mock_db: MagicMock) -> None:
        """Adds a BotActionQueue row with action_type='game_cancelled' by default."""
        game = _make_game(message_id="msg-123", channel_discord_id="111222333444555666")
        with patch("shared.services.game_cancellation.release_image", new_callable=AsyncMock):
            await cancel_game(mock_db, game)
        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 1
        row = bot_rows[0]
        assert row.action_type == "game_cancelled"
        assert row.channel_id == "111222333444555666"
        assert row.message_id == "msg-123"
        assert row.game_id == "game-uuid-1"

    @pytest.mark.asyncio
    async def test_does_not_enqueue_when_enqueue_cancellation_false(
        self, mock_db: MagicMock
    ) -> None:
        """Does not add any BotActionQueue row when enqueue_cancellation=False."""
        game = _make_game()
        with patch("shared.services.game_cancellation.release_image", new_callable=AsyncMock):
            await cancel_game(mock_db, game, enqueue_cancellation=False)
        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 0

    @pytest.mark.asyncio
    async def test_captures_message_id_before_deletion(self, mock_db: MagicMock) -> None:
        """Captures message_id and channel_id from game object before db.delete is called."""
        game = _make_game(message_id="stored-msg-id", channel_discord_id="111222333444555666")
        captured: list[str] = []

        async def fake_delete(obj: MagicMock) -> None:
            obj.message_id = "DELETED"
            obj.channel = None

        mock_db.delete = AsyncMock(side_effect=fake_delete)

        with patch("shared.services.game_cancellation.release_image", new_callable=AsyncMock):
            await cancel_game(mock_db, game, enqueue_cancellation=True)

        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 1
        captured.append(bot_rows[0].message_id or "")
        assert "stored-msg-id" in captured

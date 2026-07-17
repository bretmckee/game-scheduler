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


"""Tests for leave_game_and_notify shared service."""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.models.bot_action_queue import BotActionQueue
from shared.models.participant import ParticipantType
from shared.models.signup_method import SignupMethod
from shared.services.leave_game import leave_game_and_notify


def _make_participant(
    discord_id: str,
    position_type: int = ParticipantType.SELF_ADDED,
    position: int = 0,
    joined_at: datetime.datetime | None = None,
) -> MagicMock:
    participant = MagicMock()
    participant.user = MagicMock()
    participant.user.discord_id = discord_id
    participant.position_type = position_type
    participant.position = position
    participant.joined_at = joined_at or datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    return participant


def _make_game(
    max_players: int = 1,
    message_id: str | None = "msg-id-123",
    title: str = "Test Game",
    signup_method: str = SignupMethod.SELF_SIGNUP,
    host_discord_id: str | None = "host-discord-id",
) -> MagicMock:
    game = MagicMock()
    game.id = "game-uuid-1"
    game.title = title
    game.max_players = max_players
    game.signup_method = signup_method
    game.scheduled_at = datetime.datetime(2026, 8, 1, 18, 0, tzinfo=datetime.UTC)
    game.message_id = message_id
    game.guild = MagicMock()
    game.guild.guild_id = "111222333444555666"
    game.channel = MagicMock()
    game.channel.channel_id = "777888999000111222"
    if host_discord_id is None:
        game.host = None
    else:
        game.host = MagicMock()
        game.host.discord_id = host_discord_id
    return game


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    return db


def _bot_rows(mock_db: MagicMock) -> list[BotActionQueue]:
    added = [c.args[0] for c in mock_db.add.call_args_list]
    return [r for r in added if isinstance(r, BotActionQueue)]


class TestLeaveGameAndNotify:
    """Tests for the leave_game_and_notify shared service function."""

    @pytest.mark.asyncio
    async def test_leave_deletes_the_participant(self, mock_db: MagicMock) -> None:
        """leave_game_and_notify deletes the passed participant."""
        leaver = _make_participant("leaving-user")
        game = _make_game(max_players=1)
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        mock_db.delete.assert_called_once_with(leaver)

    @pytest.mark.asyncio
    async def test_confirmed_leave_promotes_waitlisted_participant(
        self, mock_db: MagicMock
    ) -> None:
        """A confirmed HOST_ADDED leaver frees a slot for a waitlisted HOST_ADDED user."""
        leaver = _make_participant("leaving-user", position_type=ParticipantType.HOST_ADDED)
        waitlisted = _make_participant(
            "waitlisted-user",
            position_type=ParticipantType.HOST_ADDED,
            joined_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )
        game = _make_game(max_players=1, signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST)
        game.participants = [leaver, waitlisted]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = [waitlisted]

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        promotion_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "waitlist_promotion"
        ]
        assert len(promotion_rows) == 1
        assert promotion_rows[0].discord_id == "waitlisted-user"

    @pytest.mark.asyncio
    async def test_host_added_leave_enqueues_dropout_dm_to_host(self, mock_db: MagicMock) -> None:
        """A HOST_ADDED leaver enqueues a host_added_dropout DM to the host."""
        leaver = _make_participant("leaving-user", position_type=ParticipantType.HOST_ADDED)
        game = _make_game(max_players=5, host_discord_id="host-discord-id")
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        dropout_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "host_added_dropout"
        ]
        assert len(dropout_rows) == 1
        assert dropout_rows[0].discord_id == "host-discord-id"

    @pytest.mark.asyncio
    async def test_self_added_leave_with_empty_waitlist_enqueues_nothing(
        self, mock_db: MagicMock
    ) -> None:
        """A SELF_ADDED leaver with no waitlist and no promotion enqueues nothing."""
        leaver = _make_participant("leaving-user", position_type=ParticipantType.SELF_ADDED)
        game = _make_game(max_players=5, host_discord_id="host-discord-id")
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_host_dropout_dm_when_host_missing(self, mock_db: MagicMock) -> None:
        """A HOST_ADDED leaver enqueues no dropout DM when game.host is None."""
        leaver = _make_participant("leaving-user", position_type=ParticipantType.HOST_ADDED)
        game = _make_game(max_players=5, host_discord_id=None)
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        dropout_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "host_added_dropout"
        ]
        assert len(dropout_rows) == 0

    @pytest.mark.asyncio
    async def test_repositioned_self_added_leave_does_not_enqueue_dropout_dm(
        self, mock_db: MagicMock
    ) -> None:
        """A repositioned (explicit small position) SELF_ADDED leaver triggers no dropout DM."""
        leaver = _make_participant(
            "leaving-user", position_type=ParticipantType.SELF_ADDED, position=1
        )
        game = _make_game(max_players=5, host_discord_id="host-discord-id")
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        dropout_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "host_added_dropout"
        ]
        assert len(dropout_rows) == 0

    @pytest.mark.asyncio
    async def test_converted_role_matched_leave_does_not_enqueue_dropout_dm(
        self, mock_db: MagicMock
    ) -> None:
        """A ROLE_MATCHED participant converted to SELF_ADDED enqueues no dropout DM."""
        leaver = _make_participant(
            "leaving-user", position_type=ParticipantType.SELF_ADDED, position=1
        )
        game = _make_game(
            max_players=5, host_discord_id="host-discord-id", signup_method=SignupMethod.ROLE_BASED
        )
        game.participants = [leaver]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = []

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        dropout_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "host_added_dropout"
        ]
        assert len(dropout_rows) == 0

    @pytest.mark.asyncio
    async def test_leave_promotes_only_one_of_two_waitlisted_users(
        self, mock_db: MagicMock
    ) -> None:
        """Freeing 1 slot promotes only the next-in-line waitlisted user, not both."""
        leaver = _make_participant("leaving-user", position_type=ParticipantType.HOST_ADDED)
        waitlisted_1 = _make_participant(
            "waitlisted-user-1",
            position_type=ParticipantType.HOST_ADDED,
            joined_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC),
        )
        waitlisted_2 = _make_participant(
            "waitlisted-user-2",
            position_type=ParticipantType.HOST_ADDED,
            joined_at=datetime.datetime(2026, 1, 3, tzinfo=datetime.UTC),
        )
        game = _make_game(max_players=1, signup_method=SignupMethod.HOST_SELECTED_WITH_WAITLIST)
        game.participants = [leaver, waitlisted_1, waitlisted_2]

        async def refresh_side_effect(
            g: MagicMock, attribute_names: list[str] | None = None
        ) -> None:
            g.participants = [waitlisted_1, waitlisted_2]

        mock_db.refresh = AsyncMock(side_effect=refresh_side_effect)

        await leave_game_and_notify(mock_db, game, leaver)

        promotion_rows = [
            r for r in _bot_rows(mock_db) if r.payload["notification_type"] == "waitlist_promotion"
        ]
        assert len(promotion_rows) == 1
        assert promotion_rows[0].discord_id == "waitlisted-user-1"

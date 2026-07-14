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


"""Tests for detect_and_notify_transitions shared service."""

import datetime
from unittest.mock import MagicMock

import pytest

from shared.models.bot_action_queue import BotActionQueue
from shared.models.participant import ParticipantType
from shared.services.waitlist_transitions import detect_and_notify_transitions
from shared.utils.participant_sorting import partition_participants


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
) -> MagicMock:
    game = MagicMock()
    game.id = "game-uuid-1"
    game.title = title
    game.max_players = max_players
    game.signup_method = "self_signup"
    game.scheduled_at = datetime.datetime(2026, 8, 1, 18, 0, tzinfo=datetime.UTC)
    game.message_id = message_id
    game.guild = MagicMock()
    game.guild.guild_id = "111222333444555666"
    game.channel = MagicMock()
    game.channel.channel_id = "777888999000111222"
    return game


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    return db


class TestDetectAndNotifyTransitions:
    """Tests for the detect_and_notify_transitions shared service function."""

    @pytest.mark.asyncio
    async def test_promotion_enqueues_send_dm_and_returns_promoted_id(
        self, mock_db: MagicMock
    ) -> None:
        """A participant moving overflow -> confirmed triggers a promotion send_dm row."""
        confirmed = _make_participant("host-user")
        overflow = _make_participant(
            "waitlisted-user", joined_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)
        )
        old_partitioned = partition_participants([confirmed, overflow], max_players=1)

        game = _make_game(max_players=1)
        game.participants = [overflow]  # confirmed user left, freeing the slot

        promoted, demoted = await detect_and_notify_transitions(mock_db, game, old_partitioned)

        assert promoted == {"waitlisted-user"}
        assert demoted == set()

        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 1
        row = bot_rows[0]
        assert row.action_type == "send_dm"
        assert row.discord_id == "waitlisted-user"
        assert row.game_id == "game-uuid-1"
        assert row.payload["notification_type"] == "waitlist_promotion"

    @pytest.mark.asyncio
    async def test_demotion_enqueues_send_dm_and_returns_demoted_id(
        self, mock_db: MagicMock
    ) -> None:
        """A participant moving confirmed -> overflow triggers a demotion send_dm row."""
        confirmed = _make_participant("original-user")
        old_partitioned = partition_participants([confirmed], max_players=1)

        host_added = _make_participant("host-added-user", position_type=ParticipantType.HOST_ADDED)
        game = _make_game(max_players=1)
        game.participants = [host_added, confirmed]

        promoted, demoted = await detect_and_notify_transitions(mock_db, game, old_partitioned)

        assert promoted == set()
        assert demoted == {"original-user"}

        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 1
        row = bot_rows[0]
        assert row.action_type == "send_dm"
        assert row.discord_id == "original-user"
        assert row.payload["notification_type"] == "waitlist_demotion"

    @pytest.mark.asyncio
    async def test_no_transitions_enqueues_nothing(self, mock_db: MagicMock) -> None:
        """Identical old/new partitioned state enqueues no notifications."""
        confirmed = _make_participant("stable-user")
        old_partitioned = partition_participants([confirmed], max_players=1)

        game = _make_game(max_players=1)
        game.participants = [confirmed]

        promoted, demoted = await detect_and_notify_transitions(mock_db, game, old_partitioned)

        assert promoted == set()
        assert demoted == set()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_promotion_without_jump_url_when_message_id_missing(
        self, mock_db: MagicMock
    ) -> None:
        """No jump URL is included in the promotion DM when game.message_id is None."""
        confirmed = _make_participant("host-user")
        overflow = _make_participant(
            "waitlisted-user", joined_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)
        )
        old_partitioned = partition_participants([confirmed, overflow], max_players=1)

        game = _make_game(max_players=1, message_id=None)
        game.participants = [overflow]

        await detect_and_notify_transitions(mock_db, game, old_partitioned)

        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 1
        assert "discord.com/channels" not in bot_rows[0].payload["message"]

    @pytest.mark.asyncio
    async def test_multiple_simultaneous_promotions(self, mock_db: MagicMock) -> None:
        """Increasing capacity by 2 promotes both waitlisted users in one call."""
        confirmed = _make_participant("host-user")
        overflow_1 = _make_participant(
            "waitlisted-user-1", joined_at=datetime.datetime(2026, 1, 2, tzinfo=datetime.UTC)
        )
        overflow_2 = _make_participant(
            "waitlisted-user-2", joined_at=datetime.datetime(2026, 1, 3, tzinfo=datetime.UTC)
        )
        old_partitioned = partition_participants([confirmed, overflow_1, overflow_2], max_players=1)

        game = _make_game(max_players=3)
        game.participants = [confirmed, overflow_1, overflow_2]

        promoted, demoted = await detect_and_notify_transitions(mock_db, game, old_partitioned)

        assert promoted == {"waitlisted-user-1", "waitlisted-user-2"}
        assert demoted == set()

        added = [c.args[0] for c in mock_db.add.call_args_list]
        bot_rows = [r for r in added if isinstance(r, BotActionQueue)]
        assert len(bot_rows) == 2
        assert {r.discord_id for r in bot_rows} == {"waitlisted-user-1", "waitlisted-user-2"}
        assert all(r.payload["notification_type"] == "waitlist_promotion" for r in bot_rows)

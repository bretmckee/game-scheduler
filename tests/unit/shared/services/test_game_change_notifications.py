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


"""Tests for the game change-notification shared service."""

import datetime
from unittest.mock import MagicMock

import pytest

from shared.message_formats import DMFormats
from shared.models.bot_action_queue import BotActionQueue
from shared.services.game_change_notifications import (
    GameNotifySnapshot,
    capture_notify_snapshot,
    notify_participants_of_changes,
)

OLD_TIME = datetime.datetime(2026, 8, 1, 18, 0)
OLD_TIME_UNIX = 1785607200
NEW_TIME = datetime.datetime(2026, 8, 2, 19, 30)
NEW_TIME_UNIX = 1785699000

JUMP_URL = "https://discord.com/channels/111222333444555666/777888999000111222/msg-id-123"


def _make_participant(discord_id: str | None, display_name: str | None = None) -> MagicMock:
    participant = MagicMock()
    if discord_id is None:
        participant.user = None
    else:
        participant.user = MagicMock()
        participant.user.discord_id = discord_id
    participant.display_name = display_name
    return participant


def _make_game(
    participants: list[MagicMock],
    *,
    scheduled_at: datetime.datetime = OLD_TIME,
    expected_duration_minutes: int | None = 90,
    where: str | None = "Discord voice",
    signup_instructions: str | None = "Bring a character",
    title: str = "Test Game",
) -> MagicMock:
    game = MagicMock()
    game.id = "game-uuid-1"
    game.title = title
    game.max_players = 2
    game.scheduled_at = scheduled_at
    game.expected_duration_minutes = expected_duration_minutes
    game.where = where
    game.signup_instructions = signup_instructions
    game.message_id = "msg-id-123"
    game.guild = MagicMock()
    game.guild.guild_id = "111222333444555666"
    game.channel = MagicMock()
    game.channel.channel_id = "777888999000111222"
    game.participants = participants
    return game


def _old_snapshot(**overrides: object) -> GameNotifySnapshot:
    values: dict[str, object] = {
        "scheduled_at": OLD_TIME,
        "expected_duration_minutes": 90,
        "where": "Discord voice",
        "signup_instructions": "Bring a character",
    }
    values.update(overrides)
    return GameNotifySnapshot(**values)  # type: ignore[arg-type]


def _queued_rows(mock_db: MagicMock) -> list[BotActionQueue]:
    added = [c.args[0] for c in mock_db.add.call_args_list]
    return [r for r in added if isinstance(r, BotActionQueue)]


@pytest.fixture
def mock_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    return db


class TestCaptureNotifySnapshot:
    """Tests for capture_notify_snapshot."""

    def test_returns_current_notify_field_values(self) -> None:
        """The snapshot holds the game's four notify-field values as they are now."""
        game = _make_game(
            [],
            scheduled_at=OLD_TIME,
            expected_duration_minutes=45,
            where="Table 3",
            signup_instructions="DM the host",
        )

        snapshot = capture_notify_snapshot(game)

        assert snapshot == GameNotifySnapshot(
            scheduled_at=OLD_TIME,
            expected_duration_minutes=45,
            where="Table 3",
            signup_instructions="DM the host",
        )


class TestNotifyParticipantsOfChanges:
    """Tests for notify_participants_of_changes."""

    @pytest.mark.asyncio
    async def test_time_change_dms_confirmed_and_waitlisted(self, mock_db: MagicMock) -> None:
        """A time change enqueues one game_updated send_dm per participant, waitlist included."""
        participants = [
            _make_participant("confirmed-1"),
            _make_participant("confirmed-2"),
            _make_participant("waitlisted-1"),
        ]
        game = _make_game(participants, scheduled_at=NEW_TIME)

        notified = await notify_participants_of_changes(mock_db, game, _old_snapshot())

        assert notified == {"confirmed-1", "confirmed-2", "waitlisted-1"}
        rows = _queued_rows(mock_db)
        assert mock_db.add.call_count == 3
        assert sorted(r.discord_id for r in rows) == ["confirmed-1", "confirmed-2", "waitlisted-1"]
        expected_message = (
            "📝 The host updated **Test Game**:\n"
            f"• **Time**: <t:{OLD_TIME_UNIX}:F> → <t:{NEW_TIME_UNIX}:F>\n"
            f"[View game in Discord]({JUMP_URL})"
        )
        for row in rows:
            assert row.action_type == "send_dm"
            assert row.game_id == "game-uuid-1"
            assert row.payload == {
                "notification_type": "game_updated",
                "game_title": "Test Game",
                "game_time_unix": NEW_TIME_UNIX,
                "message": expected_message,
            }

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("field", "old_value", "new_value", "expected_line"),
        [
            ("expected_duration_minutes", 90, 120, "• **Duration**: 90 min → 120 min"),
            ("expected_duration_minutes", None, 60, "• **Duration**: not set → 60 min"),
            ("where", "Discord voice", "Table 3", "• **Location**: Discord voice → Table 3"),
            ("where", None, "Table 3", "• **Location**: (none) → Table 3"),
            (
                "signup_instructions",
                "Bring a character",
                "",
                "• **Signup Instructions**: Bring a character → (none)",
            ),
        ],
    )
    async def test_single_field_change_lists_only_that_field(
        self,
        mock_db: MagicMock,
        field: str,
        old_value: object,
        new_value: object,
        expected_line: str,
    ) -> None:
        """Changing one non-time field produces a DM listing exactly that field."""
        game = _make_game([_make_participant("player-1")], **{field: new_value})  # type: ignore[arg-type]

        notified = await notify_participants_of_changes(
            mock_db, game, _old_snapshot(**{field: old_value})
        )

        assert notified == {"player-1"}
        rows = _queued_rows(mock_db)
        assert len(rows) == 1
        assert rows[0].discord_id == "player-1"
        assert rows[0].payload["message"] == (
            f"📝 The host updated **Test Game**:\n{expected_line}\n"
            f"[View game in Discord]({JUMP_URL})"
        )

    @pytest.mark.asyncio
    async def test_multiple_changes_produce_one_dm_listing_all(self, mock_db: MagicMock) -> None:
        """Two fields changed in one edit still yield exactly one DM per participant."""
        game = _make_game(
            [_make_participant("player-1"), _make_participant("player-2")],
            scheduled_at=NEW_TIME,
            where="Table 3",
        )

        notified = await notify_participants_of_changes(mock_db, game, _old_snapshot())

        assert notified == {"player-1", "player-2"}
        rows = _queued_rows(mock_db)
        assert sorted(r.discord_id for r in rows) == ["player-1", "player-2"]
        expected_message = (
            "📝 The host updated **Test Game**:\n"
            f"• **Time**: <t:{OLD_TIME_UNIX}:F> → <t:{NEW_TIME_UNIX}:F>\n"
            "• **Location**: Discord voice → Table 3\n"
            f"[View game in Discord]({JUMP_URL})"
        )
        assert [r.payload["message"] for r in rows] == [expected_message, expected_message]

    @pytest.mark.asyncio
    async def test_no_change_enqueues_nothing(self, mock_db: MagicMock) -> None:
        """A save that leaves every notify field unchanged sends no DM."""
        game = _make_game([_make_participant("player-1")])

        notified = await notify_participants_of_changes(mock_db, game, _old_snapshot())

        assert notified == set()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_placeholder_participant_is_skipped(self, mock_db: MagicMock) -> None:
        """Placeholder participants have no Discord user and are not DMed."""
        game = _make_game(
            [_make_participant("player-1"), _make_participant(None, display_name="Bob")],
            scheduled_at=NEW_TIME,
        )

        notified = await notify_participants_of_changes(mock_db, game, _old_snapshot())

        assert notified == {"player-1"}
        rows = _queued_rows(mock_db)
        assert [r.discord_id for r in rows] == ["player-1"]

    @pytest.mark.asyncio
    async def test_excluded_field_change_enqueues_nothing(self, mock_db: MagicMock) -> None:
        """Changing a field outside the snapshot (title) sends no DM."""
        game = _make_game([_make_participant("player-1")], title="Renamed Game")

        notified = await notify_participants_of_changes(mock_db, game, _old_snapshot())

        assert notified == set()
        mock_db.add.assert_not_called()


class TestGameUpdatedFormat:
    """Tests for DMFormats.game_updated."""

    def test_includes_changes_and_jump_url(self) -> None:
        """Each change renders as a bullet, followed by the game link."""
        message = DMFormats.game_updated(
            "Test Game",
            [
                ("Time", f"<t:{OLD_TIME_UNIX}:F>", f"<t:{NEW_TIME_UNIX}:F>"),
                ("Duration", "90 min", "120 min"),
            ],
            jump_url=JUMP_URL,
        )

        assert message == (
            "📝 The host updated **Test Game**:\n"
            f"• **Time**: <t:{OLD_TIME_UNIX}:F> → <t:{NEW_TIME_UNIX}:F>\n"
            "• **Duration**: 90 min → 120 min\n"
            f"[View game in Discord]({JUMP_URL})"
        )

    def test_omits_link_without_jump_url(self) -> None:
        """No link line is added when the jump URL is unavailable."""
        message = DMFormats.game_updated("Test Game", [("Location", "(none)", "Table 3")])

        assert message == "📝 The host updated **Test Game**:\n• **Location**: (none) → Table 3"

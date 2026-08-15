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


"""Unit tests for EventHandlers join notification methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from shared.models.signup_method import SignupMethod
from shared.models.user import User
from shared.schemas.events import NotificationDueEvent


@pytest.mark.asyncio
async def test_handle_join_notification_with_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM with signup instructions when present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = "Click the link to create your character: https://example.com"
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert sample_game.signup_instructions in sent_message

                # assert-not-weak: get_db_session() has no parameters
                mock_db_session.assert_called_once_with()
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_join_notification_without_signup_instructions(event_handlers, sample_game):
    """Test join notification sends DM without signup instructions when not present."""
    participant_user = User(id=str(uuid4()), discord_id="participant123")
    sample_game.signup_instructions = None
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.max_players = 5

    participant = MagicMock()
    participant.id = str(uuid4())
    participant.user_id = participant_user.id
    participant.user = participant_user
    participant.is_waitlisted = False

    sample_game.participants = [participant]

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
                mock_send_dm.return_value = True

                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant.id,
                }
                await event_handlers._handle_notification_due(data)

                assert mock_send_dm.await_count == 1
                sent_message = mock_send_dm.call_args.args[1]
                assert "joined" in sent_message.lower()
                assert sample_game.title in sent_message
                assert "signup instructions" not in sent_message.lower()

                # assert-not-weak: get_db_session() has no parameters
                mock_db_session.assert_called_once_with()
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_join_notification_missing_participant_id(event_handlers, sample_game):
    """Test join notification handles missing participant_id gracefully."""
    data = {
        "game_id": str(uuid4()),
        "notification_type": "join_notification",
        "participant_id": None,
    }

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            await event_handlers._handle_notification_due(data)

            mock_get_game.assert_awaited_once_with(mock_db, data["game_id"])
            # assert-not-weak: get_db_session() has no parameters
            mock_db_session.assert_called_once_with()


@pytest.mark.asyncio
async def test_handle_join_notification_user_not_found(event_handlers, sample_game):
    """Test join notification handles missing participant gracefully."""
    participant_id = str(uuid4())

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            with patch("services.bot.events.handlers.logger") as mock_logger:
                data = {
                    "game_id": sample_game.id,
                    "notification_type": "join_notification",
                    "participant_id": participant_id,
                }
                await event_handlers._handle_notification_due(data)
                mock_logger.info.assert_called()
                assert any(
                    "no longer active" in str(call) for call in mock_logger.info.call_args_list
                )

                # assert-not-weak: get_db_session() has no parameters
                mock_db_session.assert_called_once_with()
                mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


class TestHandleJoinNotificationHelpers:
    """Test helper methods extracted from _handle_join_notification."""

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_success(self, event_handlers, sample_game):
        """Test successful fetch of game and participant data."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = MagicMock()

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

            assert game == sample_game
            assert part == participant
            mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_game_not_found(self, event_handlers):
        """Test fetch when game doesn't exist."""
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = None

            event = NotificationDueEvent(
                game_id=str(uuid4()),
                notification_type="join_notification",
                participant_id=str(uuid4()),
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.error.assert_called_once_with("Game not found: %s", event.game_id)

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_not_found(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant doesn't exist."""
        participant_id = str(uuid4())
        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=None)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.info.assert_called_once_with(
                    "Participant %s no longer active for game %s",
                    event.participant_id,
                    event.game_id,
                )

    @pytest.mark.asyncio
    async def test_fetch_join_notification_data_participant_without_user(
        self, event_handlers, sample_game
    ):
        """Test fetch when participant exists but has no user."""
        participant_id = str(uuid4())
        participant = MagicMock()
        participant.id = participant_id
        participant.user = None

        mock_db = MagicMock()

        with patch.object(
            event_handlers, "_get_game_with_participants", new_callable=AsyncMock
        ) as mock_get_game:
            mock_get_game.return_value = sample_game

            async def mock_execute(query):
                result = MagicMock()
                result.scalar_one_or_none = MagicMock(return_value=participant)
                return result

            mock_db.execute = AsyncMock(side_effect=mock_execute)

            event = NotificationDueEvent(
                game_id=sample_game.id,
                notification_type="join_notification",
                participant_id=participant_id,
            )

            with patch("services.bot.events.handlers.logger") as mock_logger:
                game, part = await event_handlers._fetch_join_notification_data(mock_db, event)

                assert game is None
                assert part is None
                mock_get_game.assert_awaited_once_with(mock_db, str(event.game_id))
                mock_logger.info.assert_called_once_with(
                    "Participant %s no longer active for game %s",
                    event.participant_id,
                    event.game_id,
                )

    def test_should_send_join_notification_true_when_confirmed(self, event_handlers, sample_game):
        """A confirmed participant should be notified."""
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = [participant]
            mock_partitioned.overflow = []
            mock_partition.return_value = mock_partitioned

            should_send = event_handlers._should_send_join_notification(participant, sample_game)

            assert should_send is True
            mock_partition.assert_called_once_with(
                sample_game.participants,
                sample_game.max_players,
                signup_method=sample_game.signup_method,
            )

    def test_should_send_join_notification_false_when_not_found_in_either_partition(
        self, event_handlers, sample_game
    ):
        """A participant absent from both confirmed and overflow (e.g. removed
        from the game between scheduling and firing) is not notified.
        """
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partitioned.overflow = []
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.logger") as mock_logger:
                should_send = event_handlers._should_send_join_notification(
                    participant, sample_game
                )

                assert should_send is False
                mock_partition.assert_called_once_with(
                    sample_game.participants,
                    sample_game.max_players,
                    signup_method=sample_game.signup_method,
                )
                mock_logger.info.assert_called_once_with(
                    "Participant %s no longer in game %s, skipping join notification",
                    participant.id,
                    sample_game.id,
                )

    def test_should_send_join_notification_true_for_waitlisted_in_hsw_mode(
        self, event_handlers, sample_game
    ):
        """A waitlisted player in HOST_SELECTED_WITH_WAITLIST is notified (waitlist DM)."""
        sample_game.signup_method = SignupMethod.HOST_SELECTED_WITH_WAITLIST
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partitioned.overflow = [participant]
            mock_partition.return_value = mock_partitioned

            should_send = event_handlers._should_send_join_notification(participant, sample_game)

            assert should_send is True
            mock_partition.assert_called_once_with(
                sample_game.participants,
                sample_game.max_players,
                signup_method=sample_game.signup_method,
            )

    def test_should_send_join_notification_true_for_waitlisted_in_self_signup_mode(
        self, event_handlers, sample_game
    ):
        """A waitlisted player in SELF_SIGNUP is also notified (waitlist DM).

        Regression test: waitlisted self-joiners in SELF_SIGNUP (and every mode
        other than HOST_SELECTED_WITH_WAITLIST) never received any notification
        at all -- not even the fallback "no longer confirmed" skip log, just
        silence. Being on the waitlist is a real, notifiable state in any mode
        that allows landing there.
        """
        sample_game.signup_method = SignupMethod.SELF_SIGNUP
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partitioned.overflow = [participant]
            mock_partition.return_value = mock_partitioned

            should_send = event_handlers._should_send_join_notification(participant, sample_game)

            assert should_send is True
            mock_partition.assert_called_once_with(
                sample_game.participants,
                sample_game.max_players,
                signup_method=sample_game.signup_method,
            )

    def test_format_join_notification_message_with_instructions(self, event_handlers, sample_game):
        """Test message formatting with signup instructions."""
        sample_game.signup_instructions = "Join our Discord at https://discord.gg/test"
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_with_instructions.return_value = "Test message with instructions"

            message = event_handlers._format_join_notification_message(sample_game, participant)

            expected_jump_url = (
                f"https://discord.com/channels/"
                f"{sample_game.guild.guild_id}/{sample_game.channel.channel_id}/{sample_game.message_id}"
            )
            mock_formats.join_with_instructions.assert_called_once_with(
                sample_game.title,
                sample_game.signup_instructions,
                int(sample_game.scheduled_at.timestamp()),
                jump_url=expected_jump_url,
            )
            assert message == "Test message with instructions"

    def test_format_join_notification_message_without_instructions(
        self, event_handlers, sample_game
    ):
        """Test message formatting without signup instructions."""
        sample_game.signup_instructions = None
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_simple.return_value = "Test simple message"

            message = event_handlers._format_join_notification_message(sample_game, participant)

            expected_jump_url = (
                f"https://discord.com/channels/"
                f"{sample_game.guild.guild_id}/{sample_game.channel.channel_id}/{sample_game.message_id}"
            )
            mock_formats.join_simple.assert_called_once_with(
                sample_game.title, jump_url=expected_jump_url
            )
            assert message == "Test simple message"

    def test_format_join_notification_message_no_message_id(self, event_handlers, sample_game):
        """Test message formatting passes jump_url=None when message_id is absent."""
        sample_game.message_id = None
        sample_game.signup_instructions = None
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.DMFormats") as mock_formats:
            mock_formats.join_simple.return_value = "Test simple message"

            message = event_handlers._format_join_notification_message(sample_game, participant)

            mock_formats.join_simple.assert_called_once_with(sample_game.title, jump_url=None)
            assert message == "Test simple message"

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_success(self, event_handlers):
        """Test successful DM sending with success logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.info.assert_called_once()
                assert "✓ Sent join notification" in str(mock_logger.info.call_args)

    @pytest.mark.asyncio
    async def test_send_join_notification_dm_failure(self, event_handlers):
        """Test failed DM sending with warning logging."""
        participant = MagicMock()
        participant.user = MagicMock()
        participant.user.discord_id = "123456789"
        message = "Test notification message"
        game_id = str(uuid4())

        with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False

            with patch("services.bot.events.handlers.logger") as mock_logger:
                await event_handlers._send_join_notification_dm(participant, message, game_id)

                mock_send.assert_called_once_with("123456789", message)
                mock_logger.warning.assert_called_once()
                assert "Failed to send join notification" in str(mock_logger.warning.call_args)

    def test_format_join_notification_dispatches_waitlist_dm(self, event_handlers, sample_game):
        """Test join notification dispatches join_waitlist for a still-waitlisted
        participant in HOST_SELECTED_WITH_WAITLIST.

        join_simple and join_with_instructions must NOT be called.
        """
        sample_game.signup_method = SignupMethod.HOST_SELECTED_WITH_WAITLIST
        sample_game.signup_instructions = None
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partitioned.overflow = [participant]
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.DMFormats") as mock_formats:
                mock_formats.join_waitlist.return_value = "You're on the waitlist!"

                message = event_handlers._format_join_notification_message(sample_game, participant)

                mock_partition.assert_called_once_with(
                    sample_game.participants,
                    sample_game.max_players,
                    signup_method=sample_game.signup_method,
                )
                mock_formats.join_waitlist.assert_called_once_with(
                    game_title=sample_game.title,
                    jump_url=f"https://discord.com/channels/"
                    f"{sample_game.guild.guild_id}/{sample_game.channel.channel_id}/{sample_game.message_id}",
                    host_selects=True,
                )
                mock_formats.join_simple.assert_not_called()
                mock_formats.join_with_instructions.assert_not_called()
                assert message == "You're on the waitlist!"

    def test_format_join_notification_uses_instructions_for_confirmed_in_hsw_mode(
        self, event_handlers, sample_game
    ):
        """A participant who actually landed in a confirmed slot of a
        HOST_SELECTED_WITH_WAITLIST game (e.g. host-added directly) must get the
        host's welcome message, not the "you're on the waitlist" DM.
        """
        sample_game.signup_method = SignupMethod.HOST_SELECTED_WITH_WAITLIST
        sample_game.signup_instructions = "Bring your character sheet"
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = [participant]
            mock_partitioned.overflow = []
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.DMFormats") as mock_formats:
                mock_formats.join_with_instructions.return_value = "Welcome!"

                message = event_handlers._format_join_notification_message(sample_game, participant)

                mock_partition.assert_called_once_with(
                    sample_game.participants,
                    sample_game.max_players,
                    signup_method=sample_game.signup_method,
                )
                expected_jump_url = (
                    f"https://discord.com/channels/"
                    f"{sample_game.guild.guild_id}/{sample_game.channel.channel_id}/{sample_game.message_id}"
                )
                mock_formats.join_with_instructions.assert_called_once_with(
                    sample_game.title,
                    sample_game.signup_instructions,
                    int(sample_game.scheduled_at.timestamp()),
                    jump_url=expected_jump_url,
                )
                mock_formats.join_waitlist.assert_not_called()
                assert message == "Welcome!"

    def test_format_join_notification_dispatches_waitlist_dm_for_self_signup_mode(
        self, event_handlers, sample_game
    ):
        """A waitlisted participant in SELF_SIGNUP must get the waitlist DM too,
        not fall through to join_with_instructions/join_simple.
        """
        sample_game.signup_method = SignupMethod.SELF_SIGNUP
        sample_game.signup_instructions = None
        participant = MagicMock()
        participant.id = str(uuid4())

        with patch("services.bot.events.handlers.partition_participants") as mock_partition:
            mock_partitioned = MagicMock()
            mock_partitioned.confirmed = []
            mock_partitioned.overflow = [participant]
            mock_partition.return_value = mock_partitioned

            with patch("services.bot.events.handlers.DMFormats") as mock_formats:
                mock_formats.join_waitlist.return_value = "You're on the waitlist!"

                message = event_handlers._format_join_notification_message(sample_game, participant)

                mock_partition.assert_called_once_with(
                    sample_game.participants,
                    sample_game.max_players,
                    signup_method=sample_game.signup_method,
                )
                mock_formats.join_waitlist.assert_called_once_with(
                    game_title=sample_game.title,
                    jump_url=f"https://discord.com/channels/"
                    f"{sample_game.guild.guild_id}/{sample_game.channel.channel_id}/{sample_game.message_id}",
                    host_selects=False,
                )
                mock_formats.join_simple.assert_not_called()
                mock_formats.join_with_instructions.assert_not_called()
                assert message == "You're on the waitlist!"

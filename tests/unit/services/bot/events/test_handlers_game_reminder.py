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


"""Unit tests for EventHandlers game reminder methods."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import discord
import pytest

from shared.models import participant as participant_model
from shared.models.base import utc_now
from shared.models.game import GameSession
from shared.models.participant import ParticipantType
from shared.models.user import User


@pytest.mark.asyncio
async def test_send_reminder_dm_participant(event_handlers):
    """Test sending reminder DM to a regular participant."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=jump_url,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "123456789"
        message = call_args[0][1]
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Waitlist" not in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_participant_no_jump_url(event_handlers):
    """Test sending reminder DM to a participant when game has no jump URL."""
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=None,
        )

        message = mock_send_dm.call_args[0][1]
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert "discord.com" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_waitlist(event_handlers):
    """Test sending reminder DM to a waitlist participant."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="123456789",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=True,
            jump_url=jump_url,
            is_host=False,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        message = call_args[0][1]
        assert "🎫 **[Waitlist]**" in message
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Host" not in message


@pytest.mark.asyncio
async def test_send_reminder_dm_host(event_handlers):
    """Test sending reminder DM to game host."""
    jump_url = "https://discord.com/channels/111/222/333"
    with patch.object(event_handlers, "_send_dm", new_callable=AsyncMock) as mock_send_dm:
        await event_handlers._send_reminder_dm(
            user_discord_id="987654321",
            game_title="Test Game",
            game_time_unix=1700000000,
            _reminder_minutes=60,
            is_waitlist=False,
            jump_url=jump_url,
            is_host=True,
        )

        mock_send_dm.assert_awaited_once()
        call_args = mock_send_dm.call_args
        assert call_args[0][0] == "987654321"
        message = call_args[0][1]
        assert "🎮 **[Host]**" in message
        assert "Test Game" in message
        assert "<t:1700000000:F>" in message
        assert "<t:1700000000:R>" in message
        assert jump_url in message
        assert "Waitlist" not in message


@pytest.mark.asyncio
async def test_handle_game_reminder_due_success(event_handlers, sample_game, sample_user):
    """Test successful game reminder handling with host notification."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participant_user_1 = User(id=str(uuid4()), discord_id="participant456")
    participant_user_2 = User(id=str(uuid4()), discord_id="participant789")

    mock_participant_1 = MagicMock()
    mock_participant_1.user_id = participant_user_1.id
    mock_participant_1.user = participant_user_1
    mock_participant_1.position_type = ParticipantType.SELF_ADDED
    mock_participant_1.position = 0
    mock_participant_1.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    mock_participant_2 = MagicMock()
    mock_participant_2.user_id = participant_user_2.id
    mock_participant_2.user = participant_user_2
    mock_participant_2.position_type = ParticipantType.SELF_ADDED
    mock_participant_2.position = 0
    mock_participant_2.joined_at = datetime(2025, 11, 1, 11, 0, 0, tzinfo=UTC)

    sample_game.host = host_user
    sample_game.participants = [mock_participant_1, mock_participant_2]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 3

                    expected_jump_url = (
                        "https://discord.com/channels/disc_guild_123/disc_channel_456/999888777"
                    )

                    participant_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_host", False)
                    ]
                    assert len(participant_calls) == 2
                    for call in participant_calls:
                        assert call.kwargs["jump_url"] == expected_jump_url

                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"
                    assert host_calls[0].kwargs["is_host"] is True
                    assert host_calls[0].kwargs["jump_url"] == expected_jump_url
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_no_participants_but_host(
    event_handlers, sample_game, sample_user
):
    """Test game reminder when no participants but host should still receive notification."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    sample_game.host = host_user
    sample_game.participants = []
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {"game_id": sample_game.id, "notification_type": "reminder"}
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 1
                    assert mock_send_reminder.call_args.kwargs["user_discord_id"] == "host123"
                    assert mock_send_reminder.call_args.kwargs["is_host"] is True
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_no_host(event_handlers, sample_game):
    """Test game reminder when game has no host."""
    participant_user = User(id=str(uuid4()), discord_id="participant456")

    mock_participant = MagicMock()
    mock_participant.user_id = participant_user.id
    mock_participant.user = participant_user
    mock_participant.position_type = ParticipantType.SELF_ADDED
    mock_participant.position = 0
    mock_participant.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    sample_game.host = None
    sample_game.participants = [mock_participant]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 1
                    assert mock_send_reminder.call_args.kwargs.get("is_host", False) is False
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_host_error_doesnt_affect_participants(
    event_handlers, sample_game
):
    """Test that host notification failure doesn't prevent participant notifications."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participant_user = User(id=str(uuid4()), discord_id="participant456")

    mock_participant = MagicMock()
    mock_participant.user_id = participant_user.id
    mock_participant.user = participant_user
    mock_participant.position_type = ParticipantType.SELF_ADDED
    mock_participant.position = 0
    mock_participant.joined_at = datetime(2025, 11, 1, 10, 0, 0, tzinfo=UTC)

    sample_game.host = host_user
    sample_game.participants = [mock_participant]
    sample_game.max_players = 10
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                call_count = 0

                async def mock_send_reminder_side_effect(*args, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    if call_count == 2 and kwargs.get("is_host"):
                        error_msg = "Host notification failed"
                        raise Exception(error_msg)

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    mock_send_reminder.side_effect = mock_send_reminder_side_effect

                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 2
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_with_waitlist(event_handlers, sample_game):
    """Test game reminder with confirmed and waitlist participants plus host."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    participants = []
    for i in range(3):
        user = User(id=str(uuid4()), discord_id=f"participant{i}")
        mock_participant = MagicMock()
        mock_participant.user_id = user.id
        mock_participant.user = user
        mock_participant.position_type = ParticipantType.SELF_ADDED
        mock_participant.position = 0
        mock_participant.joined_at = datetime(2025, 11, 1, 10 + i, 0, 0, tzinfo=UTC)
        participants.append(mock_participant)

    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    assert mock_send_reminder.await_count == 4

                    confirmed_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if not call.kwargs.get("is_waitlist", False)
                        and not call.kwargs.get("is_host", False)
                    ]
                    assert len(confirmed_calls) == 2

                    waitlist_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_waitlist", False)
                    ]
                    assert len(waitlist_calls) == 1

                    host_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_host", False)
                    ]
                    assert len(host_calls) == 1
                    assert host_calls[0].kwargs["user_discord_id"] == "host123"
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


@pytest.mark.asyncio
async def test_handle_game_reminder_due_only_first_waitlist_reminded(event_handlers, sample_game):
    """Only the first waitlisted participant receives a reminder DM."""
    host_user = User(id=str(uuid4()), discord_id="host123")

    participants = []
    for i in range(4):
        user = User(id=str(uuid4()), discord_id=f"participant{i}")
        mock_participant = MagicMock()
        mock_participant.user_id = user.id
        mock_participant.user = user
        mock_participant.position_type = ParticipantType.SELF_ADDED
        mock_participant.position = 0
        mock_participant.joined_at = datetime(2025, 11, 1, 10 + i, 0, 0, tzinfo=UTC)
        participants.append(mock_participant)

    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)

    with patch("services.bot.events.handlers.get_db_session") as mock_db_session:
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        with patch("services.bot.events.handlers.utc_now") as mock_utc_now:
            mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

            with patch.object(
                event_handlers, "_get_game_with_participants", new_callable=AsyncMock
            ) as mock_get_game:
                mock_get_game.return_value = sample_game

                with patch.object(
                    event_handlers, "_send_reminder_dm", new_callable=AsyncMock
                ) as mock_send_reminder:
                    data = {
                        "game_id": sample_game.id,
                        "notification_type": "reminder",
                    }
                    await event_handlers._handle_notification_due(data)

                    # 2 confirmed + 1 waitlist (first only) + 1 host = 4
                    assert mock_send_reminder.await_count == 4

                    waitlist_calls = [
                        call
                        for call in mock_send_reminder.call_args_list
                        if call.kwargs.get("is_waitlist", False)
                    ]
                    assert len(waitlist_calls) == 1
                    # The first overflow participant (participant2) gets the DM
                    assert waitlist_calls[0].kwargs["user_discord_id"] == "participant2"
                    mock_db_session.assert_called()
                    mock_utc_now.assert_called()
                    mock_get_game.assert_awaited_once_with(mock_db, sample_game.id)


def _reminder_flow_patches(
    event_handlers,
    sample_game,
    get_bot_channel_return=None,
    post_result=True,
):
    """Patch stack for driving _handle_notification_due through a reminder flow."""
    db_patch = patch("services.bot.events.handlers.get_db_session")
    utc_patch = patch("services.bot.events.handlers.utc_now")
    game_patch = patch.object(event_handlers, "_get_game_with_participants", new_callable=AsyncMock)
    channel_patch = patch.object(event_handlers, "_get_bot_channel", new_callable=AsyncMock)
    post_patch = patch.object(event_handlers, "_post_reminder_to_channel", new_callable=AsyncMock)
    dm_patch = patch.object(event_handlers, "_send_reminder_dm", new_callable=AsyncMock)

    def start_all():
        mock_db_session = db_patch.start()
        mock_db = MagicMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock()
        mock_db_session.return_value = mock_db

        mock_utc_now = utc_patch.start()
        mock_utc_now.return_value = datetime(2025, 12, 13, 10, 0, 0, tzinfo=UTC)

        mock_get_game = game_patch.start()
        mock_get_game.return_value = sample_game

        mock_get_channel = channel_patch.start()
        mock_get_channel.return_value = get_bot_channel_return

        mock_post = post_patch.start()
        mock_post.return_value = post_result

        mock_send_reminder = dm_patch.start()
        return (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        )

    def stop_all():
        for p in (dm_patch, post_patch, channel_patch, game_patch, utc_patch, db_patch):
            p.stop()

    return start_all, stop_all


def _make_participants(count: int, discord_ids: list[str]):
    """Build MagicMock participants with real User objects."""
    participants = []
    for i in range(count):
        user = User(id=str(uuid4()), discord_id=discord_ids[i])
        mock_participant = MagicMock()
        mock_participant.user_id = user.id
        mock_participant.user = user
        mock_participant.position_type = ParticipantType.SELF_ADDED
        mock_participant.position = 0
        mock_participant.joined_at = datetime(2025, 11, 1, 10 + i, 0, 0, tzinfo=UTC)
        participants.append(mock_participant)
    return participants


@pytest.mark.asyncio
async def test_post_reminder_to_channel_success(event_handlers, sample_game):
    """Channel post mentions confirmed + host and returns True on success."""

    host_user = User(id=str(uuid4()), discord_id="host123")
    confirmed = _make_participants(2, ["confirmed1", "confirmed2"])
    sample_game.host = host_user

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_channel.id = "channel-abc"

    result = await event_handlers._post_reminder_to_channel(
        channel=mock_channel,
        game=sample_game,
        confirmed=confirmed,
        jump_url="https://discord.com/channels/1/2/3",
    )

    assert result is True
    mock_channel.send.assert_awaited_once()
    kwargs = mock_channel.send.call_args.kwargs
    content = kwargs["content"]
    assert "<@confirmed1>" in content
    assert "<@confirmed2>" in content
    assert "<@host123>" in content
    embed: discord.Embed = kwargs["embed"]
    assert isinstance(embed, discord.Embed)
    assert embed.title == "🔔 Game Reminder"
    # Compact layout: no fields; all content lives in the description
    assert not embed.fields
    desc = embed.description or ""
    assert "**Test Game**" in desc
    assert "<t:" in desc and ":F>" in desc and ":R>" in desc
    # Host mentions stay in message content, never in the embed
    assert "<@" not in desc
    assert "📅" not in desc and "🎯" not in desc and "📍" not in desc and "🔗" not in desc
    assert "[View in scheduler](https://discord.com/channels/1/2/3)" in desc
    # sample_game has no where set → no Where line
    assert "**Where:**" not in desc
    allowed_mentions = kwargs["allowed_mentions"]
    assert isinstance(allowed_mentions, discord.AllowedMentions)
    assert allowed_mentions.everyone is False
    assert allowed_mentions.roles is False
    assert allowed_mentions.users is True


@pytest.mark.asyncio
async def test_post_reminder_dedupes_host_who_is_player(event_handlers, sample_game):
    """A host who is also a confirmed participant appears in the ping line exactly once."""

    host_user = User(id=str(uuid4()), discord_id="host123")
    # host123 is both the host and one of the confirmed players
    confirmed = _make_participants(2, ["confirmed1", "host123"])
    sample_game.host = host_user

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_channel.id = "channel-abc"

    result = await event_handlers._post_reminder_to_channel(
        channel=mock_channel,
        game=sample_game,
        confirmed=confirmed,
        jump_url=None,
    )

    assert result is True
    content = mock_channel.send.call_args.kwargs["content"]
    assert content.count("<@host123>") == 1
    assert "<@confirmed1>" in content


@pytest.mark.asyncio
async def test_post_reminder_to_channel_forbidden_returns_false(event_handlers, sample_game):
    """Forbidden (missing send permission) returns False so caller falls back to DMs."""

    host_user = User(id=str(uuid4()), discord_id="host123")
    confirmed = _make_participants(1, ["confirmed1"])
    sample_game.host = host_user

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock(side_effect=discord.Forbidden(MagicMock(), ""))
    mock_channel.id = "channel-abc"

    result = await event_handlers._post_reminder_to_channel(
        channel=mock_channel,
        game=sample_game,
        confirmed=confirmed,
        jump_url=None,
    )

    assert result is False


@pytest.mark.asyncio
async def test_post_reminder_to_channel_not_found_returns_false(event_handlers, sample_game):
    """NotFound (deleted channel) returns False so caller falls back to DMs."""

    host_user = User(id=str(uuid4()), discord_id="host123")
    confirmed = _make_participants(1, ["confirmed1"])
    sample_game.host = host_user

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock(side_effect=discord.NotFound(MagicMock(), ""))
    mock_channel.id = "channel-abc"

    result = await event_handlers._post_reminder_to_channel(
        channel=mock_channel,
        game=sample_game,
        confirmed=confirmed,
        jump_url=None,
    )

    assert result is False


@pytest.mark.asyncio
async def test_post_reminder_to_channel_no_host_omits_host_mention(event_handlers, sample_game):
    """Without a host the post content mentions only confirmed participants."""

    confirmed = _make_participants(1, ["confirmed1"])
    sample_game.host = None

    mock_channel = MagicMock(spec=discord.TextChannel)
    mock_channel.send = AsyncMock()
    mock_channel.id = "channel-abc"

    result = await event_handlers._post_reminder_to_channel(
        channel=mock_channel,
        game=sample_game,
        confirmed=confirmed,
        jump_url=None,
    )

    assert result is True
    content = mock_channel.send.call_args.kwargs["content"]
    assert "<@confirmed1>" in content
    assert "<@" not in content.replace("<@confirmed1>", "")


@pytest.mark.asyncio
async def test_handle_game_reminder_channel_post_success(event_handlers, sample_game):
    """Single-channel location posts to the channel and DMs only first waitlisted."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    # 3 participants with max_players=2: participant0/1 confirmed, participant2 waitlist
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#123456789>"

    mock_channel = MagicMock()
    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=mock_channel, post_result=True
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        mock_get_channel.assert_awaited_once_with("123456789")
        mock_post.assert_awaited_once()
        # Only the first waitlisted participant receives a DM; no confirmed/host DMs
        assert mock_send_reminder.await_count == 1
        call_kwargs = mock_send_reminder.call_args.kwargs
        assert call_kwargs["user_discord_id"] == "participant2"
        assert call_kwargs["is_waitlist"] is True
        assert call_kwargs.get("is_host", False) is False
        mock_db_session.assert_called()
        mock_utc_now.assert_called()
        mock_get_game.assert_awaited_once_with(mock_db_session.return_value, sample_game.id)
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_handle_game_reminder_channel_post_failed_falls_back_to_dms(
    event_handlers, sample_game
):
    """Failed channel post falls back to full DM fan-out (confirmed + waitlist + host)."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#123456789>"

    mock_channel = MagicMock()
    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=mock_channel, post_result=False
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        mock_post.assert_awaited_once()
        # Full fan-out: 2 confirmed + 1 waitlist + 1 host = 4 DMs
        assert mock_send_reminder.await_count == 4

        confirmed_calls = [
            call
            for call in mock_send_reminder.call_args_list
            if not call.kwargs.get("is_waitlist", False) and not call.kwargs.get("is_host", False)
        ]
        assert len(confirmed_calls) == 2

        waitlist_calls = [
            call
            for call in mock_send_reminder.call_args_list
            if call.kwargs.get("is_waitlist", False)
        ]
        assert len(waitlist_calls) == 1
        assert waitlist_calls[0].kwargs["user_discord_id"] == "participant2"

        host_calls = [
            call for call in mock_send_reminder.call_args_list if call.kwargs.get("is_host", False)
        ]
        assert len(host_calls) == 1
        assert host_calls[0].kwargs["user_discord_id"] == "host123"
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_handle_game_reminder_no_channel_falls_back_to_dms(event_handlers, sample_game):
    """Unresolvable channel falls back to full DM fan-out without posting."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#123456789>"

    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=None, post_result=True
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        mock_get_channel.assert_awaited_once_with("123456789")
        mock_post.assert_not_awaited()
        # Full fan-out: 2 confirmed + 1 waitlist + 1 host = 4 DMs
        assert mock_send_reminder.await_count == 4
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_handle_game_reminder_ambiguous_location_falls_back_to_dms(
    event_handlers, sample_game
):
    """Multiple channel mentions in where fall back to full DM fan-out."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#111> and <#222>"

    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=None, post_result=True
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        # No single channel resolves, so no lookup or post is attempted
        mock_get_channel.assert_not_awaited()
        mock_post.assert_not_awaited()
        assert mock_send_reminder.await_count == 4
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_handle_game_reminder_dms_only_flag_skips_channel_post(event_handlers, sample_game):
    """reminders_as_dms=True skips channel lookup/post and sends full DM fan-out."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#123456789>"
    sample_game.reminders_as_dms = True

    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=None, post_result=True
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        # No channel lookup or post is attempted when the flag is set
        mock_get_channel.assert_not_awaited()
        mock_post.assert_not_awaited()
        # Full fan-out: 2 confirmed + 1 waitlist + 1 host = 4 DMs
        assert mock_send_reminder.await_count == 4

        confirmed_calls = [
            call
            for call in mock_send_reminder.call_args_list
            if not call.kwargs.get("is_waitlist", False) and not call.kwargs.get("is_host", False)
        ]
        assert len(confirmed_calls) == 2

        waitlist_calls = [
            call
            for call in mock_send_reminder.call_args_list
            if call.kwargs.get("is_waitlist", False)
        ]
        assert len(waitlist_calls) == 1
        assert waitlist_calls[0].kwargs["user_discord_id"] == "participant2"

        host_calls = [
            call for call in mock_send_reminder.call_args_list if call.kwargs.get("is_host", False)
        ]
        assert len(host_calls) == 1
        assert host_calls[0].kwargs["user_discord_id"] == "host123"
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_handle_game_reminder_dms_only_flag_false_still_posts(event_handlers, sample_game):
    """reminders_as_dms=False keeps the existing channel-post success path."""
    host_user = User(id=str(uuid4()), discord_id="host123")
    participants = _make_participants(3, ["participant0", "participant1", "participant2"])
    sample_game.host = host_user
    sample_game.participants = participants
    sample_game.max_players = 2
    sample_game.scheduled_at = datetime(2025, 12, 20, 18, 0, 0, tzinfo=UTC)
    sample_game.where = "<#123456789>"
    sample_game.reminders_as_dms = False

    mock_channel = MagicMock()
    start_all, stop_all = _reminder_flow_patches(
        event_handlers, sample_game, get_bot_channel_return=mock_channel, post_result=True
    )
    try:
        (
            mock_db_session,
            mock_utc_now,
            mock_get_game,
            mock_get_channel,
            mock_post,
            mock_send_reminder,
        ) = start_all()

        data = {"game_id": sample_game.id, "notification_type": "reminder"}
        await event_handlers._handle_notification_due(data)

        mock_get_channel.assert_awaited_once_with("123456789")
        mock_post.assert_awaited_once()
        # Channel-post success path: only the first waitlisted participant gets a DM
        assert mock_send_reminder.await_count == 1
        call_kwargs = mock_send_reminder.call_args.kwargs
        assert call_kwargs["user_discord_id"] == "participant2"
        assert call_kwargs["is_waitlist"] is True
    finally:
        stop_all()


@pytest.mark.asyncio
async def test_validate_game_for_reminder_already_started(event_handlers):
    """Test validation rejects game that already started."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() - timedelta(hours=1),
        status="SCHEDULED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is False


@pytest.mark.asyncio
async def test_validate_game_for_reminder_wrong_status(event_handlers):
    """Test validation rejects non-scheduled game."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() + timedelta(hours=1),
        status="COMPLETED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is False


@pytest.mark.asyncio
async def test_validate_game_for_reminder_valid(event_handlers):
    """Test validation accepts valid scheduled game."""
    game = GameSession(
        id=str(uuid4()),
        scheduled_at=utc_now() + timedelta(hours=1),
        status="SCHEDULED",
    )

    result = await event_handlers._validate_game_for_reminder(game, game.id)

    assert result is True


def test_partition_and_filter_participants_with_users(event_handlers):
    """Test partitioning with real user participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")
    user2 = User(id=str(uuid4()), discord_id="user2")
    user3 = User(id=str(uuid4()), discord_id="user3")

    participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p3",
            game_session_id="game1",
            user_id=user3.id,
            user=user3,
            position=2,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    game = GameSession(
        id="game1",
        max_players=2,
        participants=participants,
    )

    confirmed, overflow = event_handlers._partition_and_filter_participants(game)

    assert len(confirmed) == 2
    assert len(overflow) == 1
    assert confirmed[0].user == user1
    assert confirmed[1].user == user2
    assert overflow[0].user == user3


def test_partition_and_filter_participants_excludes_placeholders(event_handlers):
    """Test filtering excludes placeholder participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")

    participants = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=None,
            user=None,
            position=1,
            position_type=ParticipantType.HOST_ADDED,
        ),
    ]

    game = GameSession(
        id="game1",
        max_players=2,
        participants=participants,
    )

    confirmed, overflow = event_handlers._partition_and_filter_participants(game)

    assert len(confirmed) == 1
    assert len(overflow) == 0
    assert confirmed[0].user == user1


@pytest.mark.asyncio
async def test_send_participant_reminders_success(event_handlers):
    """Test sending reminders to participants."""
    user1 = User(id=str(uuid4()), discord_id="user1")
    user2 = User(id=str(uuid4()), discord_id="user2")

    participants_list = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
        participant_model.GameParticipant(
            id="p2",
            game_session_id="game1",
            user_id=user2.id,
            user=user2,
            position=1,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_participant_reminders(
            participants_list,
            "Test Game",
            1234567890,
            is_waitlist=False,
            jump_url=None,
        )

        assert mock_send.call_count == 2
        mock_send.assert_any_await(
            user_discord_id="user1",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
        )
        mock_send.assert_any_await(
            user_discord_id="user2",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
        )


@pytest.mark.asyncio
async def test_send_participant_reminders_handles_errors(event_handlers):
    """Test error handling when sending reminders."""
    user1 = User(id=str(uuid4()), discord_id="user1")

    participants_list = [
        participant_model.GameParticipant(
            id="p1",
            game_session_id="game1",
            user_id=user1.id,
            user=user1,
            position=0,
            position_type=ParticipantType.SELF_ADDED,
        ),
    ]

    with patch.object(
        event_handlers,
        "_send_reminder_dm",
        new=AsyncMock(side_effect=Exception("DM failed")),
    ):
        await event_handlers._send_participant_reminders(
            participants_list,
            "Test Game",
            1234567890,
            is_waitlist=False,
            jump_url=None,
        )
    assert True  # verifies exception is caught without propagating


@pytest.mark.asyncio
async def test_send_host_reminder_success(event_handlers):
    """Test sending reminder to game host."""
    host = User(id=str(uuid4()), discord_id="host123")

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_awaited_once_with(
            user_discord_id="host123",
            game_title="Test Game",
            game_time_unix=1234567890,
            _reminder_minutes=0,
            is_waitlist=False,
            jump_url=None,
            is_host=True,
        )


@pytest.mark.asyncio
async def test_send_host_reminder_no_host(event_handlers):
    """Test handling when no host present."""
    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            None,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_host_reminder_no_discord_id(event_handlers):
    """Test handling when host has no Discord ID."""
    host = User(id=str(uuid4()), discord_id=None)

    with patch.object(event_handlers, "_send_reminder_dm", new=AsyncMock()) as mock_send:
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )

        mock_send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_host_reminder_handles_error(event_handlers):
    """Test error handling when sending host reminder."""
    host = User(id=str(uuid4()), discord_id="host123")

    with patch.object(
        event_handlers,
        "_send_reminder_dm",
        new=AsyncMock(side_effect=Exception("DM failed")),
    ):
        await event_handlers._send_host_reminder(
            host,
            "Test Game",
            1234567890,
            jump_url=None,
        )
    assert True  # verifies exception is caught without propagating

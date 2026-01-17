# Copyright 2025 Bret McKee (bret.mckee@gmail.com)
#
# This file is part of Game_Scheduler. (https://github.com/game-scheduler)
#
# Game_Scheduler is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Game_Scheduler is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General
# Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with Game_Scheduler If not, see <https://www.gnu.org/licenses/>.


"""Unit tests for _update_game_fields helper methods."""

import datetime
import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared.discord import client as discord_client_module
from shared.messaging import publisher as messaging_publisher
from shared.models import game as game_model
from shared.schemas import game as game_schemas


@pytest.fixture
def mock_db():
    """Create mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_event_publisher():
    """Create mock event publisher."""
    publisher = AsyncMock(spec=messaging_publisher.EventPublisher)
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def mock_discord_client():
    """Create mock Discord API client."""
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def mock_participant_resolver():
    """Create mock participant resolver."""
    return AsyncMock(spec=resolver_module.ParticipantResolver)


@pytest.fixture
def game_service(mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver):
    """Create game service instance."""
    return games_service.GameService(
        db=mock_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_client,
        participant_resolver=mock_participant_resolver,
    )


def test_update_simple_text_fields_updates_all_fields(game_service):
    """Test _update_simple_text_fields updates all simple text fields."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Original Title",
        description="Original Description",
        signup_instructions="Original Instructions",
        where="Original Location",
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        title="New Title",
        description="New Description",
        signup_instructions="New Instructions",
        where="New Location",
    )

    game_service._update_simple_text_fields(game, update_data)

    assert game.title == "New Title"
    assert game.description == "New Description"
    assert game.signup_instructions == "New Instructions"
    assert game.where == "New Location"


def test_update_simple_text_fields_skips_none_values(game_service):
    """Test _update_simple_text_fields skips fields with None values."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Original Title",
        description="Original Description",
        signup_instructions="Original Instructions",
        where="Original Location",
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        title="New Title",
        description=None,
        signup_instructions=None,
        where=None,
    )

    game_service._update_simple_text_fields(game, update_data)

    assert game.title == "New Title"
    assert game.description == "Original Description"
    assert game.signup_instructions == "Original Instructions"
    assert game.where == "Original Location"


def test_update_scheduled_at_field_with_timezone_aware_datetime(game_service):
    """Test _update_scheduled_at_field converts timezone-aware datetime to naive UTC."""
    original_time = datetime.datetime.now(UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=original_time,
        status="SCHEDULED",
    )

    # Create timezone-aware datetime (EST = UTC-5)
    est = datetime.timezone(datetime.timedelta(hours=-5))
    new_time = datetime.datetime(2026, 3, 15, 14, 30, 0, tzinfo=est)  # 2:30 PM EST
    expected_utc = datetime.datetime(2026, 3, 15, 19, 30, 0)  # 7:30 PM UTC (naive)

    update_data = game_schemas.GameUpdateRequest(
        scheduled_at=new_time,
    )

    result = game_service._update_scheduled_at_field(game, update_data)

    assert result is True
    assert game.scheduled_at == expected_utc
    assert game.scheduled_at.tzinfo is None


def test_update_scheduled_at_field_with_naive_datetime(game_service):
    """Test _update_scheduled_at_field preserves naive datetime."""
    original_time = datetime.datetime.now(UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=original_time,
        status="SCHEDULED",
    )

    new_time = datetime.datetime(2026, 3, 15, 19, 30, 0)  # Naive UTC

    update_data = game_schemas.GameUpdateRequest(
        scheduled_at=new_time,
    )

    result = game_service._update_scheduled_at_field(game, update_data)

    assert result is True
    assert game.scheduled_at == new_time
    assert game.scheduled_at.tzinfo is None


def test_update_scheduled_at_field_returns_false_when_none(game_service):
    """Test _update_scheduled_at_field returns False when scheduled_at is None."""
    original_time = datetime.datetime.now(UTC).replace(tzinfo=None)
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=original_time,
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        scheduled_at=None,
    )

    result = game_service._update_scheduled_at_field(game, update_data)

    assert result is False
    assert game.scheduled_at == original_time


def test_update_schedule_affecting_fields_updates_reminder_minutes(game_service):
    """Test _update_schedule_affecting_fields updates reminder_minutes and returns True."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        reminder_minutes=[60, 15],
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        reminder_minutes=[120, 30, 10],
    )

    result = game_service._update_schedule_affecting_fields(game, update_data)

    assert result is True
    assert game.reminder_minutes == [120, 30, 10]


def test_update_schedule_affecting_fields_returns_false_when_none(game_service):
    """Test _update_schedule_affecting_fields returns False when reminder_minutes is None."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        reminder_minutes=[60, 15],
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        reminder_minutes=None,
    )

    result = game_service._update_schedule_affecting_fields(game, update_data)

    assert result is False
    assert game.reminder_minutes == [60, 15]


def test_update_remaining_fields_updates_all_fields(game_service):
    """Test _update_remaining_fields updates max_players, duration, roles, and signup_method."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        max_players=4,
        expected_duration_minutes=60,
        notify_role_ids=["123456789012345678"],
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
    )

    update_data = game_schemas.GameUpdateRequest(
        max_players=6,
        expected_duration_minutes=120,
        notify_role_ids=["234567890123456789", "345678901234567890"],
        signup_method="HOST_SELECTED",
    )

    result = game_service._update_remaining_fields(game, update_data)

    assert result is False  # status not updated
    assert game.max_players == 6
    assert game.expected_duration_minutes == 120
    assert game.notify_role_ids == ["234567890123456789", "345678901234567890"]
    assert game.signup_method == "HOST_SELECTED"


def test_update_remaining_fields_status_update_returns_true(game_service):
    """Test _update_remaining_fields returns True when status is updated."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        status="SCHEDULED",
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
    )

    update_data = game_schemas.GameUpdateRequest(
        status="IN_PROGRESS",
    )

    result = game_service._update_remaining_fields(game, update_data)

    assert result is True
    assert game.status == "IN_PROGRESS"


def test_update_remaining_fields_skips_none_values(game_service):
    """Test _update_remaining_fields preserves fields when update values are None."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        max_players=4,
        expected_duration_minutes=60,
        notify_role_ids=["role1"],
        status="SCHEDULED",
        signup_method="SELF_SIGNUP",
        scheduled_at=datetime.datetime.now(UTC).replace(tzinfo=None),
    )

    update_data = game_schemas.GameUpdateRequest(
        max_players=None,
        expected_duration_minutes=None,
        notify_role_ids=None,
        status=None,
        signup_method=None,
    )

    result = game_service._update_remaining_fields(game, update_data)

    assert result is False
    assert game.max_players == 4
    assert game.expected_duration_minutes == 60
    assert game.notify_role_ids == ["role1"]
    assert game.status == "SCHEDULED"
    assert game.signup_method == "SELF_SIGNUP"


def test_update_game_fields_integrates_all_helpers(game_service):
    """Test _update_game_fields correctly integrates all helper methods."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Original Title",
        description="Original Description",
        where="Original Location",
        max_players=4,
        reminder_minutes=[60],
        scheduled_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        title="New Title",
        where="New Location",
        max_players=6,
        reminder_minutes=[120, 30],
        scheduled_at=datetime.datetime(2026, 2, 1, 14, 0, 0),
    )

    schedule_needs_update, status_schedule_needs_update = game_service._update_game_fields(
        game, update_data
    )

    # Verify simple text fields updated
    assert game.title == "New Title"
    assert game.where == "New Location"
    assert game.description == "Original Description"  # Not updated

    # Verify remaining fields updated
    assert game.max_players == 6

    # Verify schedule-affecting fields updated
    assert game.reminder_minutes == [120, 30]

    # Verify scheduled_at updated
    assert game.scheduled_at == datetime.datetime(2026, 2, 1, 14, 0, 0)

    # Verify return values correct (scheduled_at and reminder_minutes both trigger updates)
    assert schedule_needs_update is True
    assert status_schedule_needs_update is True


def test_update_game_fields_scheduled_at_affects_both_schedules(game_service):
    """Test _update_game_fields sets both flags when scheduled_at is updated."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        scheduled_at=datetime.datetime(2026, 2, 1, 14, 0, 0),
    )

    schedule_needs_update, status_schedule_needs_update = game_service._update_game_fields(
        game, update_data
    )

    assert schedule_needs_update is True
    assert status_schedule_needs_update is True


def test_update_game_fields_status_only_affects_status_schedule(game_service):
    """Test _update_game_fields sets only status_schedule flag when status changes."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        status="IN_PROGRESS",
    )

    schedule_needs_update, status_schedule_needs_update = game_service._update_game_fields(
        game, update_data
    )

    assert schedule_needs_update is False
    assert status_schedule_needs_update is True


def test_update_game_fields_reminder_only_affects_notification_schedule(game_service):
    """Test _update_game_fields sets only notification schedule flag for reminder changes."""
    game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        reminder_minutes=[60],
        scheduled_at=datetime.datetime(2026, 1, 1, 12, 0, 0),
        status="SCHEDULED",
    )

    update_data = game_schemas.GameUpdateRequest(
        reminder_minutes=[120, 30],
    )

    schedule_needs_update, status_schedule_needs_update = game_service._update_game_fields(
        game, update_data
    )

    assert schedule_needs_update is True
    assert status_schedule_needs_update is False

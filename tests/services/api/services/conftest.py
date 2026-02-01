# Copyright 2026 Bret McKee (bret.mckee@gmail.com)
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


"""Shared fixtures for API game service tests.

This module provides shared test fixtures for the game service cluster
(test_games.py, test_games_promotion.py, test_games_edit_participants.py,
test_games_image_upload.py, test_update_game_fields_helpers.py).

Fixtures Provided:
- mock_db: AsyncMock of AsyncSession for database operations
- mock_event_publisher: AsyncMock of DeferredEventPublisher for event publishing
- mock_discord_client: MagicMock of DiscordClient for Discord API operations
- mock_participant_resolver: AsyncMock of participant resolver functions
- game_service: Configured GameService instance with all mocks
- sample_guild: Sample Guild model for test data
- sample_channel: Sample Channel model for test data
- sample_user: Sample User model for test data

Usage:
    Test files in this directory automatically have access to these fixtures.
    Create additional test-specific fixtures in individual test files when
    they are only needed for that specific test scenario.

Example:
    def test_create_game(game_service, sample_guild, sample_channel):
        # Use shared fixtures directly in test parameters
        pass
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.api.services import games as games_service
from services.api.services import participant_resolver as resolver_module
from shared.discord import client as discord_client_module
from shared.messaging import deferred_publisher as messaging_deferred_publisher
from shared.models import channel as channel_model
from shared.models import guild as guild_model
from shared.models import user as user_model


@pytest.fixture
def mock_db():
    """Mock database session for service tests."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_event_publisher():
    """Mock deferred event publisher for game events."""
    publisher = AsyncMock(spec=messaging_deferred_publisher.DeferredEventPublisher)
    publisher.publish_deferred = MagicMock()
    return publisher


@pytest.fixture
def mock_discord_client():
    """Mock Discord API client."""
    return MagicMock(spec=discord_client_module.DiscordAPIClient)


@pytest.fixture
def mock_participant_resolver():
    """Mock participant resolver."""
    return AsyncMock(spec=resolver_module.ParticipantResolver)


@pytest.fixture
def game_service(mock_db, mock_event_publisher, mock_discord_client, mock_participant_resolver):
    """Game service instance with mocked dependencies."""
    return games_service.GameService(
        db=mock_db,
        event_publisher=mock_event_publisher,
        discord_client=mock_discord_client,
        participant_resolver=mock_participant_resolver,
    )


@pytest.fixture
def sample_guild():
    """Sample guild configuration for tests."""
    return guild_model.GuildConfiguration(
        id=str(uuid.uuid4()),
        guild_id="123456789",
    )


@pytest.fixture
def sample_channel(sample_guild):
    """Sample channel configuration for tests."""
    return channel_model.ChannelConfiguration(
        id=str(uuid.uuid4()),
        channel_id="987654321",
        guild_id=sample_guild.id,
    )


@pytest.fixture
def sample_user():
    """Sample user for tests."""
    return user_model.User(
        id=str(uuid.uuid4()),
        discord_id="111222333",
    )

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


"""Unit tests for game image upload functionality."""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models import channel as channel_model
from shared.models import game as game_model
from shared.models import guild as guild_model
from shared.models import template as template_model
from shared.models import user as user_model
from shared.schemas import game as game_schemas


@pytest.fixture
def mock_role_service():
    """Create mock role service."""
    role_service = AsyncMock()
    role_service.check_game_host_permission = AsyncMock(return_value=True)
    return role_service


@pytest.fixture
def sample_template(sample_guild, sample_channel):
    """Create sample game template."""
    return template_model.GameTemplate(
        id=str(uuid.uuid4()),
        name="Test Game",
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        max_players=10,
        reminder_minutes=[60, 15],
    )


async def test_create_game_with_thumbnail(
    game_service,
    mock_db,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
    mock_role_service,
):
    """Test creating game with thumbnail image."""
    # Image data
    thumbnail_data = b"fake_image_data"
    thumbnail_mime = "image/png"

    # Create expected game object
    expected_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status=game_model.GameStatus.SCHEDULED.value,
        signup_method="SELF_SIGNUP",
        thumbnail_data=thumbnail_data,
        thumbnail_mime_type=thumbnail_mime,
    )
    expected_game.participants = []

    # Mock database queries
    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one.return_value = expected_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = expected_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            user_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    # Create game data
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        description=None,
        max_players=None,
        expected_duration_minutes=None,
        reminder_minutes=None,
        where=None,
        signup_instructions=None,
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="test_token",
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime,
        )

    # Verify image data was set
    assert game.thumbnail_data == thumbnail_data
    assert game.thumbnail_mime_type == thumbnail_mime
    assert game.image_data is None
    assert game.image_mime_type is None


async def test_create_game_with_both_images(
    game_service,
    mock_db,
    sample_template,
    sample_guild,
    sample_channel,
    sample_user,
    mock_role_service,
):
    """Test creating game with both thumbnail and banner images."""
    # Image data
    thumbnail_data = b"fake_thumbnail_data"
    thumbnail_mime = "image/png"
    image_data = b"fake_image_data"
    image_mime = "image/jpeg"

    # Create expected game object
    expected_game = game_model.GameSession(
        id=str(uuid.uuid4()),
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=sample_guild.id,
        channel_id=sample_channel.id,
        host_id=sample_user.id,
        status=game_model.GameStatus.SCHEDULED.value,
        signup_method="SELF_SIGNUP",
        thumbnail_data=thumbnail_data,
        thumbnail_mime_type=thumbnail_mime,
        image_data=image_data,
        image_mime_type=image_mime,
    )
    expected_game.participants = []

    # Mock database queries
    template_result = MagicMock()
    template_result.scalar_one_or_none.return_value = sample_template
    guild_result = MagicMock()
    guild_result.scalar_one_or_none.return_value = sample_guild
    channel_result = MagicMock()
    channel_result.scalar_one_or_none.return_value = sample_channel
    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = sample_user
    reload_result = MagicMock()
    reload_result.scalar_one.return_value = expected_game
    get_game_result = MagicMock()
    get_game_result.scalar_one_or_none.return_value = expected_game

    mock_db.execute = AsyncMock(
        side_effect=[
            template_result,
            guild_result,
            channel_result,
            user_result,
            reload_result,
            get_game_result,
        ]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    # Create game data
    game_data = game_schemas.GameCreateRequest(
        template_id=sample_template.id,
        title="Test Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        description=None,
        max_players=None,
        expected_duration_minutes=None,
        reminder_minutes=None,
        where=None,
        signup_instructions=None,
    )

    with patch("services.api.auth.roles.get_role_service", return_value=mock_role_service):
        game = await game_service.create_game(
            game_data=game_data,
            host_user_id=sample_user.id,
            access_token="test_token",
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime,
            image_data=image_data,
            image_mime_type=image_mime,
        )

    # Verify both images were set
    assert game.thumbnail_data == thumbnail_data
    assert game.thumbnail_mime_type == thumbnail_mime
    assert game.image_data == image_data
    assert game.image_mime_type == image_mime


async def test_update_game_with_new_thumbnail(game_service, mock_db, mock_role_service):
    """Test updating game with new thumbnail."""
    # Create existing game
    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=str(uuid.uuid4()),
    )
    existing_game = game_model.GameSession(
        id=game_id,
        title="Existing Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=str(uuid.uuid4()),
        channel_id=channel_id,
        host_id=str(uuid.uuid4()),
        status=game_model.GameStatus.SCHEDULED.value,
        thumbnail_data=None,
        thumbnail_mime_type=None,
    )
    existing_game.host = user_model.User(id=existing_game.host_id, discord_id="999888777")
    existing_game.guild = guild_model.GuildConfiguration(
        id=existing_game.guild_id, guild_id="123456"
    )
    existing_game.channel = mock_channel
    existing_game.participants = []

    # Mock database queries
    mock_db.execute = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=existing_game)
    mock_db.execute.return_value.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Update data
    update_data = game_schemas.GameUpdateRequest(
        title=None,
        description=None,
        signup_instructions=None,
        scheduled_at=None,
        where=None,
        max_players=None,
        reminder_minutes=None,
        expected_duration_minutes=None,
        status=None,
        notify_role_ids=None,
        participants=None,
        removed_participant_ids=None,
    )
    thumbnail_data = b"new_thumbnail_data"
    thumbnail_mime = "image/png"

    # Mock current user
    current_user = MagicMock()
    current_user.user.discord_id = "999888777"
    current_user.access_token = "test_token"

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=current_user,
            role_service=mock_role_service,
            thumbnail_data=thumbnail_data,
            thumbnail_mime_type=thumbnail_mime,
        )

    # Verify thumbnail was updated
    assert existing_game.thumbnail_data == thumbnail_data
    assert existing_game.thumbnail_mime_type == thumbnail_mime


async def test_update_game_remove_thumbnail(game_service, mock_db, mock_role_service):
    """Test removing thumbnail from game."""
    # Create existing game with thumbnail
    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=str(uuid.uuid4()),
    )
    existing_game = game_model.GameSession(
        id=game_id,
        title="Existing Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=str(uuid.uuid4()),
        channel_id=channel_id,
        host_id=str(uuid.uuid4()),
        status=game_model.GameStatus.SCHEDULED.value,
        thumbnail_data=b"existing_data",
        thumbnail_mime_type="image/png",
    )
    existing_game.host = user_model.User(id=existing_game.host_id, discord_id="999888777")
    existing_game.guild = guild_model.GuildConfiguration(
        id=existing_game.guild_id, guild_id="123456"
    )
    existing_game.channel = mock_channel
    existing_game.participants = []

    # Mock database queries
    mock_db.execute = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=existing_game)
    mock_db.execute.return_value.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Update data with empty bytes to signal removal
    update_data = game_schemas.GameUpdateRequest(
        title=None,
        description=None,
        signup_instructions=None,
        scheduled_at=None,
        where=None,
        max_players=None,
        reminder_minutes=None,
        expected_duration_minutes=None,
        status=None,
        notify_role_ids=None,
        participants=None,
        removed_participant_ids=None,
    )

    # Mock current user
    current_user = MagicMock()
    current_user.user.discord_id = "999888777"
    current_user.access_token = "test_token"

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=current_user,
            role_service=mock_role_service,
            thumbnail_data=b"",  # Empty bytes signals removal
            thumbnail_mime_type="",
        )

    # Verify thumbnail was removed
    assert existing_game.thumbnail_data is None
    assert existing_game.thumbnail_mime_type is None


async def test_update_game_preserve_existing_thumbnail(game_service, mock_db, mock_role_service):
    """Test that thumbnail is preserved when not provided in update."""
    # Create existing game with thumbnail
    game_id = str(uuid.uuid4())
    channel_id = str(uuid.uuid4())
    existing_thumbnail = b"existing_data"
    existing_mime = "image/png"

    mock_channel = channel_model.ChannelConfiguration(
        id=channel_id,
        channel_id="987654321",
        guild_id=str(uuid.uuid4()),
    )
    existing_game = game_model.GameSession(
        id=game_id,
        title="Existing Game",
        scheduled_at=datetime.datetime.now(datetime.UTC).replace(tzinfo=None),
        guild_id=str(uuid.uuid4()),
        channel_id=channel_id,
        host_id=str(uuid.uuid4()),
        status=game_model.GameStatus.SCHEDULED.value,
        thumbnail_data=existing_thumbnail,
        thumbnail_mime_type=existing_mime,
    )
    existing_game.host = user_model.User(id=existing_game.host_id, discord_id="999888777")
    existing_game.guild = guild_model.GuildConfiguration(
        id=existing_game.guild_id, guild_id="123456"
    )
    existing_game.channel = mock_channel
    existing_game.participants = []

    # Mock database queries
    mock_db.execute = AsyncMock()
    mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=existing_game)
    mock_db.execute.return_value.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=[]))
    )
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Update data without image parameters
    update_data = game_schemas.GameUpdateRequest(
        title="Updated Title",
        description=None,
        signup_instructions=None,
        scheduled_at=None,
        where=None,
        max_players=None,
        reminder_minutes=None,
        expected_duration_minutes=None,
        status=None,
        notify_role_ids=None,
        participants=None,
        removed_participant_ids=None,
    )

    # Mock current user
    current_user = MagicMock()
    current_user.user.discord_id = "999888777"
    current_user.access_token = "test_token"

    with patch("services.api.dependencies.permissions.can_manage_game", return_value=True):
        await game_service.update_game(
            game_id=game_id,
            update_data=update_data,
            current_user=current_user,
            role_service=mock_role_service,
            # No thumbnail_data/thumbnail_mime_type provided
        )

    # Verify thumbnail was preserved
    assert existing_game.thumbnail_data == existing_thumbnail
    assert existing_game.thumbnail_mime_type == existing_mime

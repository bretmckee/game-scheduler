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


"""Integration tests for guild sync and template API endpoints.

These tests verify the full stack integration of:
- Discord API interaction for fetching guilds and channels
- Guild and channel synchronization with database
- Template CRUD operations with permission checks
- Role-based template filtering
"""

import os
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from services.api.app import create_app


@pytest.fixture(scope="module")
def db_url():
    """Get database URL from environment."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://gamebot:dev_password_change_in_prod@postgres:5432/game_scheduler",
    )


@pytest.fixture(scope="module")
async def engine(db_url):
    """Create async database engine."""
    async_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Create a database session for testing."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def app():
    """Create FastAPI application."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_discord_guilds():
    """Mock Discord API guild responses."""
    return [
        {
            "id": "111222333",
            "name": "Test Guild 1",
            "icon": "icon_hash_1",
            "owner": False,
            "permissions": "2147483647",  # All permissions
        },
        {
            "id": "444555666",
            "name": "Test Guild 2",
            "icon": "icon_hash_2",
            "owner": True,
            "permissions": "8",  # MANAGE_GUILD permission
        },
    ]


@pytest.fixture
def mock_discord_channels():
    """Mock Discord API channel responses."""
    return [
        {
            "id": "777888999",
            "name": "general",
            "type": 0,  # TEXT_CHANNEL
            "position": 0,
        },
        {
            "id": "111000222",
            "name": "games",
            "type": 0,  # TEXT_CHANNEL
            "position": 1,
        },
    ]


@pytest.fixture
def mock_discord_roles():
    """Mock Discord API role responses."""
    return [
        {"id": "role_admin", "name": "Admin", "permissions": "8"},
        {"id": "role_player", "name": "Player", "permissions": "0"},
    ]


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user."""
    return Mock(
        user_id="user123",
        user=Mock(discord_id="discord_user_123"),
        access_token="test_access_token",
        session_token="test_session_token",
    )


class TestGuildSync:
    """Integration tests for guild synchronization endpoint."""

    @pytest.mark.asyncio
    async def test_guild_sync_creates_new_guilds_and_channels(
        self,
        client,
        db_session,
        mock_auth_user,
        mock_discord_guilds,
        mock_discord_channels,
    ):
        """Test that guild sync creates new guild configs, channels, and templates."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_user_guilds,
            patch(
                "services.api.auth.discord_client.DiscordClient.get_bot_guilds"
            ) as mock_get_bot_guilds,
            patch(
                "services.api.auth.discord_client.DiscordClient.get_guild_channels"
            ) as mock_get_guild_channels,
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_get_user_guilds.return_value = mock_discord_guilds
            mock_get_bot_guilds.return_value = mock_discord_guilds
            mock_get_guild_channels.return_value = mock_discord_channels

            response = await client.post("/guilds/sync")

            assert response.status_code == 200
            data = response.json()
            assert data["new_guilds"] == 2
            assert data["new_channels"] == 4  # 2 channels per guild

            # Verify guilds were created in database
            result = await db_session.execute(
                text("SELECT guild_id, bot_manager_role_ids FROM guild_configurations")
            )
            guilds = result.fetchall()
            assert len(guilds) == 2

            # Verify channels were created
            result = await db_session.execute(
                text("SELECT channel_id, guild_id FROM channel_configurations")
            )
            channels = result.fetchall()
            assert len(channels) == 4

            # Verify default templates were created
            result = await db_session.execute(
                text("SELECT id, guild_id, name, is_default FROM game_templates")
            )
            templates = result.fetchall()
            assert len(templates) >= 2  # At least one default per guild
            assert all(t[3] for t in templates)  # All should be default

    @pytest.mark.asyncio
    async def test_guild_sync_idempotent(
        self,
        client,
        db_session,
        mock_auth_user,
        mock_discord_guilds,
        mock_discord_channels,
    ):
        """Test that guild sync is idempotent and doesn't duplicate."""
        with (
            patch("services.api.auth.oauth2.get_user_guilds") as mock_get_user_guilds,
            patch(
                "services.api.auth.discord_client.DiscordClient.get_bot_guilds"
            ) as mock_get_bot_guilds,
            patch(
                "services.api.auth.discord_client.DiscordClient.get_guild_channels"
            ) as mock_get_guild_channels,
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_get_user_guilds.return_value = mock_discord_guilds
            mock_get_bot_guilds.return_value = mock_discord_guilds
            mock_get_guild_channels.return_value = mock_discord_channels

            # First sync
            response1 = await client.post("/guilds/sync")
            assert response1.status_code == 200
            response1.json()

            # Second sync
            response2 = await client.post("/guilds/sync")
            assert response2.status_code == 200
            data2 = response2.json()

            # Should not create duplicates
            assert data2["new_guilds"] == 0
            assert data2["new_channels"] == 0


class TestTemplateAPI:
    """Integration tests for template CRUD endpoints."""

    @pytest.fixture
    async def setup_guild_and_channel(self, db_session):
        """Create a guild and channel configuration for testing."""
        guild_id = str(uuid4())
        channel_id = str(uuid4())

        await db_session.execute(
            text(
                """
                INSERT INTO guild_configurations (guild_id, bot_manager_role_ids, require_host_role)
                VALUES (:guild_id, :roles, false)
            """
            ),
            {"guild_id": guild_id, "roles": ["role_admin"]},
        )

        await db_session.execute(
            text(
                """
                INSERT INTO channel_configurations (channel_id, guild_id, is_active)
                VALUES (:channel_id, :guild_id, true)
            """
            ),
            {"channel_id": channel_id, "guild_id": guild_id},
        )

        await db_session.commit()

        return {"guild_id": guild_id, "channel_id": channel_id}

    @pytest.mark.asyncio
    async def test_create_template_success(
        self, client, db_session, mock_auth_user, setup_guild_and_channel
    ):
        """Test creating a template with bot manager permissions."""
        guild_id = setup_guild_and_channel["guild_id"]
        channel_id = setup_guild_and_channel["channel_id"]

        template_data = {
            "name": "Weekly D&D",
            "description": "Weekly Dungeons & Dragons session",
            "channel_id": channel_id,
            "order": 1,
            "is_default": False,
            "notify_role_ids": ["role_player"],
            "allowed_player_role_ids": None,
            "allowed_host_role_ids": ["role_admin"],
            "max_players": 6,
            "expected_duration_minutes": 240,
            "reminder_minutes": [60, 15],
            "where": "Roll20",
            "signup_instructions": "React to join!",
        }

        with (
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
            patch(
                "services.api.auth.roles.RoleService.check_bot_manager_permission"
            ) as mock_check_permission,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_check_permission.return_value = True

            response = await client.post(f"/guilds/{guild_id}/templates", json=template_data)

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Weekly D&D"
            assert data["guild_id"] == guild_id
            assert data["channel"]["channel_id"] == channel_id
            assert data["max_players"] == 6

            # Verify in database
            result = await db_session.execute(
                text("SELECT name, max_players FROM game_templates WHERE guild_id = :guild_id"),
                {"guild_id": guild_id},
            )
            template = result.fetchone()
            assert template[0] == "Weekly D&D"
            assert template[1] == 6

    @pytest.mark.asyncio
    async def test_list_templates_role_filtering(
        self, client, db_session, mock_auth_user, setup_guild_and_channel
    ):
        """Test that templates are filtered by user roles."""
        guild_id = setup_guild_and_channel["guild_id"]
        channel_id = setup_guild_and_channel["channel_id"]

        # Create templates with different role restrictions
        await db_session.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, "order", is_default, allowed_host_role_ids)
                VALUES
                (:id1, :guild_id, :channel_id, 'Public Template', 1, false, NULL),
                (:id2, :guild_id, :channel_id, 'Admin Only', 2, false, :admin_roles)
            """
            ),
            {
                "id1": str(uuid4()),
                "id2": str(uuid4()),
                "guild_id": guild_id,
                "channel_id": channel_id,
                "admin_roles": ["role_admin"],
            },
        )
        await db_session.commit()

        with (
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
            patch("services.api.auth.roles.RoleService.has_permissions") as mock_has_permissions,
            patch(
                "services.api.auth.discord_client.DiscordClient.get_user_guild_member"
            ) as mock_get_member,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_has_permissions.return_value = False  # Not admin
            mock_get_member.return_value = {"roles": ["role_player"]}

            response = await client.get(f"/guilds/{guild_id}/templates")

            assert response.status_code == 200
            data = response.json()
            # Should only see public template
            assert len(data) == 1
            assert data[0]["name"] == "Public Template"

    @pytest.mark.asyncio
    async def test_delete_default_template_fails(
        self, client, db_session, mock_auth_user, setup_guild_and_channel
    ):
        """Test that default templates cannot be deleted."""
        guild_id = setup_guild_and_channel["guild_id"]
        channel_id = setup_guild_and_channel["channel_id"]

        template_id = str(uuid4())
        await db_session.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, "order", is_default)
                VALUES (:id, :guild_id, :channel_id, 'Default Template', 1, true)
            """
            ),
            {"id": template_id, "guild_id": guild_id, "channel_id": channel_id},
        )
        await db_session.commit()

        with (
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
            patch(
                "services.api.auth.roles.RoleService.check_bot_manager_permission"
            ) as mock_check_permission,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_check_permission.return_value = True

            response = await client.delete(f"/templates/{template_id}")

            assert response.status_code == 400
            assert "Cannot delete the default template" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_default_template(
        self, client, db_session, mock_auth_user, setup_guild_and_channel
    ):
        """Test setting a template as default unsets others."""
        guild_id = setup_guild_and_channel["guild_id"]
        channel_id = setup_guild_and_channel["channel_id"]

        template1_id = str(uuid4())
        template2_id = str(uuid4())

        await db_session.execute(
            text(
                """
                INSERT INTO game_templates
                (id, guild_id, channel_id, name, "order", is_default)
                VALUES
                (:id1, :guild_id, :channel_id, 'Template 1', 1, true),
                (:id2, :guild_id, :channel_id, 'Template 2', 2, false)
            """
            ),
            {
                "id1": template1_id,
                "id2": template2_id,
                "guild_id": guild_id,
                "channel_id": channel_id,
            },
        )
        await db_session.commit()

        with (
            patch("services.api.dependencies.auth.get_current_user") as mock_get_current_user,
            patch(
                "services.api.auth.roles.RoleService.check_bot_manager_permission"
            ) as mock_check_permission,
        ):
            mock_get_current_user.return_value = mock_auth_user
            mock_check_permission.return_value = True

            response = await client.post(f"/templates/{template2_id}/set-default")

            assert response.status_code == 200

            # Verify only template2 is default
            result = await db_session.execute(
                text("SELECT id, is_default FROM game_templates WHERE guild_id = :guild_id"),
                {"guild_id": guild_id},
            )
            templates = result.fetchall()
            defaults = [t for t in templates if t[1]]
            assert len(defaults) == 1
            assert defaults[0][0] == template2_id

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


"""
pytest configuration for E2E tests.

Provides fixtures for Discord credentials, database sessions,
and HTTP clients needed by E2E tests.
"""

import os

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def discord_token():
    """Provide Discord bot token from environment."""
    return os.environ["DISCORD_TOKEN"]


@pytest.fixture(scope="session")
def discord_guild_id():
    """Provide test Discord guild ID from environment."""
    return os.environ["DISCORD_GUILD_ID"]


@pytest.fixture(scope="session")
def discord_channel_id():
    """Provide test Discord channel ID from environment."""
    return os.environ["DISCORD_CHANNEL_ID"]


@pytest.fixture(scope="session")
def discord_user_id():
    """Provide test Discord user ID from environment."""
    return os.environ["DISCORD_USER_ID"]


@pytest.fixture(scope="session")
def database_url():
    """Construct database URL from environment variables."""
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ['POSTGRES_HOST']}:{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


@pytest.fixture(scope="session")
def db_engine(database_url):
    """Create database engine for E2E tests."""
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Provide database session for individual tests."""
    session_factory = sessionmaker(bind=db_engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def api_base_url():
    """Provide API base URL for E2E tests."""
    return "http://api:8000"


@pytest.fixture(scope="function")
def http_client(api_base_url):
    """Provide HTTP client for API requests."""
    client = httpx.Client(base_url=api_base_url, timeout=10.0)
    try:
        yield client
    finally:
        client.close()


@pytest.fixture
async def discord_helper(discord_token):
    """Create and connect Discord test helper."""
    from tests.e2e.helpers.discord import DiscordTestHelper

    helper = DiscordTestHelper(discord_token)
    await helper.connect()
    yield helper
    await helper.disconnect()

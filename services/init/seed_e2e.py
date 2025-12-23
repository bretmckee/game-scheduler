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
E2E test data seeding.

Seeds the database with test guild, channel, user, and template records required for E2E tests.
Only runs when TEST_ENVIRONMENT=true.
"""

import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from shared.database import get_sync_db_session

logger = logging.getLogger(__name__)


def seed_e2e_data() -> bool:
    """
    Seed database with E2E test configuration.

    Creates:
    - Test guild configuration
    - Test channel configuration
    - Test host user
    - Default game template

    Returns:
        True if seeding succeeded, False otherwise
    """
    if os.getenv("TEST_ENVIRONMENT") != "true":
        logger.info("Skipping E2E seed - TEST_ENVIRONMENT not set to 'true'")
        return True

    discord_guild_id = os.getenv("DISCORD_GUILD_ID")
    discord_channel_id = os.getenv("DISCORD_CHANNEL_ID")
    discord_user_id = os.getenv("DISCORD_USER_ID")
    admin_bot_token = os.getenv("DISCORD_ADMIN_BOT_TOKEN")

    if not all([discord_guild_id, discord_channel_id, discord_user_id, admin_bot_token]):
        logger.warning("Skipping E2E seed - missing DISCORD_* environment variables")
        return True

    try:
        # Extract bot Discord ID from token
        from shared.utils.discord_tokens import extract_bot_discord_id

        bot_discord_id = extract_bot_discord_id(admin_bot_token)
        with get_sync_db_session() as session:
            now = datetime.now(UTC).replace(tzinfo=None)

            # Check if guild already exists
            result = session.execute(
                text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
                {"guild_id": discord_guild_id},
            )
            existing_guild = result.fetchone()

            if existing_guild:
                logger.info(f"E2E test guild {discord_guild_id} already exists, skipping seed")
                return True

            guild_id = str(uuid4())
            channel_id = str(uuid4())
            user_id = str(uuid4())
            bot_user_id = str(uuid4())
            template_id = str(uuid4())

            logger.info(f"Seeding E2E test data for guild {discord_guild_id}")
            logger.info(f"Seeding bot user with Discord ID: {bot_discord_id}")

            session.execute(
                text(
                    "INSERT INTO guild_configurations "
                    "(id, guild_id, created_at, updated_at) "
                    "VALUES (:id, :guild_id, :created_at, :updated_at)"
                ),
                {
                    "id": guild_id,
                    "guild_id": discord_guild_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            session.execute(
                text(
                    "INSERT INTO channel_configurations "
                    "(id, channel_id, guild_id, created_at, updated_at) "
                    "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
                ),
                {
                    "id": channel_id,
                    "channel_id": discord_channel_id,
                    "guild_id": guild_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            session.execute(
                text(
                    "INSERT INTO game_templates "
                    "(id, guild_id, channel_id, name, is_default, "
                    "created_at, updated_at) "
                    "VALUES (:id, :guild_id, :channel_id, :name, :is_default, "
                    ":created_at, :updated_at)"
                ),
                {
                    "id": template_id,
                    "guild_id": guild_id,
                    "channel_id": channel_id,
                    "name": "Default E2E Template",
                    "is_default": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            session.execute(
                text(
                    "INSERT INTO users (id, discord_id, created_at, updated_at) "
                    "VALUES (:id, :discord_id, :created_at, :updated_at)"
                ),
                {
                    "id": user_id,
                    "discord_id": discord_user_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            session.execute(
                text(
                    "INSERT INTO users (id, discord_id, created_at, updated_at) "
                    "VALUES (:id, :discord_id, :created_at, :updated_at)"
                ),
                {
                    "id": bot_user_id,
                    "discord_id": bot_discord_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )

            logger.info("E2E test data seeded successfully (guild, channel, users, template)")
            session.commit()
            return True

    except Exception as e:
        logger.error(f"Failed to seed E2E test data: {e}")
        return False

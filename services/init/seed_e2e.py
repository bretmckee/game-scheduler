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
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.database import get_sync_db_session
from shared.utils.discord_tokens import extract_bot_discord_id

logger = logging.getLogger(__name__)


@dataclass
class E2EConfig:
    """E2E test environment configuration."""

    guild_a_id: str
    channel_a_id: str
    user_id: str
    bot_token: str
    guild_b_id: str
    channel_b_id: str
    user_b_id: str


@dataclass
class GuildConfig:
    """Configuration for seeding a single guild."""

    guild_id: str
    channel_id: str
    user_id: str
    guild_name: str


def _validate_e2e_config() -> E2EConfig | None:
    """Validate and load E2E test configuration from environment."""
    if os.getenv("TEST_ENVIRONMENT") != "true":
        logger.info("Skipping E2E seed - TEST_ENVIRONMENT not set to 'true'")
        return None

    config_dict = {
        "guild_a_id": os.getenv("DISCORD_GUILD_A_ID"),
        "channel_a_id": os.getenv("DISCORD_GUILD_A_CHANNEL_ID"),
        "user_id": os.getenv("DISCORD_USER_ID"),
        "bot_token": os.getenv("DISCORD_ADMIN_BOT_A_TOKEN"),
        "guild_b_id": os.getenv("DISCORD_GUILD_B_ID"),
        "channel_b_id": os.getenv("DISCORD_GUILD_B_CHANNEL_ID"),
        "user_b_id": os.getenv("DISCORD_ADMIN_BOT_B_CLIENT_ID"),
    }

    if not all(config_dict.values()):
        logger.warning("Skipping E2E seed - missing DISCORD_* environment variables")
        return None

    return E2EConfig(**config_dict)


def _guild_exists(session: Session, guild_id: str) -> bool:
    """Check if guild already exists in database."""
    result = session.execute(
        text("SELECT id FROM guild_configurations WHERE guild_id = :guild_id"),
        {"guild_id": guild_id},
    )
    return result.fetchone() is not None


def _create_guild_entities(
    session: Session, guild_config: GuildConfig, bot_id: str | None = None
) -> None:
    """Create guild, channel, template, and user entities."""
    now = datetime.now(UTC).replace(tzinfo=None)
    guild_id = str(uuid4())

    session.execute(
        text(
            "INSERT INTO guild_configurations "
            "(id, guild_id, created_at, updated_at) "
            "VALUES (:id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": guild_id,
            "guild_id": guild_config.guild_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    channel_config_id = str(uuid4())
    session.execute(
        text(
            "INSERT INTO channel_configurations "
            "(id, channel_id, guild_id, created_at, updated_at) "
            "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
        ),
        {
            "id": channel_config_id,
            "channel_id": guild_config.channel_id,
            "guild_id": guild_id,
            "created_at": now,
            "updated_at": now,
        },
    )

    session.execute(
        text(
            "INSERT INTO game_templates "
            "(id, guild_id, channel_id, name, is_default, created_at, updated_at) "
            "VALUES (:id, :guild_id, :channel_id, :name, :is_default, :created_at, :updated_at)"
        ),
        {
            "id": str(uuid4()),
            "guild_id": guild_id,
            "channel_id": channel_config_id,
            "name": f"Default E2E Template ({guild_config.guild_name})",
            "is_default": True,
            "created_at": now,
            "updated_at": now,
        },
    )

    for user_id in [guild_config.user_id] + ([bot_id] if bot_id else []):
        session.execute(
            text(
                "INSERT INTO users (id, discord_id, created_at, updated_at) "
                "VALUES (:id, :discord_id, :created_at, :updated_at) "
                "ON CONFLICT (discord_id) DO NOTHING"
            ),
            {
                "id": str(uuid4()),
                "discord_id": user_id,
                "created_at": now,
                "updated_at": now,
            },
        )

    logger.info("Created guild entities for %s", guild_config.guild_name)


def seed_e2e_data() -> bool:
    """
    Seed database with E2E test configuration.

    Creates:
    - Test guild configuration (Guild A)
    - Test channel configuration (Channel A)
    - Test host user (User A)
    - Default game template for Guild A
    - Guild B, Channel B, User B for cross-guild isolation testing (required)

    Returns:
        True if seeding succeeded, False otherwise
    """
    config = _validate_e2e_config()
    if not config:
        return True

    bot_id = extract_bot_discord_id(config.bot_token)
    logger.info("Extracted bot Discord ID: %s", bot_id)

    try:
        session: Session
        with get_sync_db_session() as session:
            if _guild_exists(session, config.guild_a_id):
                logger.info("E2E test guild %s already exists, skipping seed", config.guild_a_id)
                return True

            guild_a_config = GuildConfig(
                guild_id=config.guild_a_id,
                channel_id=config.channel_a_id,
                user_id=config.user_id,
                guild_name="Guild A",
            )
            _create_guild_entities(session, guild_a_config, bot_id)
            logger.info("E2E test data seeded successfully (guild A, channel A, users, template)")

            logger.info(
                "Seeding Guild B for cross-guild isolation testing: %s",
                config.guild_b_id,
            )

            if _guild_exists(session, config.guild_b_id):
                logger.info("Guild B %s already exists, skipping seed", config.guild_b_id)
            else:
                guild_b_config = GuildConfig(
                    guild_id=config.guild_b_id,
                    channel_id=config.channel_b_id,
                    user_id=config.user_b_id,
                    guild_name="Guild B",
                )
                _create_guild_entities(session, guild_b_config)
                logger.info("Guild B seeded successfully (guild B, channel B, user B, template)")

            session.commit()
            return True

    except Exception as e:
        logger.error("Failed to seed E2E test data: %s", e)
        return False

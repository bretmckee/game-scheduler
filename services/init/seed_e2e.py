# Copyright 2025-2026 Bret McKee
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
    archive_channel_id: str | None
    user_id: str
    bot_token: str
    guild_b_id: str
    channel_b_id: str
    user_b_id: str
    main_bot_token: str
    player_a_client_id: str | None


@dataclass
class GuildConfig:
    """Configuration for seeding a single guild."""

    guild_id: str
    channel_id: str
    user_id: str
    guild_name: str
    archive_channel_id: str | None = None


def _validate_e2e_config() -> E2EConfig | None:
    """Validate and load E2E test configuration from environment."""
    if os.getenv("TEST_ENVIRONMENT") != "true":
        logger.info("Skipping E2E seed - TEST_ENVIRONMENT not set to 'true'")
        return None

    required = {
        "guild_a_id": os.getenv("DISCORD_GUILD_A_ID"),
        "channel_a_id": os.getenv("DISCORD_GUILD_A_CHANNEL_ID"),
        "user_id": os.getenv("DISCORD_USER_ID"),
        "bot_token": os.getenv("DISCORD_ADMIN_BOT_A_TOKEN"),
        "guild_b_id": os.getenv("DISCORD_GUILD_B_ID"),
        "channel_b_id": os.getenv("DISCORD_GUILD_B_CHANNEL_ID"),
        "user_b_id": os.getenv("DISCORD_ADMIN_BOT_B_CLIENT_ID"),
        "main_bot_token": os.getenv("DISCORD_BOT_TOKEN"),
    }

    if not all(required.values()):
        logger.warning("Skipping E2E seed - missing DISCORD_* environment variables")
        return None

    return E2EConfig(
        **required,
        archive_channel_id=os.getenv("DISCORD_ARCHIVE_CHANNEL_ID"),
        player_a_client_id=os.getenv("DISCORD_PLAYER_A_CLIENT_ID"),
    )


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

    if (
        guild_config.archive_channel_id is not None
        and guild_config.archive_channel_id != guild_config.channel_id
    ):
        archive_channel_config_id = str(uuid4())
        session.execute(
            text(
                "INSERT INTO channel_configurations "
                "(id, channel_id, guild_id, created_at, updated_at) "
                "VALUES (:id, :channel_id, :guild_id, :created_at, :updated_at)"
            ),
            {
                "id": archive_channel_config_id,
                "channel_id": guild_config.archive_channel_id,
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

    logger.debug(
        "Created guild entities for %s: guild_db_id=%s channel_db_id=%s",
        guild_config.guild_name,
        guild_id,
        channel_config_id,
    )


def _seed_standalone_users(session: Session, discord_ids: list[str]) -> None:
    """
    Seed user records for IDs not covered by guild entity seeding.

    Uses ON CONFLICT DO NOTHING so this is safe to call on an already-seeded DB.

    Args:
        session: Database session
        discord_ids: Discord snowflake IDs to ensure exist in the users table
    """
    logger.debug("_seed_standalone_users: inserting %d user(s): %s", len(discord_ids), discord_ids)
    now = datetime.now(UTC).replace(tzinfo=None)
    for discord_id in discord_ids:
        logger.debug("  inserting user discord_id=%s", discord_id)
        session.execute(
            text(
                "INSERT INTO users (id, discord_id, created_at, updated_at) "
                "VALUES (:id, :discord_id, :created_at, :updated_at) "
                "ON CONFLICT (discord_id) DO NOTHING"
            ),
            {
                "id": str(uuid4()),
                "discord_id": discord_id,
                "created_at": now,
                "updated_at": now,
            },
        )
    logger.debug("_seed_standalone_users: done")


def seed_e2e_data() -> bool:
    """
    Seed database with E2E test configuration.

    Creates:
    - Test guild configuration (Guild A)
    - Test channel configuration (Channel A)
    - Test host user (User A)
    - Default game template for Guild A
    - Guild B, Channel B, User B for cross-guild isolation testing (required)
    - Main notification bot user record
    - Player A user record (if DISCORD_PLAYER_A_CLIENT_ID is set)

    Returns:
        True if seeding succeeded, False otherwise
    """
    logger.debug("seed_e2e_data: starting")
    config = _validate_e2e_config()
    if not config:
        return True

    logger.debug(
        "seed_e2e_data: config loaded guild_a=%s guild_b=%s user_id=%s",
        config.guild_a_id,
        config.guild_b_id,
        config.user_id,
    )

    bot_id = extract_bot_discord_id(config.bot_token)
    logger.debug("seed_e2e_data: bot_a discord_id=%s", bot_id)

    try:
        session: Session
        with get_sync_db_session() as session:
            main_bot_id = extract_bot_discord_id(config.main_bot_token)
            standalone_ids = [main_bot_id]
            if config.player_a_client_id:
                standalone_ids.append(config.player_a_client_id)
            _seed_standalone_users(session, standalone_ids)
            logger.info("Seeded standalone users: %s", standalone_ids)

            if _guild_exists(session, config.guild_a_id):
                session.commit()
                logger.info("E2E test guild %s already exists, skipping seed", config.guild_a_id)
                return True

            guild_a_config = GuildConfig(
                guild_id=config.guild_a_id,
                channel_id=config.channel_a_id,
                archive_channel_id=config.archive_channel_id,
                user_id=config.user_id,
                guild_name="Guild A",
            )
            _create_guild_entities(session, guild_a_config, bot_id)
            logger.info(
                "Guild A seeded: guild=%s channel=%s user=%s bot=%s",
                config.guild_a_id,
                config.channel_a_id,
                config.user_id,
                bot_id,
            )

            logger.debug("seed_e2e_data: checking Guild B %s", config.guild_b_id)

            if _guild_exists(session, config.guild_b_id):
                logger.info("Guild B %s already exists, skipping seed", config.guild_b_id)
            else:
                guild_b_config = GuildConfig(
                    guild_id=config.guild_b_id,
                    channel_id=config.channel_b_id,
                    archive_channel_id=None,
                    user_id=config.user_b_id,
                    guild_name="Guild B",
                )
                _create_guild_entities(session, guild_b_config)
                logger.info(
                    "Guild B seeded: guild=%s channel=%s user=%s",
                    config.guild_b_id,
                    config.channel_b_id,
                    config.user_b_id,
                )

            logger.debug("seed_e2e_data: committing")
            session.commit()
            logger.info("seed_e2e_data: committed, all done")
            return True

    except Exception as e:
        logger.error("Failed to seed E2E test data: %s", e)
        return False

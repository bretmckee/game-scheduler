#!/usr/bin/env python3
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
Database user initialization for RLS enforcement.

Creates two separate database users with distinct privileges:
1. gamebot_admin (superuser) - For migrations and database administration
2. gamebot_app (non-superuser) - For application runtime with RLS enforcement

This separation is CRITICAL for Row-Level Security (RLS) to function correctly.
PostgreSQL RLS policies only enforce on non-superuser roles.
"""

import logging
import os

import psycopg2
from opentelemetry import trace
from psycopg2 import sql

logger = logging.getLogger(__name__)


def _create_admin_user(cursor, admin_user: str, admin_password: str) -> None:
    """
    Create admin superuser for migrations and database administration.

    Args:
        cursor: Database cursor for executing SQL
        admin_user: Username for admin account
        admin_password: Password for admin account
    """
    logger.info("Creating admin user '%s' (superuser)...", admin_user)
    cursor.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = %s) THEN
                CREATE USER {admin_user} WITH PASSWORD %s SUPERUSER;
                COMMENT ON ROLE {admin_user} IS
                    'Superuser for Alembic migrations and database administration';
                RAISE NOTICE 'Created admin user: {admin_user}';
            ELSE
                RAISE NOTICE 'Admin user already exists: {admin_user}';
            END IF;
        END
        $$;
        """,
        (admin_user, admin_password),
    )
    logger.info("✓ Admin user '%s' ready", admin_user)


def _create_app_user(cursor, app_user: str, app_password: str) -> None:
    """
    Create non-privileged application user with RLS enforcement.

    Args:
        cursor: Database cursor for executing SQL
        app_user: Username for application account
        app_password: Password for application account
    """
    logger.info("Creating application user '%s' (non-superuser for RLS)...", app_user)
    cursor.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = %s) THEN
                CREATE USER {app_user} WITH PASSWORD %s LOGIN;
                COMMENT ON ROLE {app_user} IS
                    'Non-privileged user for application runtime (RLS enforced)';
                RAISE NOTICE 'Created app user: {app_user}';
            ELSE
                RAISE NOTICE 'App user already exists: {app_user}';
            END IF;
        END
        $$;
        """,
        (app_user, app_password),
    )
    logger.info("✓ Application user '%s' ready", app_user)


def _grant_permissions(
    cursor, target_user: str, postgres_user: str, admin_user: str, postgres_db: str
) -> None:
    """
    Grant comprehensive database permissions to target user.

    Args:
        cursor: Database cursor for executing SQL
        target_user: User to grant permissions to
        postgres_user: PostgreSQL superuser name
        admin_user: Admin user name for default privileges
        postgres_db: Database name
    """
    logger.info("Granting permissions to '%s'...", target_user)
    cursor.execute(
        sql.SQL(
            """
        GRANT CONNECT ON DATABASE {postgres_db} TO {target_user};
        GRANT USAGE, CREATE ON SCHEMA public TO {target_user};
        GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
            ON ALL TABLES IN SCHEMA public TO {target_user};
        GRANT USAGE, SELECT, UPDATE
            ON ALL SEQUENCES IN SCHEMA public TO {target_user};
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {target_user};

        -- Set default privileges for tables created by postgres superuser
        ALTER DEFAULT PRIVILEGES FOR ROLE {postgres_user} IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
            ON TABLES TO {target_user};
        ALTER DEFAULT PRIVILEGES FOR ROLE {postgres_user} IN SCHEMA public
            GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {target_user};
        ALTER DEFAULT PRIVILEGES FOR ROLE {postgres_user} IN SCHEMA public
            GRANT EXECUTE ON FUNCTIONS TO {target_user};

        -- Set default privileges for tables created by admin user (migrations)
        ALTER DEFAULT PRIVILEGES FOR ROLE {admin_user} IN SCHEMA public
            GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
            ON TABLES TO {target_user};
        ALTER DEFAULT PRIVILEGES FOR ROLE {admin_user} IN SCHEMA public
            GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {target_user};
        ALTER DEFAULT PRIVILEGES FOR ROLE {admin_user} IN SCHEMA public
            GRANT EXECUTE ON FUNCTIONS TO {target_user};
        """
        ).format(
            postgres_db=sql.Identifier(postgres_db),
            target_user=sql.Identifier(target_user),
            postgres_user=sql.Identifier(postgres_user),
            admin_user=sql.Identifier(admin_user),
        )
    )
    logger.info("✓ Permissions granted to '%s'", target_user)


def _create_bot_user(cursor, bot_user: str, bot_password: str) -> None:
    """
    Create bot user with BYPASSRLS for bot and daemon services.

    Args:
        cursor: Database cursor for executing SQL
        bot_user: Username for bot account
        bot_password: Password for bot account
    """
    logger.info("Creating bot user '%s' (BYPASSRLS for bot/daemon services)...", bot_user)
    cursor.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = %s) THEN
                CREATE USER {bot_user} WITH PASSWORD %s LOGIN BYPASSRLS;
                COMMENT ON ROLE {bot_user} IS
                    'Bot/daemon user - bypasses RLS (all guilds by design)';
                RAISE NOTICE 'Created bot user: {bot_user}';
            ELSE
                RAISE NOTICE 'Bot user already exists: {bot_user}';
            END IF;
        END
        $$;
        """,
        (bot_user, bot_password),
    )
    logger.info("✓ Bot user '%s' ready", bot_user)


def create_database_users() -> None:
    """
    Create database users with appropriate privileges for RLS enforcement.

    Creates two users:
    - gamebot_admin: Superuser for migrations and DDL operations
    - gamebot_app: Non-superuser for application runtime (RLS enforced)

    Raises:
        psycopg2.Error: If database connection or user creation fails
    """
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("init.create_database_users"):
        postgres_user = os.getenv("POSTGRES_USER", "postgres")
        postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        postgres_db = os.getenv("POSTGRES_DB", "game_scheduler")
        postgres_host = os.getenv("POSTGRES_HOST", "postgres")
        postgres_port = os.getenv("POSTGRES_PORT", "5432")

        admin_user = os.getenv("POSTGRES_ADMIN_USER", "gamebot_admin")
        admin_password = os.getenv("POSTGRES_ADMIN_PASSWORD")
        app_user = os.getenv("POSTGRES_APP_USER", "gamebot_app")
        app_password = os.getenv("POSTGRES_APP_PASSWORD")

        if not admin_password:
            logger.warning("POSTGRES_ADMIN_PASSWORD not set, skipping database user creation")
            return

        if not app_password:
            logger.warning("POSTGRES_APP_PASSWORD not set, skipping database user creation")
            return

        logger.info("Connecting to PostgreSQL as superuser to create application users...")

        conn = None
        try:
            conn = psycopg2.connect(
                host=postgres_host,
                port=postgres_port,
                user=postgres_user,
                password=postgres_password,
                dbname=postgres_db,
            )
            conn.autocommit = True

            with conn.cursor() as cursor:
                _create_admin_user(cursor, admin_user, admin_password)
                _create_app_user(cursor, app_user, app_password)
                _grant_permissions(cursor, app_user, postgres_user, admin_user, postgres_db)

                bot_user = os.getenv("POSTGRES_BOT_USER", "gamebot_bot")
                bot_password = os.getenv("POSTGRES_BOT_PASSWORD")

                if bot_password:
                    _create_bot_user(cursor, bot_user, bot_password)
                    _grant_permissions(cursor, bot_user, postgres_user, admin_user, postgres_db)
                    logger.info("Database users configured successfully")
                    logger.info("  - Admin user (future use): %s", admin_user)
                    logger.info("  - App user (API with RLS): %s", app_user)
                    logger.info("  - Bot user (bot/daemons, bypasses RLS): %s", bot_user)
                else:
                    logger.warning("POSTGRES_BOT_PASSWORD not set, skipping bot user creation")
                    logger.info("Database users configured successfully")
                    logger.info("  - Admin user (future use): %s", admin_user)
                    logger.info("  - App user (API with RLS): %s", app_user)

        except psycopg2.Error as e:
            logger.error("Failed to create database users: %s", e)
            raise
        finally:
            if conn:
                conn.close()

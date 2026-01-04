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

logger = logging.getLogger(__name__)


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
                logger.info(f"Creating admin user '{admin_user}' (superuser)...")
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
                logger.info(f"✓ Admin user '{admin_user}' ready")

                logger.info(f"Creating application user '{app_user}' (non-superuser for RLS)...")
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
                logger.info(f"✓ Application user '{app_user}' ready")

                logger.info(f"Granting permissions to '{app_user}'...")
                cursor.execute(
                    f"""
                    GRANT CONNECT ON DATABASE {postgres_db} TO {app_user};
                    GRANT USAGE, CREATE ON SCHEMA public TO {app_user};
                    GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
                        ON ALL TABLES IN SCHEMA public TO {app_user};
                    GRANT USAGE, SELECT, UPDATE
                        ON ALL SEQUENCES IN SCHEMA public TO {app_user};
                    GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {app_user};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
                        ON TABLES TO {app_user};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {app_user};
                    ALTER DEFAULT PRIVILEGES IN SCHEMA public
                        GRANT EXECUTE ON FUNCTIONS TO {app_user};
                    """
                )
                logger.info(f"✓ Permissions granted to '{app_user}'")

                bot_user = os.getenv("POSTGRES_BOT_USER", "gamebot_bot")
                bot_password = os.getenv("POSTGRES_BOT_PASSWORD")

                if not bot_password:
                    logger.warning("POSTGRES_BOT_PASSWORD not set, skipping bot user creation")
                else:
                    logger.info(
                        f"Creating bot user '{bot_user}' (BYPASSRLS for bot/daemon services)..."
                    )
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
                    logger.info(f"✓ Bot user '{bot_user}' ready")

                    logger.info(f"Granting permissions to '{bot_user}'...")
                    cursor.execute(
                        f"""
                        GRANT CONNECT ON DATABASE {postgres_db} TO {bot_user};
                        GRANT USAGE ON SCHEMA public TO {bot_user};
                        GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
                            ON ALL TABLES IN SCHEMA public TO {bot_user};
                        GRANT USAGE, SELECT, UPDATE
                            ON ALL SEQUENCES IN SCHEMA public TO {bot_user};
                        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {bot_user};
                        ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
                            GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
                            ON TABLES TO {bot_user};
                        ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
                            GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {bot_user};
                        ALTER DEFAULT PRIVILEGES FOR ROLE {app_user} IN SCHEMA public
                            GRANT EXECUTE ON FUNCTIONS TO {bot_user};
                        """
                    )
                    logger.info(f"✓ Permissions granted to '{bot_user}'")

                logger.info("Database users configured successfully")
                logger.info(f"  - Admin user (future use): {admin_user}")
                logger.info(f"  - App user (API with RLS): {app_user}")
                if bot_password:
                    logger.info(f"  - Bot user (bot/daemons, bypasses RLS): {bot_user}")

        except psycopg2.Error as e:
            logger.error(f"Failed to create database users: {e}")
            raise
        finally:
            if conn:
                conn.close()

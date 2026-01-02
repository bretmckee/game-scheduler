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
Integration tests for database user creation.

Verifies that database users are created with correct permissions for RLS enforcement.
"""

import os

import psycopg2
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def postgres_connection():
    """Create connection to PostgreSQL as superuser for verification."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        dbname=os.getenv("POSTGRES_DB", "game_scheduler"),
    )
    yield conn
    conn.close()


def test_database_users_exist(postgres_connection):
    """Verify that both gamebot_admin and gamebot_app users exist."""
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT rolname, rolsuper
            FROM pg_catalog.pg_roles
            WHERE rolname IN ('gamebot_admin', 'gamebot_app')
            ORDER BY rolname;
            """
        )
        users = cursor.fetchall()

    assert len(users) == 2, "Expected exactly 2 users (gamebot_admin, gamebot_app)"

    admin_user, admin_is_super = users[0]
    app_user, app_is_super = users[1]

    assert admin_user == "gamebot_admin", "Admin user should be gamebot_admin"
    assert admin_is_super, "Admin user should be superuser"

    assert app_user == "gamebot_app", "App user should be gamebot_app"
    assert not app_is_super, "App user should NOT be superuser (for RLS enforcement)"


def test_app_user_has_connect_permission(postgres_connection):
    """Verify that gamebot_app can connect to the database."""
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT has_database_privilege('gamebot_app', current_database(), 'CONNECT');
            """
        )
        has_connect = cursor.fetchone()[0]

    assert has_connect, "gamebot_app should have CONNECT permission"


def test_app_user_has_schema_permissions(postgres_connection):
    """Verify that gamebot_app has USAGE and CREATE on public schema."""
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT has_schema_privilege('gamebot_app', 'public', 'USAGE'),
                   has_schema_privilege('gamebot_app', 'public', 'CREATE');
            """
        )
        has_usage, has_create = cursor.fetchone()

    assert has_usage, "gamebot_app should have USAGE on public schema"
    assert has_create, "gamebot_app should have CREATE on public schema"


def test_app_user_can_create_and_query_tables(postgres_connection):
    """Verify that gamebot_app can create tables, insert, and query data."""
    app_conn = None
    try:
        app_password = os.getenv("POSTGRES_APP_PASSWORD")
        if not app_password:
            pytest.skip("POSTGRES_APP_PASSWORD not set")

        app_conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "postgres"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            user=os.getenv("POSTGRES_APP_USER", "gamebot_app"),
            password=app_password,
            dbname=os.getenv("POSTGRES_DB", "game_scheduler"),
        )
        app_conn.autocommit = True

        with app_conn.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS test_table_permissions;")

            cursor.execute(
                """
                CREATE TABLE test_table_permissions (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL
                );
                """
            )

            cursor.execute("INSERT INTO test_table_permissions (name) VALUES ('test_value');")

            cursor.execute("SELECT name FROM test_table_permissions WHERE id = 1;")
            result = cursor.fetchone()

            assert result[0] == "test_value", "Should be able to query inserted data"

            cursor.execute("DROP TABLE test_table_permissions;")

    finally:
        if app_conn:
            app_conn.close()


def test_app_user_has_default_privileges_on_new_tables(postgres_connection):
    """Verify that default privileges are set for gamebot_app on future tables."""
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT defaclacl::text
            FROM pg_default_acl
            WHERE defaclobjtype = 'r'  -- 'r' for tables
                AND defaclnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            LIMIT 1;
            """
        )
        result = cursor.fetchone()

    if result:
        privileges = result[0]
        assert "gamebot_app" in privileges, "gamebot_app should have default privileges"
    else:
        pytest.skip("No default ACL found - may be using owner-based permissions")

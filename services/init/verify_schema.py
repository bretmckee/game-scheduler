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


"""Database schema verification after migrations."""

import logging
import os

import psycopg2
from opentelemetry import trace
from psycopg2 import sql

logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "users",
    "guild_configurations",
    "channel_configurations",
    "game_sessions",
    "game_participants",
    "notification_schedule",
    "game_status_schedule",
    "game_templates",
]


def verify_schema() -> None:
    """
    Verify that all required database tables exist.

    Raises:
        RuntimeError: If any required table is missing
    """
    tracer = trace.get_tracer(__name__)

    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "gamebot")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    db_name = os.getenv("POSTGRES_DB", "game_scheduler")

    logger.info("Verifying database schema")

    with tracer.start_as_current_span("init.verify_schema") as span:
        span.set_attribute("db.tables.required", len(REQUIRED_TABLES))

        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            dbname=db_name,
        )
        cursor = conn.cursor()

        missing_tables = []
        for table in REQUIRED_TABLES:
            try:
                cursor.execute(
                    sql.SQL("SELECT 1 FROM {table} LIMIT 0").format(table=sql.Identifier(table))
                )
                logger.debug(f"Table '{table}' exists")
            except psycopg2.Error:
                missing_tables.append(table)
                logger.error(f"Table '{table}' is missing!")

        cursor.close()
        conn.close()

        if missing_tables:
            error_msg = f"Missing required tables: {', '.join(missing_tables)}"
            logger.error(error_msg)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            span.set_attribute("db.tables.missing", len(missing_tables))
            raise RuntimeError(error_msg)

        logger.info(f"All {len(REQUIRED_TABLES)} required tables verified")
        span.set_status(trace.Status(trace.StatusCode.OK))
        span.set_attribute("db.tables.verified", len(REQUIRED_TABLES))

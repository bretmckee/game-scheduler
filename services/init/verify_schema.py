#!/usr/bin/env python3
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
                logger.debug("Table '%s' exists", table)
            except psycopg2.Error:
                missing_tables.append(table)
                logger.error("Table '%s' is missing!", table)

        cursor.close()
        conn.close()

        if missing_tables:
            error_msg = f"Missing required tables: {', '.join(missing_tables)}"
            logger.error(error_msg)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            span.set_attribute("db.tables.missing", len(missing_tables))
            raise RuntimeError(error_msg)

        logger.info("All %s required tables verified", len(REQUIRED_TABLES))
        span.set_status(trace.Status(trace.StatusCode.OK))
        span.set_attribute("db.tables.verified", len(REQUIRED_TABLES))

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


"""PostgreSQL readiness check with retry logic."""

import logging
import os
import time

import psycopg2
from opentelemetry import trace

logger = logging.getLogger(__name__)


def wait_for_postgres(max_retries: int = 60, retry_delay: float = 1.0) -> None:
    """
    Wait for PostgreSQL to be ready to accept connections.

    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retry attempts in seconds

    Raises:
        RuntimeError: If PostgreSQL is not ready after max_retries
    """
    tracer = trace.get_tracer(__name__)

    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "gamebot")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    db_name = os.getenv("POSTGRES_DB", "game_scheduler")

    logger.info(f"Waiting for PostgreSQL at {db_host}:{db_port} (max {max_retries} attempts)")

    with tracer.start_as_current_span("init.wait_postgres") as span:
        for attempt in range(1, max_retries + 1):
            try:
                conn = psycopg2.connect(
                    host=db_host,
                    port=db_port,
                    user=db_user,
                    password=db_password,
                    dbname=db_name,
                    connect_timeout=3,
                )
                conn.close()
                logger.info("PostgreSQL is ready")
                span.set_status(trace.Status(trace.StatusCode.OK))
                return
            except psycopg2.OperationalError as e:
                if attempt < max_retries:
                    logger.debug(f"PostgreSQL not ready (attempt {attempt}/{max_retries}): {e}")
                    time.sleep(retry_delay)
                else:
                    error_msg = f"PostgreSQL failed to become ready after {max_retries} attempts"
                    logger.error(error_msg)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                    span.record_exception(e)
                    raise RuntimeError(error_msg) from e

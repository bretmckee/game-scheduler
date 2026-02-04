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

    logger.info(
        "Waiting for PostgreSQL at %s:%s (max %s attempts)",
        db_host,
        db_port,
        max_retries,
    )

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
                    logger.debug(
                        "PostgreSQL not ready (attempt %s/%s): %s",
                        attempt,
                        max_retries,
                        e,
                    )
                    time.sleep(retry_delay)
                else:
                    error_msg = f"PostgreSQL failed to become ready after {max_retries} attempts"
                    logger.error(error_msg)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                    span.record_exception(e)
                    raise RuntimeError(error_msg) from e

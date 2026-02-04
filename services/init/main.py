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


"""
Environment initialization orchestrator.

Coordinates all initialization steps for the application environment:
1. Wait for PostgreSQL to be ready
2. Create database users for RLS enforcement
3. Run database migrations
4. Verify database schema
5. Initialize RabbitMQ infrastructure

All steps are instrumented with OpenTelemetry for observability.
"""

import logging
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from opentelemetry import trace

from services.init.database_users import create_database_users
from services.init.migrations import run_migrations
from services.init.rabbitmq import initialize_rabbitmq
from services.init.verify_schema import verify_schema
from services.init.wait_postgres import wait_for_postgres
from shared.telemetry import flush_telemetry, init_telemetry

SECONDS_PER_DAY = 86400

# Configure logging before any operations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def _initialize_telemetry_and_logging() -> tuple[trace.Tracer, datetime]:
    """Initialize telemetry and log startup banner."""
    init_telemetry("init-service")
    tracer = trace.get_tracer(__name__)
    start_time = datetime.now(UTC)

    logger.info("=" * 60)
    logger.info("Environment Initialization Started")
    logger.info("Timestamp: %s", start_time.strftime("%Y-%m-%d %H:%M:%S UTC"))
    logger.info("=" * 60)

    return tracer, start_time


def _log_phase(phase: int, total: int, description: str, completed: bool = False) -> None:
    """Log initialization phase progress."""
    status = "✓" if completed else ""
    logger.info("%s[%s/%s] %s", status, phase, total, description)


def _complete_initialization(start_time: datetime) -> NoReturn:
    """Complete initialization and enter healthy sleep mode."""
    end_time = datetime.now(UTC)
    duration = (end_time - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("Environment Initialization Complete")
    logger.info("Duration: %.2f seconds", duration)
    logger.info("=" * 60)

    marker_file = Path(tempfile.gettempdir()) / "init-complete"
    marker_file.touch()
    logger.info("Created completion marker: %s", marker_file)

    logger.info("Entering sleep mode. Container will remain healthy.")
    while True:
        time.sleep(SECONDS_PER_DAY)


def main() -> int:
    """
    Main initialization orchestrator.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    tracer, start_time = _initialize_telemetry_and_logging()

    with tracer.start_as_current_span("init.environment") as span:
        try:
            _log_phase(1, 5, "Waiting for PostgreSQL...")
            wait_for_postgres()
            _log_phase(1, 5, "PostgreSQL ready", completed=True)

            _log_phase(2, 5, "Creating database users for RLS enforcement...")
            create_database_users()
            _log_phase(2, 5, "Database users configured", completed=True)

            _log_phase(3, 5, "Running database migrations...")
            run_migrations()
            _log_phase(3, 5, "Migrations complete", completed=True)

            _log_phase(4, 5, "Verifying database schema...")
            verify_schema()
            _log_phase(4, 5, "Schema verified", completed=True)

            _log_phase(5, 5, "Initializing RabbitMQ infrastructure...")
            initialize_rabbitmq()
            _log_phase(5, 5, "RabbitMQ infrastructure ready", completed=True)

            logger.info("Finalizing initialization...")
            span.set_status(trace.Status(trace.StatusCode.OK))
            _complete_initialization(start_time)

        except Exception as e:
            logger.error("=" * 60)
            logger.error("Environment Initialization Failed")
            logger.exception("Error: %s", e)
            logger.error("=" * 60)

            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            return 1

        finally:
            flush_telemetry()


if __name__ == "__main__":
    sys.exit(main())

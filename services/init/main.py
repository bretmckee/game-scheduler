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
Environment initialization orchestrator.

Coordinates all initialization steps for the application environment:
1. Wait for PostgreSQL to be ready
2. Run database migrations
3. Verify database schema
4. Wait for RabbitMQ to be ready
5. Create RabbitMQ infrastructure

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
from services.init.seed_e2e import seed_e2e_data
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
            _log_phase(1, 6, "Waiting for PostgreSQL...")
            wait_for_postgres()
            _log_phase(1, 6, "PostgreSQL ready", completed=True)

            _log_phase(2, 6, "Creating database users for RLS enforcement...")
            create_database_users()
            _log_phase(2, 6, "Database users configured", completed=True)

            _log_phase(3, 6, "Running database migrations...")
            run_migrations()
            _log_phase(3, 6, "Migrations complete", completed=True)

            _log_phase(4, 6, "Verifying database schema...")
            verify_schema()
            _log_phase(4, 6, "Schema verified", completed=True)

            _log_phase(5, 6, "Initializing RabbitMQ infrastructure...")
            initialize_rabbitmq()
            _log_phase(5, 6, "RabbitMQ infrastructure ready", completed=True)

            _log_phase(6, 6, "Seeding E2E test data (if applicable)...")
            if not seed_e2e_data():
                msg = "E2E test data seeding failed. Cannot continue with invalid test environment."
                raise RuntimeError(msg)
            _log_phase(6, 6, "E2E seeding complete", completed=True)

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

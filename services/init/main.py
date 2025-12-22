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
from datetime import UTC, datetime

from opentelemetry import trace

from services.init.migrations import run_migrations
from services.init.rabbitmq import initialize_rabbitmq
from services.init.seed_e2e import seed_e2e_data
from services.init.verify_schema import verify_schema
from services.init.wait_postgres import wait_for_postgres
from shared.telemetry import flush_telemetry, init_telemetry

# Configure logging before any operations
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def main() -> int:
    """
    Main initialization orchestrator.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    init_telemetry("init-service")
    tracer = trace.get_tracer(__name__)

    start_time = datetime.now(UTC)
    logger.info("=" * 60)
    logger.info("Environment Initialization Started")
    logger.info(f"Timestamp: {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)

    with tracer.start_as_current_span("init.environment") as span:
        try:
            logger.info("[1/5] Waiting for PostgreSQL...")
            wait_for_postgres()
            logger.info("✓ PostgreSQL ready")

            logger.info("[2/5] Running database migrations...")
            run_migrations()
            logger.info("✓ Migrations complete")

            logger.info("[3/5] Verifying database schema...")
            verify_schema()
            logger.info("✓ Schema verified")

            logger.info("[4/5] Initializing RabbitMQ infrastructure...")
            initialize_rabbitmq()
            logger.info("✓ RabbitMQ infrastructure ready")

            logger.info("[5/5] Seeding E2E test data (if applicable)...")
            if not seed_e2e_data():
                logger.warning("E2E seed failed, but continuing...")
            logger.info("✓ E2E seeding complete")

            logger.info("[6/6] Finalizing initialization...")
            span.set_status(trace.Status(trace.StatusCode.OK))

            end_time = datetime.now(UTC)
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 60)
            logger.info("Environment Initialization Complete")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info("=" * 60)

            return 0

        except Exception as e:
            logger.error("=" * 60)
            logger.error("Environment Initialization Failed")
            logger.error(f"Error: {e}", exc_info=True)
            logger.error("=" * 60)

            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            span.record_exception(e)
            return 1

        finally:
            flush_telemetry()


if __name__ == "__main__":
    sys.exit(main())

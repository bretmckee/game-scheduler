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


"""Database migration execution via Alembic."""

import logging
import shutil
import subprocess  # noqa: S404 - Used safely with shell=False

from opentelemetry import trace

logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Run Alembic database migrations to upgrade schema.

    Raises:
        RuntimeError: If migration fails
    """
    tracer = trace.get_tracer(__name__)

    logger.info("Running database migrations")

    with tracer.start_as_current_span("init.database_migration") as span:
        alembic_path = shutil.which("alembic")
        if not alembic_path:
            error_msg = "alembic executable not found in PATH"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # S603: Safe - using absolute path from shutil.which() validation
        result = subprocess.run(  # noqa: S603
            [alembic_path, "upgrade", "head"],
            capture_output=True,
            text=True,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"[alembic] {line}")

        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning(f"[alembic] {line}")

        if result.returncode != 0:
            error_msg = "Database migration failed"
            logger.error(f"{error_msg}: {result.stderr}")
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            span.record_exception(Exception(result.stderr))
            raise RuntimeError(error_msg)

        logger.info("Database migrations completed successfully")
        span.set_status(trace.Status(trace.StatusCode.OK))

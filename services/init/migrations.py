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
            check=False,
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info("[alembic] %s", line)

        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning("[alembic] %s", line)

        if result.returncode != 0:
            error_msg = "Database migration failed"
            logger.error("%s: %s", error_msg, result.stderr)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            span.record_exception(Exception(result.stderr))
            raise RuntimeError(error_msg)

        logger.info("Database migrations completed successfully")
        span.set_status(trace.Status(trace.StatusCode.OK))

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


"""Database migration service with OpenTelemetry instrumentation."""

import subprocess
import sys

from opentelemetry import trace

from shared.telemetry import init_telemetry


def run_migrations() -> int:
    """
    Run Alembic database migrations with telemetry.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    init_telemetry("init-service")
    tracer = trace.get_tracer(__name__)

    print("Running database migrations...")
    with tracer.start_as_current_span("init.database_migration") as span:
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)

        if result.returncode != 0:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Migration failed"))
            span.record_exception(Exception(result.stderr))
            return result.returncode

        span.set_status(trace.Status(trace.StatusCode.OK))
        print("✓ Migrations complete")
        return 0


if __name__ == "__main__":
    sys.exit(run_migrations())

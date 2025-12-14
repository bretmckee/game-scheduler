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
Environment initialization service.

This package orchestrates all initialization steps required before the
application can start:

1. PostgreSQL readiness check (wait_postgres.py)
2. Database migrations via Alembic (migrations.py)
3. Database schema verification (verify_schema.py)
4. RabbitMQ infrastructure creation (rabbitmq.py)

All modules are fully instrumented with OpenTelemetry for observability,
providing traces, metrics, and structured logs that are sent to Grafana Cloud.

Architecture:
- main.py: Orchestrator that coordinates all initialization steps
- Each module is independently testable and reusable
- All modules use Python logging (captured by OpenTelemetry)
- All errors include proper exception handling and trace correlation

Usage:
    # Full initialization (orchestrated)
    python -m services.init.main

    # RabbitMQ only (CI/CD standalone)
    python -m services.init.rabbitmq
"""

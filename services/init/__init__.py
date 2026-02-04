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

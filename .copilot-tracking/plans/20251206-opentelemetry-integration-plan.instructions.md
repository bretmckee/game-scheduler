---
applyTo: '.copilot-tracking/changes/20251206-opentelemetry-integration-changes.md'
---
<!-- markdownlint-disable-file -->
# Task Checklist: OpenTelemetry Integration

## Overview

Integrate OpenTelemetry observability into the game scheduler application for distributed tracing, metrics collection, and log correlation across all Python microservices and infrastructure components.

## Objectives

- Enable distributed tracing across API, Bot, and Daemon services
- Collect infrastructure metrics from PostgreSQL, Redis, and RabbitMQ
- Correlate logs with traces for improved debugging
- Deploy to Grafana Cloud for zero-cost production observability
- Maintain <5% performance overhead

## Research Summary

### Project Files
- `pyproject.toml` - Python dependency management (Lines 1-50)
- `docker-compose.base.yml` - Service definitions (Lines 1-200)
- `RUNTIME_CONFIG.md` - Runtime configuration patterns (Lines 1-150)
- `services/api/main.py` - FastAPI application entry point
- `services/bot/main.py` - Discord bot entry point
- `services/scheduler/notification_daemon.py` - Notification daemon
- `services/scheduler/status_transition_daemon.py` - Status transition daemon

### External References
- #file:../research/20251206-opentelemetry-compatibility-research.md (Lines 1-669) - Complete compatibility assessment
- #fetch:"https://opentelemetry.io/docs/languages/python/libraries/" - Python instrumentation libraries
- #fetch:"https://opentelemetry.io/docs/collector/" - Collector architecture patterns
- #githubRepo:"open-telemetry/opentelemetry-python instrumentation" - Python instrumentation examples

### Standards References
- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker best practices
- #file:../../.github/instructions/coding-best-practices.instructions.md - General coding standards

## Implementation Checklist

### [ ] Phase 1: Python Dependencies and Base Configuration

- [ ] Task 1.1: Add OpenTelemetry Python packages to pyproject.toml
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 15-35)

- [ ] Task 1.2: Create shared OpenTelemetry initialization module
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 37-70)

- [ ] Task 1.3: Add OpenTelemetry environment variables to .env.example
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 72-90)

### [ ] Phase 2: Service Instrumentation

- [ ] Task 2.1: Instrument FastAPI service (services/api)
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 92-125)

- [ ] Task 2.2: Instrument Discord Bot service (services/bot)
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 127-165)

- [ ] Task 2.3: Instrument Notification Daemon
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 167-195)

- [ ] Task 2.4: Instrument Status Transition Daemon
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 197-225)

### [ ] Phase 3: Infrastructure Telemetry Collection

- [ ] Task 3.1: Create OpenTelemetry Collector configuration
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 227-280)

- [ ] Task 3.2: Add Grafana Alloy service to docker-compose
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 282-310)

- [ ] Task 3.3: Configure PostgreSQL metrics collection
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 312-335)

- [ ] Task 3.4: Configure Redis metrics collection
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 337-355)

### [ ] Phase 4: Grafana Cloud Integration

- [ ] Task 4.1: Document Grafana Cloud setup process
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 357-380)

- [ ] Task 4.2: Create Alloy configuration for Grafana Cloud export
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 382-425)

- [ ] Task 4.3: Update RUNTIME_CONFIG.md with OpenTelemetry documentation
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 427-455)

### [ ] Phase 5: Testing and Validation

- [ ] Task 5.1: Create integration tests for trace propagation
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 457-490)

- [ ] Task 5.2: Verify metrics collection from all infrastructure components
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 492-515)

- [ ] Task 5.3: Test log correlation with trace IDs
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 517-540)

- [ ] Task 5.4: Performance baseline and overhead measurement
  - Details: .copilot-tracking/details/20251206-opentelemetry-integration-details.md (Lines 542-570)

## Dependencies

- OpenTelemetry Python SDK 1.28.2+
- OpenTelemetry instrumentation libraries for FastAPI, SQLAlchemy, asyncpg, redis, aio-pika
- Grafana Alloy (OpenTelemetry Collector distribution)
- Grafana Cloud account (free tier)
- Docker Compose 2.x

## Success Criteria

- All API requests generate complete trace spans from HTTP ingress to database queries
- Bot commands create trace spans with Discord event context
- Database queries appear as child spans with SQL statements visible
- Redis operations create spans with command details
- RabbitMQ message publish/consume operations create linked spans
- Daemon scheduled tasks create root spans with proper context
- PostgreSQL connection pool metrics collected and exported
- Redis memory usage and command metrics collected
- Logs automatically include trace IDs for correlation
- All telemetry successfully exports to Grafana Cloud
- Performance overhead remains below 5% for P99 latency
- Integration tests verify trace propagation across service boundaries

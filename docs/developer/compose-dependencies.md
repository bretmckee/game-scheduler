# Docker Compose Service Dependencies

## Overview

This document describes the service dependency structure across all Docker Compose environments and how to use the debugging features in test environments.

## Service Architecture

The application consists of:

- **Infrastructure**: postgres, redis, grafana-alloy
- **Initialization**: init (database migrations and seed data)
- **Application services**: api, bot, frontend
- **Test services**: e2e-tests, integration-tests
- **Debug helper**: system-ready (test environments only)

## Dependency Chains

### Base (compose.yaml)

```
postgres + grafana-alloy
  ↓
init
  ↓
bot ──────────────────────────┐
  ↓                           │
api ────────────────────────► frontend
```

- `init` waits for postgres (healthy) and grafana-alloy (started)
- `bot` waits for init (healthy)
- `api` waits for init (healthy) and bot (healthy) — bot must be up so BotActionListener is ready to process queue rows
- `frontend` waits for api (healthy) in all non-development environments

### Development (compose.override.yaml)

Same as base. The frontend only requires api, allowing fast iteration without waiting for bot.

### Production / Staging

```
postgres + redis + grafana-alloy
  ↓
init
  ↓
bot
  ↓
api
  ↓
frontend (waits for api healthy)
```

### E2E Tests (compose.e2e.yaml)

```
postgres + redis + grafana-alloy
  ↓
init
  ↓
bot + api
  ↓
system-ready
  ↓
e2e-tests
```

`system-ready` waits for: init (healthy), postgres (healthy), redis (healthy), api (healthy), bot (healthy).

### Integration Tests (compose.int.yaml)

```
postgres + redis + grafana-alloy
  ↓
init
  ↓
api + fake-discord
  ↓
system-ready
  ↓
integration-tests
```

`system-ready` waits for: init (healthy), postgres (healthy), redis (healthy), api (healthy), fake-discord (healthy).

Integration tests do not require a live bot service — they use `fake-discord` to simulate Discord API responses.

## Usage Guide

### Running Tests

```bash
# E2E tests
scripts/run-e2e-tests.sh

# E2E - specific test
scripts/run-e2e-tests.sh tests/e2e/test_game_reminder.py -v

# Integration tests
scripts/run-integration-tests.sh

# Integration - specific test
scripts/run-integration-tests.sh tests/integration/test_signup.py -v
```

### Debugging Tests with Persistent Services

Start the environment without running tests by targeting `system-ready`:

```bash
# E2E environment
docker compose -f compose.yaml -f compose.e2e.yaml \
  --env-file config/env/env.e2e \
  up -d system-ready

# Integration environment
docker compose -f compose.yaml -f compose.int.yaml \
  --env-file config/env/env.int \
  up -d system-ready
```

Then run tests manually against the running services:

```bash
# E2E
docker compose -f compose.yaml -f compose.e2e.yaml \
  run --rm e2e-tests tests/e2e/ -v

# Integration
docker compose -f compose.yaml -f compose.int.yaml \
  run --rm integration-tests tests/integration/ -v
```

Inspect logs while services are running:

```bash
# E2E
docker compose -f compose.yaml -f compose.e2e.yaml logs -f api bot

# Integration
docker compose -f compose.yaml -f compose.int.yaml logs -f api fake-discord
```

Tear down when done:

```bash
docker compose -f compose.yaml -f compose.e2e.yaml down -v
docker compose -f compose.yaml -f compose.int.yaml down -v
```

### Deployment Environments

```bash
# Development
docker compose up

# Staging
docker compose --env-file config/env/env.staging up -d

# Production
docker compose --env-file config/env/env.prod up -d
```

## Telemetry in Test Environments

All Python services in test environments have `PYTEST_RUNNING: "1"` set, which disables OpenTelemetry data collection during test runs. This prevents test traffic from appearing in Grafana Cloud dashboards.

## Troubleshooting

**Services won't start:**

```bash
# Check service status and health
docker compose ps

# Check init logs for migration failures
docker compose logs init

# Check bot logs for startup failures
docker compose logs bot

# Check api logs
docker compose logs api
```

**Tests fail immediately:**

- Verify system-ready completed: `docker compose ps system-ready`
- Check that postgres is healthy: `docker compose ps postgres`
- Integration tests: verify fake-discord is healthy

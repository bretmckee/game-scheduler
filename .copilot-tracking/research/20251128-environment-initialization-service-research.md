<!-- markdownlint-disable-file -->
# Task Research Notes: Environment Initialization Service

## Research Executed

### File Analysis
- `docker-compose.base.yml`
  - Infrastructure services: postgres, rabbitmq, redis with health checks
  - Application services: bot, api, scheduler, scheduler-beat, notification-daemon, frontend
  - Services depend on infrastructure using `depends_on` with health check conditions
  - No migration or initialization service currently defined
- `docker-compose.yml` (development)
  - Includes base services with persistent volumes
- `docker-compose.integration.yml` (integration tests)
  - Includes base services with tmpfs volumes for speed
  - Runs integration-tests service depending on infrastructure
- `docker-compose.e2e.yml` (e2e tests)
  - Includes base services with tmpfs volumes
  - Runs e2e-tests service depending on infrastructure, bot, and notification-daemon
- `docker/migrate.Dockerfile` and `docker/migrate-entrypoint.sh`
  - Existing migration infrastructure using Alembic
  - Waits for PostgreSQL, then runs `alembic upgrade head`
- `docker/init-entrypoint.sh`
  - Identical to migrate-entrypoint.sh, appears to be a duplicate
- `alembic/versions/012_add_notification_schedule.py`
  - Creates notification_schedule table with PostgreSQL trigger
  - Trigger sends LISTEN/NOTIFY events for schedule changes
- `rabbitmq/definitions.json`
  - Pre-configured exchanges, queues, and bindings
  - Loaded via volume mount at `/etc/rabbitmq/definitions.json:ro`
  - RabbitMQ auto-loads this on startup

### Code Search Results
- `notification_schedule` table
  - Created by migration 012 with PostgreSQL trigger function
  - No manual seeding required, migrations handle structure
- Database initialization patterns
  - Tests create fixtures programmatically
  - No seed data scripts found in codebase
  - Migrations handle all schema setup

### External Research
- #fetch:https://docs.docker.com/compose/startup-order/
  - Docker Compose `depends_on` with health checks ensures proper startup order
  - `condition: service_healthy` waits for healthcheck to pass
  - Init containers pattern: run one-time setup tasks before application services
- #githubRepo:"docker/compose" startup order initialization
  - Common pattern: separate "init" service that runs migrations and setup
  - Use `depends_on` to make application services wait for init completion
  - Init service should exit after completion (no restart policy)

### Project Conventions
- Standards referenced: Docker containerization best practices from `.github/instructions/containerization-docker-best-practices.instructions.md`
- Instructions followed: Use minimal base images, multi-stage builds, non-root users
- Existing patterns: Services use health checks, depend on infrastructure services

## Key Discoveries

### Project Structure
The project uses Docker Compose with a base configuration pattern:
- `docker-compose.base.yml`: Shared service definitions
- Environment-specific files (`.yml`, `.integration.yml`, `.e2e.yml`) include base and add overrides
- Infrastructure services (postgres, rabbitmq, redis) have health checks
- Application services use `depends_on` with `condition: service_healthy`

### Implementation Patterns

**Current Migration Approach:**
- `migrate.Dockerfile` builds image with Alembic and dependencies
- `migrate-entrypoint.sh` waits for database, runs migrations
- Currently only used implicitly or manually

**RabbitMQ Configuration:**
- Uses definitions.json mounted as read-only volume
- RabbitMQ auto-loads configuration on startup
- No additional initialization needed

**Redis Configuration:**
- No initialization required
- Starts empty and ready to use

### Database Migration Details

**Alembic Migration System:**
```python
# Migration 012 creates notification_schedule with trigger
op.create_table("notification_schedule", ...)
op.execute("""
    CREATE OR REPLACE FUNCTION notify_schedule_changed()
    RETURNS TRIGGER AS $$ ... $$ LANGUAGE plpgsql;
""")
op.execute("""
    CREATE TRIGGER notification_schedule_trigger
    AFTER INSERT OR UPDATE OR DELETE ON notification_schedule
    FOR EACH ROW EXECUTE FUNCTION notify_schedule_changed();
""")
```

**Current Migration Process:**
- `migrate-entrypoint.sh` uses psql to wait for database
- Runs `alembic upgrade head` to apply all pending migrations
- No rollback or error handling beyond `set -e`

### Docker Compose Dependency Patterns

**Health Check Pattern:**
```yaml
postgres:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 10s
    timeout: 5s
    retries: 5

api:
  depends_on:
    postgres:
      condition: service_healthy
```

**Init Container Pattern:**
```yaml
init:
  depends_on:
    postgres:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
    redis:
      condition: service_healthy
  restart: "no"  # Exit after completion

api:
  depends_on:
    init:
      condition: service_completed_successfully
```

## Recommended Approach

**Create dedicated `init` service for environment initialization**

The init service will:
1. Wait for all infrastructure services to be healthy (postgres, rabbitmq, redis)
2. Run database migrations using Alembic
3. Perform any additional setup (currently none needed for rabbitmq/redis)
4. Exit successfully to signal readiness to dependent services
5. Run in all environments: development, integration tests, e2e tests, production

### Implementation Strategy

**1. Reuse Existing migrate.Dockerfile**
- Already contains all dependencies (Alembic, psycopg2, shared models)
- Minimal image based on python:3.11-slim
- No changes needed to Dockerfile

**2. Enhance migrate-entrypoint.sh**
- Add better error handling and logging
- Add verification steps
- Make it more robust for production use

**3. Add init service to docker-compose.base.yml**
```yaml
init:
  build:
    context: .
    dockerfile: docker/migrate.Dockerfile
  container_name: ${CONTAINER_PREFIX:-gamebot}-init
  environment:
    DATABASE_URL: ${DATABASE_URL}
    POSTGRES_HOST: postgres
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
  depends_on:
    postgres:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
    redis:
      condition: service_healthy
  networks:
    - app-network
  restart: "no"  # Exit after successful completion
```

**4. Update Application Services**
Change all application services to depend on init completion:
```yaml
api:
  depends_on:
    init:
      condition: service_completed_successfully
  # ... rest of config
```

**5. Enhance Entrypoint Script**
```bash
#!/bin/bash
set -e

echo "=== Environment Initialization ==="
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "  PostgreSQL not ready, retrying..."
  sleep 1
done
echo "✓ PostgreSQL is ready"

# Run database migrations
echo "Running database migrations..."
alembic upgrade head
echo "✓ Migrations complete"

# Verify critical tables exist
echo "Verifying database schema..."
TABLES="users guild_configurations channel_configurations game_sessions game_participants notification_schedule"
for table in $TABLES; do
  if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1 FROM $table LIMIT 0" >/dev/null 2>&1; then
    echo "  ✓ Table $table exists"
  else
    echo "  ✗ Table $table missing!"
    exit 1
  fi
done

echo "=== Initialization Complete ==="
```

### Benefits of This Approach

1. **Runs in All Environments**: Development, test, and production
2. **Guarantees Order**: Application services wait for initialization
3. **Idempotent**: Safe to run multiple times (migrations are idempotent)
4. **Fast for Tests**: Completes quickly with tmpfs volumes
5. **Clear Dependency Chain**: Infrastructure → Init → Applications
6. **Single Responsibility**: One service handles all initialization
7. **Reuses Existing Code**: Leverages migrate.Dockerfile and Alembic
8. **Production Ready**: Proper error handling and verification

## Implementation Guidance

### Objectives
- Ensure database is migrated before applications start
- Provide clear initialization status and error messages
- Support all environments (dev, test, production)
- Maintain fast startup times for test environments

### Key Tasks
1. Enhance `docker/migrate-entrypoint.sh` with better logging and verification
2. Add `init` service to `docker-compose.base.yml`
3. Update all application services to depend on `init` completion
4. Test in development environment
5. Test in integration test environment
6. Test in e2e test environment

### Dependencies
- Existing `docker/migrate.Dockerfile` (no changes needed)
- Existing Alembic migrations (no changes needed)
- PostgreSQL health checks (already configured)
- RabbitMQ health checks (already configured)
- Redis health checks (already configured)

### Success Criteria
- Init service runs successfully in all environments
- Application services start only after init completes
- Clear log messages indicate initialization progress
- Schema verification catches missing tables
- Fast startup in test environments with tmpfs volumes
- Idempotent: safe to restart without side effects

<!-- markdownlint-disable-file -->

# Task Details: Minimize Docker Port Exposure for Security

## Research Reference

**Source Research**: #file:../research/20251210-test-instance-deployment-issues-research.md

## Phase 1: Remove Infrastructure Ports from Base Configuration

### Task 1.1: Remove postgres port mapping from docker-compose.base.yml

Remove the `ports:` section from the postgres service definition. Services will access PostgreSQL via internal Docker network using `postgres:5432`.

- **Files**:
  - docker-compose.base.yml - Remove lines 27-28 (ports section)
- **Success**:
  - No `ports:` section in postgres service
  - Service still accessible internally via `postgres:5432`
  - Healthcheck continues to function
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Issue 1: Unnecessary port exposure
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Strategy explanation
- **Dependencies**:
  - None

### Task 1.2: Remove rabbitmq data port (5672) from docker-compose.base.yml

Remove only the 5672 port mapping (AMQP protocol) from RabbitMQ. Keep management UI (15672) and Prometheus metrics (15692) ports for now - they will be moved to development overrides in Phase 2.

- **Files**:
  - docker-compose.base.yml - Remove line 50 (5672 port mapping only)
- **Success**:
  - No 5672 port mapping in rabbitmq service
  - Lines 51-52 (15672 and 15692) remain temporarily
  - Service still accessible internally via `rabbitmq:5672`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Infrastructure port exposure issue
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Management UI port analysis
- **Dependencies**:
  - None

### Task 1.3: Remove redis port mapping from docker-compose.base.yml

Remove the `ports:` section from the redis service definition. Services will access Redis via internal Docker network using `redis:6379`.

- **Files**:
  - docker-compose.base.yml - Remove lines 69-70 (ports section)
- **Success**:
  - No `ports:` section in redis service
  - Service still accessible internally via `redis:6379`
  - Healthcheck continues to function
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 48-65) - Infrastructure service exposure
- **Dependencies**:
  - None

### Task 1.4: Remove grafana-alloy OTLP ports from docker-compose.base.yml

Remove OTLP port mappings (4317, 4318) from grafana-alloy service. All services send telemetry to Alloy via internal network using `grafana-alloy:4317` and `grafana-alloy:4318`.

- **Files**:
  - docker-compose.base.yml - Search for grafana-alloy service and remove its ports section
- **Success**:
  - No `ports:` section in grafana-alloy service
  - Services continue sending telemetry via internal network
  - Alloy continues forwarding to Grafana Cloud
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Observability port analysis
- **Dependencies**:
  - None

## Phase 2: Add Development Port Overrides

### Task 2.1: Add frontend port to compose.override.yaml

Add frontend port mapping to development overrides for browser access during development.

- **Files**:
  - compose.override.yaml - Add `ports:` section to frontend service
- **Success**:
  - Frontend accessible at `http://localhost:3000` in development
  - Port configurable via `FRONTEND_HOST_PORT` environment variable
  - Uses format: `"${FRONTEND_HOST_PORT:-3000}:80"`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Development override strategy
- **Dependencies**:
  - Phase 1 completion (base configuration has no ports)

### Task 2.2: Add API port to compose.override.yaml

Add API port mapping to development overrides for direct API testing during development.

- **Files**:
  - compose.override.yaml - Add `ports:` section to api service
- **Success**:
  - API accessible at `http://localhost:8000` in development
  - Port configurable via `API_HOST_PORT` environment variable
  - Uses format: `"${API_HOST_PORT:-8000}:8000"`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Development port requirements
- **Dependencies**:
  - Phase 1 completion

### Task 2.3: Add RabbitMQ management UI port to compose.override.yaml

Add RabbitMQ management UI port (15672) to development overrides for monitoring and debugging.

- **Files**:
  - compose.override.yaml - Add `ports:` section to rabbitmq service (if it exists, otherwise create service override)
  - docker-compose.base.yml - Remove remaining RabbitMQ port mappings (15672, 15692)
- **Success**:
  - RabbitMQ management UI accessible at `http://localhost:15672` in development only
  - Port configurable via `RABBITMQ_MGMT_HOST_PORT` environment variable
  - Prometheus metrics port (15692) not exposed (Alloy scrapes internally)
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 108-136) - Management UI analysis
- **Dependencies**:
  - Phase 1 Task 1.2 completion (base has no RabbitMQ ports)

## Phase 3: Add Test Environment Port Overrides

### Task 3.1: Add frontend and API ports to docker-compose.test.yml

Add frontend and API port mappings to test configuration for test execution and verification.

- **Files**:
  - docker-compose.test.yml - Add service overrides for frontend and api with ports
- **Success**:
  - Frontend accessible during test runs
  - API accessible during test runs
  - No management UI ports exposed in test environment
  - Uses same port environment variables as development
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Test environment requirements
- **Dependencies**:
  - Phase 1 completion (base has no ports)
  - Phase 2 completion (pattern established)

## Phase 4: Update Documentation

### Task 4.1: Update .env.example with port configuration guidance

Add comprehensive documentation about port configuration strategy and `docker exec` usage for infrastructure debugging.

- **Files**:
  - .env.example - Add new section explaining port exposure strategy
- **Success**:
  - Clear explanation of which ports are exposed in which environments
  - `docker exec` examples for postgres, redis, rabbitmq debugging
  - Explanation that observability uses internal network only
  - Port variables documented: API_HOST_PORT, FRONTEND_HOST_PORT, RABBITMQ_MGMT_HOST_PORT
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 138-163) - Documentation requirements
- **Dependencies**:
  - All previous phases complete

### Task 4.2: Verify compose.production.yaml has no port mappings

Verify that production configuration does not expose any ports (reverse proxy handles external access).

- **Files**:
  - compose.production.yaml - Inspect all services
- **Success**:
  - No `ports:` sections in any service
  - Documentation confirms reverse proxy usage
  - Production services communicate only via internal network
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 96-106) - Production security requirements
- **Dependencies**:
  - None (verification only)

## Phase 5: Fix Game Host Notifications

### Task 5.1: Add is_host parameter to _send_reminder_dm method

Add optional `is_host` parameter to customize reminder message for game hosts.

- **Files**:
  - services/bot/events/handlers.py - Modify `_send_reminder_dm` method signature
- **Success**:
  - Method accepts `is_host: bool = False` parameter
  - Reminder message customized when `is_host=True` (e.g., "You are hosting...")
  - Existing functionality unchanged when `is_host=False`
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 233-296) - Game host notification issue
- **Dependencies**:
  - None

### Task 5.2: Send reminder to game host in _handle_game_reminder_due

After sending reminders to participants, also send reminder to game host.

- **Files**:
  - services/bot/events/handlers.py - Modify `_handle_game_reminder_due` method
- **Success**:
  - Host receives DM reminder at scheduled times
  - Host notification sent even if there are no other participants
  - Error handling prevents host notification failure from affecting other notifications
  - Unit tests verify host receives notifications
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 233-296) - Implementation approach
- **Dependencies**:
  - Task 5.1 completion

## Phase 6: Verify Notify Roles Functionality

### Task 6.1: Verify notify_role_ids database storage and retrieval

Check that notify_role_ids are being properly stored in database and loaded with game objects.

- **Files**:
  - services/bot/events/handlers.py - Check `_get_game_with_participants` query
  - Database - Inspect game_sessions table for notify_role_ids values
- **Success**:
  - notify_role_ids field is loaded from database with game object
  - Database contains valid role IDs for games with notify roles
  - Query includes notify_role_ids in select statement
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 298-342) - Notify roles analysis
- **Dependencies**:
  - None (verification task)

### Task 6.2: Test role mentions in Discord announcements

Test that role mentions appear in Discord messages and trigger notifications.

- **Files**:
  - services/bot/formatters/game_message.py - Verify `format_game_announcement` logic
  - Discord - Test actual notification delivery to users with roles
- **Success**:
  - Role mentions appear in message content above embed
  - Users with mentioned roles receive Discord notifications
  - Role IDs are valid snowflake format
  - Bot has permission to mention roles
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 298-342) - Current behavior analysis
- **Dependencies**:
  - Task 6.1 completion

## Phase 7: Remove Unused Environment Variables

### Task 7.1: Remove DISCORD_REDIRECT_URI from all environment files

Remove unused DISCORD_REDIRECT_URI from all environment configuration files.

- **Files**:
  - .env.example - Remove DISCORD_REDIRECT_URI
  - env/env.dev - Remove DISCORD_REDIRECT_URI
  - env/env.prod - Remove DISCORD_REDIRECT_URI
  - env/env.staging - Remove DISCORD_REDIRECT_URI
  - env/env.int - Remove DISCORD_REDIRECT_URI
  - env/env.e2e - Remove DISCORD_REDIRECT_URI
- **Success**:
  - DISCORD_REDIRECT_URI removed from all environment files
  - No references to DISCORD_REDIRECT_URI remain in environment configs
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 344-455) - Unused variable analysis
- **Dependencies**:
  - None

### Task 7.2: Remove DISCORD_REDIRECT_URI from compose.yaml

Remove DISCORD_REDIRECT_URI from bot service environment variables.

- **Files**:
  - compose.yaml - Remove `DISCORD_REDIRECT_URI: ${DISCORD_REDIRECT_URI:-}` from bot service
- **Success**:
  - Bot service no longer receives DISCORD_REDIRECT_URI environment variable
  - Bot service starts successfully without the variable
  - OAuth flow continues to work (uses API_URL instead)
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 344-455) - Variable usage analysis
- **Dependencies**:
  - Task 7.1 completion

### Task 7.3: Remove DISCORD_REDIRECT_URI from documentation

Remove references to DISCORD_REDIRECT_URI from deployment documentation.

- **Files**:
  - DEPLOYMENT_QUICKSTART.md - Remove DISCORD_REDIRECT_URI reference
- **Success**:
  - Documentation no longer mentions DISCORD_REDIRECT_URI
  - Setup instructions remain accurate and complete
  - OAuth configuration explained correctly
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 344-455) - Files affected
- **Dependencies**:
  - Task 7.2 completion

## Phase 8: Fix Game Completion Status Transitions

### Task 8.1: Add DEFAULT_GAME_DURATION_MINUTES constant

Add constant for default game duration when expected_duration_minutes is not set.

- **Files**:
  - services/api/services/games.py - Add constant at module level
- **Success**:
  - `DEFAULT_GAME_DURATION_MINUTES = 60` constant defined
  - Constant documented with comment explaining usage
  - Constant accessible to create_game and update_game methods
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 457-631) - Implementation solution
- **Dependencies**:
  - None

### Task 8.2: Create COMPLETED schedule entry in create_game method

Modify create_game to create TWO status schedule entries: IN_PROGRESS and COMPLETED.

- **Files**:
  - services/api/services/games.py - Modify `create_game` method (after line 249)
- **Success**:
  - Two game_status_schedule entries created for SCHEDULED games
  - First entry: target_status=IN_PROGRESS, transition_time=scheduled_at
  - Second entry: target_status=COMPLETED, transition_time=scheduled_at + duration
  - Duration uses expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
  - Unit tests verify both entries created correctly
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 457-631) - Primary fix implementation
- **Dependencies**:
  - Task 8.1 completion

### Task 8.3: Handle both IN_PROGRESS and COMPLETED schedules in update_game method

Modify update_game to manage both IN_PROGRESS and COMPLETED status schedule entries.

- **Files**:
  - services/api/services/games.py - Modify `update_game` method (around lines 556-591)
- **Success**:
  - Method fetches ALL status schedules for game
  - Updates or creates IN_PROGRESS schedule when game is SCHEDULED
  - Updates or creates COMPLETED schedule when game is SCHEDULED
  - Deletes all schedules when game status changes from SCHEDULED
  - Unit tests verify schedule management logic
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 457-631) - Secondary fix implementation
- **Dependencies**:
  - Task 8.1 completion

### Task 8.4: Create database migration for existing games

Create migration to add missing COMPLETED schedules to existing IN_PROGRESS games.

- **Files**:
  - alembic/versions/new_migration.py - Create new migration file
- **Success**:
  - Migration adds COMPLETED schedule to games missing it
  - Uses scheduled_at + 60 minutes as default completion time
  - Migration is idempotent (safe to run multiple times)
  - Migration tested in development environment
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 457-631) - Migration strategy
- **Dependencies**:
  - Tasks 8.1, 8.2, 8.3 completion

## Phase 9: Add Observability to Init Service

### Task 9.1: Add telemetry to init_rabbitmq.py script

Initialize OpenTelemetry in init_rabbitmq.py and wrap operations in spans.

- **Files**:
  - scripts/init_rabbitmq.py - Add telemetry initialization and span instrumentation
- **Success**:
  - `init_telemetry("init-service")` called at script start
  - RabbitMQ initialization wrapped in `init.rabbitmq` span
  - Errors recorded as span exceptions
  - Console output continues to work (Docker logs)
  - Init traces visible in Grafana Cloud
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 633-739) - Implementation approach
- **Dependencies**:
  - None

### Task 9.2: Add telemetry wrapper to database migrations

Wrap alembic upgrade command with OpenTelemetry span in init-entrypoint.sh.

- **Files**:
  - docker/init-entrypoint.sh - Add Python telemetry wrapper around alembic command
- **Success**:
  - `init_telemetry("init-service")` called before migrations
  - Database migration wrapped in `init.database_migration` span
  - Migration failures recorded as span errors
  - Console output continues (migration logs visible)
  - Migration traces visible in Grafana Cloud
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 633-739) - Telemetry wrapper example
- **Dependencies**:
  - None

## Phase 10: Add service.name to Infrastructure Metrics

### Task 10.1: Route infrastructure metrics through OTEL processors

Configure Grafana Alloy to add service.name resource attribute to infrastructure metrics.

- **Files**:
  - grafana-alloy/config.alloy - Add OTEL processors for postgres, redis, rabbitmq
- **Success**:
  - Infrastructure metrics routed through otelcol.receiver.prometheus
  - Resource processor adds service.name attribute
  - Metrics sent to batch processor and then Mimir
  - service.name visible in Grafana Cloud for postgres, redis, rabbitmq
  - Can filter dashboards by service.name
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 741-1133) - Phase 1 implementation
- **Dependencies**:
  - None

### Task 10.2: Add Docker log rotation to all services

Configure Docker logging driver with rotation limits for all services.

- **Files**:
  - compose.yaml - Add x-logging-default anchor and apply to all services
- **Success**:
  - All services have logging configuration with max-size=10m, max-file=3
  - Log files rotate when size limit reached
  - Old log files compressed automatically
  - Service and environment labels attached to logs
  - No unbounded disk growth from Docker logs
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 741-1133) - Phase 2 implementation
- **Dependencies**:
  - None

### Task 10.3: Configure Grafana Alloy to collect Docker logs

Configure Grafana Alloy to collect Docker logs and send to Grafana Cloud Loki.

- **Files**:
  - grafana-alloy/config.alloy - Add loki.source.docker configuration
  - compose.yaml - Mount Docker socket in grafana-alloy service
- **Success**:
  - Alloy collects logs from all containers with 'service' label
  - Logs forwarded to Grafana Cloud Loki
  - Service, environment, container labels attached to logs
  - Infrastructure logs searchable in Grafana Cloud
  - Can filter logs by service name in Loki
- **Research References**:
  - #file:../research/20251210-test-instance-deployment-issues-research.md (Lines 741-1133) - Phase 3 implementation
- **Dependencies**:
  - Task 10.2 completion (labels configured)

## Dependencies

- Docker Compose with multi-file support
- Existing layered compose configuration structure
- OpenTelemetry instrumentation (shared/telemetry.py)
- Grafana Cloud account with Mimir, Loki, Tempo
- Discord API permissions for role mentions

## Success Criteria

- All infrastructure services accessible via internal Docker network only
- Application services accessible on host in development and test environments
- Production environment exposes zero ports externally
- Documentation provides clear guidance on debugging with `docker exec`
- No port conflicts when running multiple environments
- Game hosts receive reminder notifications with customized messages
- Notify roles properly trigger Discord user notifications
- DISCORD_REDIRECT_URI removed from all configuration and documentation
- Games automatically transition to COMPLETED status after duration
- Existing IN_PROGRESS games receive COMPLETED schedule entries
- Init service telemetry visible in Grafana Cloud (traces and spans)
- Infrastructure metrics have service.name resource attribute
- Docker logs rotate properly (max 30MB per service)
- Infrastructure logs collected and searchable in Grafana Cloud Loki
- All tests pass (no regression in functionality)

<!-- markdownlint-disable-file -->
# Task Research Notes: Test Instance Deployment Issues

## Research Executed

### File Analysis
- `docker-compose.base.yml`
  - Infrastructure services (postgres, rabbitmq, redis) expose ports to host
  - Port exposure controlled via environment variables (POSTGRES_HOST_PORT, etc.)
  - All services connected via `app-network` bridge network
- `.env.example`
  - No port configuration variables defined (uses defaults from docker-compose.base.yml)
  - Services communicate internally via service names (postgres:5432, rabbitmq:5672, redis:6379)
- `docker-compose.test.yml`
  - Uses tmpfs volumes for fast ephemeral storage
  - Includes base configuration with all port mappings

### Code Search Results
- Port mappings in docker-compose.base.yml:
  - postgres: `"${POSTGRES_HOST_PORT:-5432}:5432"`
  - rabbitmq: `"${RABBITMQ_HOST_PORT:-5672}:5672"`, `"${RABBITMQ_MGMT_HOST_PORT:-15672}:15672"`, `"${RABBITMQ_PROMETHEUS_PORT:-15692}:15692"`
  - redis: `"${REDIS_HOST_PORT:-6379}:6379"`
  - api: `"${API_HOST_PORT:-8000}:8000"`
  - frontend: `"${FRONTEND_HOST_PORT:-3000}:80"`
  - grafana-alloy: `"${ALLOY_OTLP_GRPC_PORT:-4317}:4317"`, `"${ALLOY_OTLP_HTTP_PORT:-4318}:4318"`

### External Research
- #fetch:https://docs.docker.com/compose/networking/
  - Services on the same Docker network can communicate using service names
  - Port mappings (ports:) expose container ports to the host machine
  - No port mapping needed for inter-container communication on same network
  - Port exposure increases attack surface in production environments
- #githubRepo:"docker/docs" container networking best practices
  - Only expose ports that need to be accessed from outside the Docker network
  - Internal services (databases, message queues) should not expose ports in production
  - Port exposure should be environment-specific (development vs production vs test)

### Project Conventions
- Containerization best practices: `.github/instructions/containerization-docker-best-practices.instructions.md`
  - Security principle: minimize exposed ports to reduce attack surface
  - Network isolation: use Docker networks for inter-service communication
  - Environment-specific configuration: different port strategies for dev/test/prod

## Issues Discovered

### Issue 1: Unnecessary Port Exposure on Infrastructure Services

**Problem**: PostgreSQL, RabbitMQ (5672), and Redis expose ports to the host machine that are not needed for normal operation.

**Impact**:
- Increased attack surface in production/test environments
- Potential port conflicts when running multiple instances (test, dev, production)
- Security risk: databases and message brokers accessible from host without network isolation

**Current Behavior**:
- `postgres` exposes port 5432 to host via `${POSTGRES_HOST_PORT:-5432}:5432`
- `rabbitmq` exposes port 5672 to host via `${RABBITMQ_HOST_PORT:-5672}:5672`
- `redis` exposes port 6379 to host via `${REDIS_HOST_PORT:-6379}:6379`

**Why Ports Are Exposed**:
All application services (bot, api, notification-daemon, status-transition-daemon) connect to infrastructure services using internal Docker network names:
- `postgres:5432` (not `localhost:5432`)
- `rabbitmq:5672` (not `localhost:5672`)
- `redis:6379` (not `localhost:6379`)

**When Port Exposure IS Needed**:
- Development: Management/monitoring UIs (RabbitMQ:15672) for debugging
- Development/Test: Frontend (3000) and API (8000) for direct access
- Never needed in production (reverse proxy handles external access)

**When Port Exposure IS NOT Needed**:
- Infrastructure services (postgres:5432, rabbitmq:5672, redis:6379) - use `docker exec`
- Observability ports (4317, 4318, 15692) - Alloy collects via internal network
- Production: Frontend/API ports - reverse proxy handles external routing
- Production: Management UIs - not needed externally

### Issue 2: Port Configuration Missing from .env.example

**Problem**: Environment variables for controlling port exposure (POSTGRES_HOST_PORT, etc.) are not documented in `.env.example`.

**Impact**:
- Users unaware they can customize ports
- Port conflicts not easily resolvable
- No guidance on which ports are optional vs required

**Current State**:
- Port variables exist in docker-compose.base.yml with defaults
- Not documented in .env.example
- Users must read docker-compose files to discover port configuration options

## Recommended Approach

### Strategy: Minimal Port Exposure with Environment-Specific Overrides

**Base Configuration** (`docker-compose.base.yml`): Remove ALL port mappings
- No ports exposed by default
- Services communicate via internal Docker network
- Maximum security and flexibility

**Development Override** (`compose.override.yaml`): Add useful ports for local development
- Frontend: 3000 (direct browser access)
- API: 8000 (direct API testing)
- RabbitMQ Management UI: 15672 (monitoring/debugging)

**Production Configuration** (`compose.production.yaml`): No ports exposed
- Reverse proxy handles external routing to frontend/API
- No direct port access needed
- Management UIs not exposed externally
### Observability Port Analysis

**Grafana Alloy Architecture**:
- Alloy runs inside the Docker Compose network
- All services send telemetry to Alloy via internal network (grafana-alloy:4317, grafana-alloy:4318)
- RabbitMQ Prometheus metrics scraped internally (rabbitmq:15692)
- Alloy forwards aggregated data to Grafana Cloud
- **No external port exposure needed for observability**

**Management UI Ports**:
- RabbitMQ Management UI (15672): Useful for development debugging only
- Should be in development override, not base configuration
- Not needed in production or test environments
- Forces best practice of using `docker exec` for infrastructure access

### Keep Management/Monitoring Ports

**Ports to Keep Exposed** (useful in all environments):
- RabbitMQ Management UI: `15672` (useful for monitoring)
- RabbitMQ Prometheus metrics: `15692` (needed for Grafana Alloy)
- Grafana Alloy OTLP endpoints: `4317`, `4318` (needed for observability)

**Rationale**:
- Management UIs are secured by authentication
- Monitoring ports are needed for observability stack
### Documentation Updates

Update `.env.example`:
```bash
# Application Ports (exposed in development and test, not in production)
# Production uses reverse proxy for external access
API_HOST_PORT=8000
FRONTEND_HOST_PORT=3000

# Management UI Ports (development only)
# Note: Only exposed via compose.override.yaml for local development
# Production and test environments use 'docker exec' for debugging
RABBITMQ_MGMT_HOST_PORT=15672

# Note: Infrastructure service ports are NOT exposed
# Use 'docker exec' to access them for debugging:
#   docker exec -it gamebot-postgres psql -U gamebot -d game_scheduler
#   docker exec -it gamebot-redis redis-cli
#   docker exec -it gamebot-rabbitmq rabbitmqctl status
#
# Note: Observability ports are NOT exposed externally
# Grafana Alloy collects metrics/traces via internal Docker network
# Services connect to grafana-alloy:4317 (gRPC) and grafana-alloy:4318 (HTTP)
``` docker exec -it gamebot-redis redis-cli
#   docker exec -it gamebot-rabbitmq rabbitmqctl status
```

## Implementation Guidance

### Objectives
### Key Tasks

1. **Update docker-compose.base.yml**:
   - Remove ALL `ports:` sections from all services
   - Infrastructure services: postgres, rabbitmq, redis
   - Application services: api, frontend
   - Observability services: grafana-alloy
   - Services communicate only via internal network

2. **Update compose.override.yaml** (development):
   - Add frontend port mapping: `"${FRONTEND_HOST_PORT:-3000}:80"`
   - Add api port mapping: `"${API_HOST_PORT:-8000}:8000"`
   - Add rabbitmq management port: `"${RABBITMQ_MGMT_HOST_PORT:-15672}:15672"`

3. **Update docker-compose.test.yml** (test environments):
   - Add frontend port mapping: `"${FRONTEND_HOST_PORT:-3000}:80"`
   - Add api port mapping: `"${API_HOST_PORT:-8000}:8000"`
   - No management UI ports

4. **Verify compose.production.yaml**:
   - Should have NO port mappings
   - Reverse proxy handles external routing

5. **Update .env.example**:
   - Document that ports are environment-specific
   - Explain observability uses internal network only
   - Add `docker exec` examples for debugging

6. **Update documentation**:
### Success Criteria
- Base configuration exposes zero ports
- Development exposes: frontend (3000), api (8000), rabbitmq management (15672)
- Test exposes: frontend (3000), api (8000) only
- Production exposes: zero ports (reverse proxy handles routing)
- No observability ports exposed (internal collection by Alloy)
- Documentation clearly explains architecture and `docker exec` usage
- No port conflicts when running multiple environments simultaneously
- No regression in functionality (all services communicate via internal network)
   - Add section on using `docker exec` for infrastructure service access
   - Update troubleshooting guides to use `docker exec` instead of localhost connections
   - Document that no infrastructure ports are exposed by design
### Dependencies
- Docker Compose with multi-file support (already in use)
- Existing layered compose configuration structure

### Success Criteria
- Test environments expose no infrastructure ports by default
- Development environment exposes all ports for debugging
- Production environment exposes only application and monitoring ports
- Clear documentation about port configuration options
- No regression in functionality (services communicate via internal network)

### Success Criteria
- No infrastructure ports exposed in any environment
- Only application ports (8000, 3000) and monitoring ports (15672, 15692, 4317, 4318) exposed
- Documentation clearly explains `docker exec` usage for debugging
- No port conflicts when running multiple instances simultaneously
- No regression in functionality (services communicate via internal network)
- Docker Compose Networking: https://docs.docker.com/compose/networking/
- Project containerization standards: `.github/instructions/containerization-docker-best-practices.instructions.md`
- Current base configuration: `docker-compose.base.yml` (Lines 15-70)
- Development overrides: `compose.override.yaml`
- Test configuration: `docker-compose.test.yml`

### Issue 3: Game Host Not Receiving Notifications

**Problem**: Game reminders are sent only to participants, but the game host does not receive notification reminders even though they are hosting the game.

**Impact**:
- Game hosts may forget about games they are hosting
- No reminder when they need to prepare or show up
- Asymmetric experience: participants get reminders, host doesn't
- Particularly problematic for games where host has setup responsibilities

**Current Behavior**:
```python
# services/bot/events/handlers.py _handle_game_reminder_due()
# Filters to real participants only
real_participants = [p for p in game.participants if p.user_id and p.user]

# Sends reminders to confirmed participants
for participant in confirmed_participants:
    await self._send_reminder_dm(...)

# Sends reminders to waitlist participants  
for participant in overflow_participants:
    await self._send_reminder_dm(...)

# Host (game.host.discord_id) is NOT included in notification loop
```

**Analysis**:
- Game host is stored separately in `GameSession.host_id` (separate from participants)
- Notification logic only iterates through `game.participants` list
- Host is not in participants list (removed in Phase 6 refactor)
- Host receives no DM reminder at scheduled times

**Desired Behavior**:
- Game host should receive the same reminder DMs as confirmed participants
- Host notification should include their role (e.g., "Reminder: You are hosting...")
- Host should receive reminder even if there are no other participants
- Consistent with user expectation that creator gets notified about their event

**Implementation Approach**:
```python
# After sending to confirmed participants, also send to host
if game.host and game.host.discord_id:
    try:
        await self._send_reminder_dm(
            user_discord_id=game.host.discord_id,
            game_title=game.title,
            game_time_unix=game_time_unix,
            reminder_minutes=reminder_event.reminder_minutes,
            is_waitlist=False,
            is_host=True,  # New parameter to customize message
        )
    except Exception as e:
        logger.error(f"Failed to send reminder to host {game.host.discord_id}: {e}")
```

**Files Affected**:
- `services/bot/events/handlers.py` - `_handle_game_reminder_due()` method
- `services/bot/events/handlers.py` - `_send_reminder_dm()` method (add is_host parameter)

### Issue 4: Notify Roles Not Mentioned in Initial Game Announcement

**Problem**: When a game is created with `notify_role_ids`, the role mentions might not be triggering Discord notifications as expected.

**Impact**:
- Role-based notifications feature may not be working fully
- Users who want to be pinged about specific game types might miss announcements
- Reduced engagement for games that rely on role-based notifications

**Current Behavior**:
```python
# services/bot/formatters/game_message.py format_game_announcement()
# Role mentions are formatted in message content
content = None
if notify_role_ids:
    role_mentions = " ".join([f"<@&{role_id}>" for role_id in notify_role_ids])
    content = role_mentions

return content, embed, view

# services/bot/events/handlers.py _create_game_announcement()
return format_game_announcement(
    game_id=str(game.id),
    notify_role_ids=game.notify_role_ids or [],  # Passed correctly
    # ...
)
```

**Analysis**:
- `notify_role_ids` field exists in database (`GameSession.notify_role_ids`)
- Frontend allows setting notify roles during game creation
- Bot formatter has code to format role mentions
- Role mentions should appear above embed in message content
- Discord format: `<@&role_id>` triggers notification for users with that role

**Verification Needed**:
- Check if role IDs are actually being stored in database
- Verify `game.notify_role_ids` is populated when message is created
- Confirm role mentions are appearing in Discord message content
- Test that users with mentioned roles receive Discord notifications
- Verify role IDs are valid snowflake strings

**Potential Issues**:
- notify_role_ids not being loaded from database with game object
- notify_role_ids being None/empty when it should have values
- Role IDs format incorrect or invalid
- Discord message content not being sent properly
- Permissions issue preventing bot from mentioning roles

**Files to Check**:
- `services/bot/events/handlers.py` - `_handle_game_created()` method
- `services/bot/events/handlers.py` - `_get_game_with_participants()` query
- `services/bot/formatters/game_message.py` - `format_game_announcement()` function
- `shared/models/game.py` - `GameSession.notify_role_ids` field
- Database: Check actual stored values in game_sessions table

## Additional Issues To Be Added

*Note: User may have more issues to document. This research file will be updated as additional issues are identified.*

### Issue 5: Missing Game Completion Transition for Games Without Duration

**Problem**: Games transition from SCHEDULED → IN_PROGRESS at the scheduled time, but there's no automatic transition to COMPLETED status for games that don't have an `expected_duration_minutes` set. These games remain in IN_PROGRESS status indefinitely.

**Impact**:
- Games without duration stay IN_PROGRESS forever unless manually marked complete
- Historical game data inaccurate (games appear ongoing when they ended)
- Discord messages never update to show COMPLETED status
- Game lists cluttered with old "in progress" games
- No clear indication when game actually finished

**Current Behavior**:
```python
# Status transition lifecycle (from services/scheduler/utils/status_transitions.py)
def get_next_status(current_status: str) -> str | None:
    if current_status == GameStatus.SCHEDULED:
        return GameStatus.IN_PROGRESS  # ✓ Happens at scheduled_at time
    elif current_status == GameStatus.IN_PROGRESS:
        return GameStatus.COMPLETED    # ✗ Only if expected_duration_minutes set
    return None

# Game model (shared/models/game.py)
expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

# Status schedule creation (services/api/services/games.py)
# Creates transition to IN_PROGRESS at scheduled_at time
# Creates transition to COMPLETED at scheduled_at + expected_duration_minutes
# BUT: If expected_duration_minutes is None, no COMPLETED transition scheduled
```

**Analysis**:
- `expected_duration_minutes` field is optional (nullable)
- Status transition daemon creates COMPLETED schedule only when duration exists
- Games without duration never get a COMPLETED transition scheduled
- Two status transitions exist: SCHEDULED → IN_PROGRESS, IN_PROGRESS → COMPLETED
- First transition always happens, second only if duration specified

**Game Creation Flow**:
1. User creates game with `scheduled_at` but no `expected_duration_minutes`
2. `game_status_schedule` entry created: `transition_time = scheduled_at`, `target_status = IN_PROGRESS`
3. At scheduled time: daemon transitions game to IN_PROGRESS
4. No further status transitions scheduled
5. Game remains IN_PROGRESS indefinitely

**Desired Behavior**:
- Games without `expected_duration_minutes` should still transition to COMPLETED
- Use a default duration (e.g., 60 minutes) for games without explicit duration
- Alternative: Require duration to be set during game creation (prevent None)
- Alternative: Allow manual "Mark Complete" action but also have automatic fallback
- Completion transition should happen even for games without explicit end time

**Implementation Options**:

**Option 1: Default Duration (Recommended)**
```python
# When creating status schedule, use default if no duration specified
DEFAULT_GAME_DURATION_MINUTES = 60  # 1 hour default

if game.expected_duration_minutes:
    completion_time = game.scheduled_at + timedelta(minutes=game.expected_duration_minutes)
else:
    completion_time = game.scheduled_at + timedelta(minutes=DEFAULT_GAME_DURATION_MINUTES)

# Create COMPLETED transition schedule
status_schedule = GameStatusSchedule(
    game_id=game.id,
    target_status=GameStatus.COMPLETED.value,
    transition_time=completion_time,
    executed=False,
)
```

**Option 2: Require Duration at Creation**
```python
# In game creation validation
if not game_data.expected_duration_minutes:
    raise ValueError("expected_duration_minutes is required")
```

**Option 3: Prompt for Completion**
- Send notification to host after default duration
- Message: "Is [Game Title] complete? React to mark as done or specify additional time"
- Requires Discord interaction handling

**Recommendation**: Option 1 (Default Duration)
- Least disruptive to users
- Games naturally progress through full lifecycle
- Host can still manually override if needed
- Sensible default (1 hour) covers most casual games
- Easy to implement in existing status transition logic

**Files Affected**:
- `services/api/services/games.py` - `create_game()` and `update_game()` methods
- `services/api/services/games.py` - Status schedule creation logic
- Configuration/constants file - Add `DEFAULT_GAME_DURATION_MINUTES = 60`
- Frontend - Display default duration in UI when not specified
- Documentation - Explain default completion behavior

**Additional Considerations**:
- Should host receive notification when game auto-completes?
- Should completion notification differentiate between explicit duration vs default?
- Should default duration be configurable per guild/channel?
- What about very long games (all-day events, multi-session campaigns)?

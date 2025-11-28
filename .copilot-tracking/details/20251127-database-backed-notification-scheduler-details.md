<!-- markdownlint-disable-file -->
# Task Details: Database-Backed Event-Driven Notification Scheduler

## Research Reference

**Source Research**: #file:../research/20251127-database-backed-notification-scheduler-research.md

## Phase 1: Database Schema and Migration

### Task 1.1: Create Alembic migration for notification_schedule table

Create new Alembic migration `012_add_notification_schedule.py` with table and indexes.

- **Files**:
  - alembic/versions/012_add_notification_schedule.py - New migration file
- **Success**:
  - Migration creates `notification_schedule` table with UUID primary key
  - Foreign key to `game_sessions(id)` with ON DELETE CASCADE
  - Unique constraint on (game_id, reminder_minutes)
  - Partial index on notification_time WHERE sent = FALSE
  - Index on game_id for cleanup queries
  - Migration runs successfully with `alembic upgrade head`
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 65-89) - Database schema design
  - alembic/versions/011_add_expected_duration_minutes.py - Migration pattern reference
- **Dependencies**:
  - None

### Task 1.2: Add PostgreSQL trigger for LISTEN/NOTIFY

Add PostgreSQL function and trigger in same migration to send NOTIFY events.

- **Files**:
  - alembic/versions/012_add_notification_schedule.py - Add trigger in upgrade()
- **Success**:
  - Function `notify_schedule_changed()` created in PostgreSQL
  - Trigger fires on INSERT/UPDATE/DELETE of notification_schedule
  - NOTIFY sent to 'notification_schedule_changed' channel
  - Payload includes operation, game_id, notification_time as JSON
  - Only notifies for near-term changes (within 10 minutes)
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 91-118) - PostgreSQL trigger implementation
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Notification Daemon Core

### Task 2.1: Create PostgreSQL LISTEN/NOTIFY client

Create `services/scheduler/postgres_listener.py` with connection management.

- **Files**:
  - services/scheduler/postgres_listener.py - New LISTEN/NOTIFY client
- **Success**:
  - Class `PostgresNotificationListener` with psycopg2 connection
  - `connect()` method sets ISOLATION_LEVEL_AUTOCOMMIT
  - `listen(channel)` subscribes to notification channel
  - `wait_for_notification(timeout)` returns (received, payload) tuple
  - Handles reconnection on connection loss
  - Uses select.select() for timeout-based waiting
  - Parses JSON payloads from NOTIFY
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 216-258) - psycopg2 LISTEN/NOTIFY implementation
- **Dependencies**:
  - Task 1.2 completion (trigger must exist)

### Task 2.2: Implement notification schedule queries

Create `services/scheduler/schedule_queries.py` with database query functions.

- **Files**:
  - services/scheduler/schedule_queries.py - New query module
- **Success**:
  - `get_next_due_notification()` returns MIN(notification_time) record
  - `get_due_notifications(buffer_seconds)` returns all due notifications with FOR UPDATE SKIP LOCKED
  - `mark_notification_sent(notification_id)` updates sent flag
  - All queries use synchronous SQLAlchemy with get_sync_db_session
  - Proper error handling and logging
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 120-156) - Scheduler loop algorithm
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 260-304) - Batch processing with locking
- **Dependencies**:
  - Task 1.1 completion (table must exist)

### Task 2.3: Create main notification daemon loop

Create `services/scheduler/notification_daemon.py` with main loop logic.

- **Files**:
  - services/scheduler/notification_daemon.py - Main daemon implementation
- **Success**:
  - Main loop queries MIN(notification_time) for next due
  - Calculates wait time with 10-second buffer
  - Waits for earliest of: due time, NOTIFY event, or 5-minute timeout
  - Processes all due notifications in batch using FOR UPDATE SKIP LOCKED
  - Publishes game.reminder_due events to RabbitMQ via SyncEventPublisher
  - Marks notifications as sent after successful publish
  - Handles exceptions without crashing daemon
  - Logs all state transitions and decisions
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 120-156) - Complete scheduler loop algorithm
- **Dependencies**:
  - Task 2.1 completion (LISTEN client)
  - Task 2.2 completion (query functions)

### Task 2.4: Add daemon entry point and configuration

Create daemon main entry point and configuration.

- **Files**:
  - services/scheduler/notification_daemon.py - Add __main__ block
  - services/scheduler/config.py - Add daemon configuration if needed
- **Success**:
  - Can run with `uv run python -m services.scheduler.notification_daemon`
  - Graceful shutdown on SIGTERM/SIGINT
  - Proper logging configuration
  - Database connection established on startup
  - LISTEN connection established on startup
  - All configuration from environment variables
- **Research References**:
  - services/scheduler/beat.py - Entry point pattern reference
- **Dependencies**:
  - Task 2.3 completion

## Phase 3: API Integration

### Task 3.1: Add schedule population on game creation

Add schedule population logic to API game creation endpoint.

- **Files**:
  - services/api/routes/games.py - Modify game creation endpoint
  - services/api/services/notification_schedule.py - New helper module (optional)
- **Success**:
  - When game created, calculate all notification times
  - Resolve reminder_minutes via game → channel → guild inheritance
  - Insert notification_schedule records for each future reminder
  - All inserts in same transaction as game creation
  - PostgreSQL trigger automatically sends NOTIFY
  - Handle empty reminder_minutes gracefully
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 158-214) - Game event handlers
  - services/scheduler/tasks/check_notifications.py (Lines 127-147) - Existing _resolve_reminder_minutes logic
- **Dependencies**:
  - Task 1.2 completion (trigger must exist)

### Task 3.2: Add schedule updates on game modification

Add schedule update logic to API game update endpoint.

- **Files**:
  - services/api/routes/games.py - Modify game update endpoint
- **Success**:
  - When game.scheduled_at changes, recalculate notification schedule
  - When game.reminder_minutes changes, recalculate schedule
  - DELETE old schedule records for game
  - INSERT new schedule records based on updated values
  - Mark unsent notifications as sent=FALSE to allow re-scheduling
  - All updates in same transaction as game modification
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 158-214) - Game event handlers with ON CONFLICT logic
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Add schedule cleanup on game deletion

Ensure schedule records deleted when game is deleted.

- **Files**:
  - No code changes needed (CASCADE handles this)
  - Verify CASCADE behavior in tests
- **Success**:
  - ON DELETE CASCADE automatically removes notification_schedule records
  - Test verifies records deleted when game deleted
  - No orphaned schedule records remain
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 65-89) - Foreign key with CASCADE
- **Dependencies**:
  - Task 1.1 completion

## Phase 4: Docker and Deployment

### Task 4.1: Create notification daemon Docker entrypoint

Create entrypoint script for notification daemon container.

- **Files**:
  - docker/notification-daemon-entrypoint.sh - New entrypoint script
- **Success**:
  - Script runs Alembic migrations before starting daemon
  - Starts notification daemon with proper Python module path
  - Passes through all environment variables
  - Executable permissions set
- **Research References**:
  - docker/scheduler-entrypoint.sh - Existing pattern reference
- **Dependencies**:
  - Task 2.4 completion

### Task 4.2: Add daemon service to docker-compose.yml

Add notification-daemon service to docker-compose configuration.

- **Files**:
  - docker-compose.yml - Add new service definition
- **Success**:
  - Service named `notification-daemon`
  - Uses scheduler Dockerfile
  - Overrides entrypoint to notification-daemon-entrypoint.sh
  - Depends on postgres and rabbitmq
  - Uses same environment variables as scheduler
  - Connects to gamebot-network
  - Healthcheck verifies process running
- **Research References**:
  - docker-compose.yml (Lines 1-200) - Existing service patterns
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Update scheduler Dockerfile for daemon

Ensure Dockerfile includes notification daemon files.

- **Files**:
  - docker/scheduler.Dockerfile - Verify includes all scheduler files
- **Success**:
  - notification_daemon.py included in image
  - postgres_listener.py included in image
  - schedule_queries.py included in image
  - notification-daemon-entrypoint.sh copied to image
  - No separate Dockerfile needed (reuses scheduler image)
- **Research References**:
  - docker/scheduler.Dockerfile - Current Dockerfile
- **Dependencies**:
  - Task 4.1 completion

## Phase 5: Testing

### Task 5.1: Create unit tests for daemon components

Create unit tests for LISTEN client and query functions.

- **Files**:
  - tests/services/scheduler/test_postgres_listener.py - LISTEN client tests
  - tests/services/scheduler/test_schedule_queries.py - Query function tests
- **Success**:
  - Test PostgresNotificationListener connection lifecycle
  - Test wait_for_notification timeout behavior
  - Test wait_for_notification with actual NOTIFY
  - Test get_next_due_notification with various scenarios
  - Test get_due_notifications batch processing
  - Test mark_notification_sent updates database
  - Mock external dependencies appropriately
  - All tests pass with pytest
- **Research References**:
  - tests/services/ - Existing test structure
- **Dependencies**:
  - Tasks 2.1, 2.2 completion

### Task 5.2: Create integration tests with PostgreSQL LISTEN/NOTIFY

Create integration tests with real PostgreSQL database.

- **Files**:
  - tests/integration/test_notification_daemon.py - Integration tests
- **Success**:
  - Test trigger sends NOTIFY on INSERT to notification_schedule
  - Test daemon wakes up on NOTIFY within 2 seconds
  - Test daemon processes due notifications correctly
  - Test daemon publishes correct RabbitMQ events
  - Test daemon handles database connection loss
  - Use test database fixture with actual PostgreSQL
  - All tests pass with pytest
- **Research References**:
  - tests/integration/ - Existing integration test patterns
- **Dependencies**:
  - Tasks 2.1, 2.2, 2.3 completion

### Task 5.3: Create end-to-end notification flow tests

Create end-to-end tests simulating complete flow.

- **Files**:
  - tests/integration/test_notification_flow_e2e.py - E2E tests
- **Success**:
  - Test: Create game → schedule populated → daemon sends notification
  - Test: Update game.scheduled_at → schedule recalculated → notifications sent at new times
  - Test: Delete game → schedule cleaned up
  - Test: Daemon restart → resumes from database state
  - Test: Multiple games with overlapping notification times
  - All tests pass with pytest
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 372-411) - Migration strategy
- **Dependencies**:
  - Phase 3 completion (API integration)

## Phase 6: Cleanup and Documentation

### Task 6.1: Remove old Celery notification tasks

Remove deprecated Celery task files and configuration.

- **Files**:
  - services/scheduler/tasks/check_notifications.py - DELETE file
  - services/scheduler/tasks/send_notification.py - DELETE file
  - services/scheduler/celery_app.py - Remove check-notifications beat schedule
  - services/scheduler/utils/notification_windows.py - DELETE if unused elsewhere
- **Success**:
  - Old task files deleted
  - Celery beat schedule no longer includes check_notifications
  - No imports reference deleted modules
  - Celery worker still functional for update_game_status
  - All tests still pass
- **Research References**:
  - services/scheduler/celery_app.py (Lines 20-35) - Beat schedule to modify
- **Dependencies**:
  - All previous phases complete and tested

### Task 6.2: Remove Redis deduplication code

Remove Redis-based notification deduplication since database handles it.

- **Files**:
  - services/scheduler/tasks/check_notifications.py - Already deleted in 6.1
  - Verify no other references to notification_sent: keys
- **Success**:
  - No code references notification_sent:{key} Redis pattern
  - grep confirms no usage of _notification_already_sent pattern
  - Database sent flag is sole deduplication mechanism
- **Research References**:
  - services/scheduler/tasks/check_notifications.py (Lines 148-160) - Redis deduplication code
- **Dependencies**:
  - Task 6.1 completion

### Task 6.3: Update documentation and README

Update project documentation with new architecture.

- **Files**:
  - README.md - Update architecture section
  - Add docs/architecture/notification-scheduler.md if detailed docs exist
- **Success**:
  - README explains database-backed notification scheduler
  - Diagram shows: Database → Daemon → RabbitMQ → Bot flow
  - Documents MIN() query pattern and LISTEN/NOTIFY mechanism
  - Explains unlimited notification window capability
  - Notes removed Celery dependency for notifications
  - Instructions for running notification daemon
- **Research References**:
  - #file:../research/20251127-database-backed-notification-scheduler-research.md (Lines 1-64) - Architecture summary
- **Dependencies**:
  - All implementation complete

## Dependencies

- psycopg2-binary>=2.9.0 (already installed in pyproject.toml)
- sqlalchemy[asyncio]>=2.0.0 (already installed)
- PostgreSQL 15+ with LISTEN/NOTIFY support

## Success Criteria

- All 18 tasks completed and checked off
- Database migration runs successfully
- Notification daemon starts and processes notifications
- <10 second latency from due time to RabbitMQ publish
- All unit, integration, and E2E tests pass
- Old Celery notification code removed
- Documentation updated

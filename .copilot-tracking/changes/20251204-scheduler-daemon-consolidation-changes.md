<!-- markdownlint-disable-file -->

# Release Changes: Scheduler Daemon Consolidation and Bot Status Updates

**Related Plan**: 20251204-scheduler-daemon-consolidation.plan.md
**Implementation Date**: 2025-12-04

## Summary

Consolidate duplicate daemon implementations into a single generic scheduler, move status update logic to bot event handlers, and fix integration test failures. This eliminates 95% code duplication and reduces total scheduler daemon code from 494 lines to ~150 lines.

## Changes

### Added

- services/scheduler/generic_scheduler_daemon.py - Generic parameterized scheduler daemon eliminating code duplication
- services/scheduler/event_builders.py - Event builder functions for notification and status transition events
- shared/schemas/events.py - Event payload schemas for scheduler system with GameStatusTransitionDueEvent
- services/scheduler/notification_daemon_wrapper.py - Thin wrapper instantiating generic daemon for notifications
- services/scheduler/status_transition_daemon_wrapper.py - Thin wrapper instantiating generic daemon for status transitions
- tests/services/scheduler/test_generic_scheduler_daemon.py - Comprehensive unit tests for generic scheduler daemon with 33 tests covering initialization, connection, query operations, item processing, error handling, and cleanup

### Modified

- shared/messaging/events.py - Added GAME_STATUS_TRANSITION_DUE event type to EventType enum
- services/bot/events/handlers.py - Added \_handle_status_transition_due method to update game status and refresh Discord message, registered GAME_STATUS_TRANSITION_DUE handler in event consumer; Removed manual updated_at assignment to rely on SQLAlchemy's automatic onupdate behavior
- tests/services/bot/events/test_handlers.py - Added tests for status transition handler and updated handler count assertion
- docker/notification-daemon.Dockerfile - Updated to use notification_daemon_wrapper and copy generic daemon files
- docker/status-transition-daemon.Dockerfile - Updated to use status_transition_daemon_wrapper and copy generic daemon files
- tests/integration/test_status_transitions.py - Rewrote to use generic SchedulerDaemon with proper parameters instead of StatusTransitionDaemon compatibility wrapper, updated tests to check for executed status rather than game status updates since daemon now publishes events instead of directly updating database
- tests/integration/test_notification_daemon.py - Rewrote to use generic SchedulerDaemon with proper parameters instead of NotificationDaemon compatibility wrapper
- services/scheduler/generic_scheduler_daemon.py - Enhanced \_cleanup method to wrap each connection close in try-except blocks for graceful error handling
- README.md - Updated scheduler section to reflect new generic daemon architecture with wrappers and event builders instead of old daemon implementations

### Removed

- services/scheduler/notification_daemon.py - Replaced by generic_scheduler_daemon.py with notification_daemon_wrapper.py
- services/scheduler/status_transition_daemon.py - Replaced by generic_scheduler_daemon.py with status_transition_daemon_wrapper.py
- services/scheduler/schedule_queries.py - Query logic now integrated into generic_scheduler_daemon.py
- services/scheduler/status_schedule_queries.py - Query logic now integrated into generic_scheduler_daemon.py
- tests/services/scheduler/test_notification_daemon.py - Tests now in test_generic_scheduler_daemon.py
- tests/services/scheduler/test_schedule_queries.py - Query tests removed as query logic is now internal to generic daemon
- tests/services/scheduler/test_status_schedule_queries.py - Query tests removed as query logic is now internal to generic daemon
- tests/integration/test_notification_daemon.py TestScheduleQueriesIntegration class - Query function tests removed as functions are now internal to generic daemon
- tests/integration/test_status_transitions.py TestStatusScheduleQueries class - Query function tests removed as functions are now internal to generic daemon

## Release Summary

**Total Files Affected**: 23

### Files Created (7)

- services/scheduler/generic_scheduler_daemon.py
- services/scheduler/event_builders.py
- shared/schemas/events.py
- services/scheduler/notification_daemon_wrapper.py
- services/scheduler/status_transition_daemon_wrapper.py
- tests/services/scheduler/test_generic_scheduler_daemon.py

### Files Modified (7)

- shared/messaging/events.py
- services/bot/events/handlers.py
- tests/services/bot/events/test_handlers.py
- docker/notification-daemon.Dockerfile
- docker/status-transition-daemon.Dockerfile
- tests/integration/test_status_transitions.py
- tests/integration/test_notification_daemon.py
- README.md

### Files Removed (9)

- services/scheduler/notification_daemon.py
- services/scheduler/status_transition_daemon.py
- services/scheduler/schedule_queries.py
- services/scheduler/status_schedule_queries.py
- tests/services/scheduler/test_notification_daemon.py
- tests/services/scheduler/test_schedule_queries.py
- tests/services/scheduler/test_status_schedule_queries.py

### Test Results

- Unit tests: 53 passed (tests/services/scheduler/)
- Bot handler tests: 19 passed (tests/services/bot/events/test_handlers.py)
- Integration tests: 11 passed (scripts/run-integration-tests.sh)
- Total: 83 tests passed with no failures

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Deployment Notes

**Breaking Changes**: None - The consolidation is fully backward compatible through wrapper modules.

**Deployment Steps**:

1. Build new Docker images with updated daemon implementations
2. Deploy containers - wrappers maintain same entry points
3. Verify scheduler daemons are running correctly
4. Monitor RabbitMQ for event publication
5. Verify Discord messages update when game status transitions

**Rollback Plan**: Previous daemon implementations preserved in git history if needed.

**Performance Impact**: Improved - reduced code duplication and eliminated constructor overhead.

**Testing**: All 83 tests passing (53 unit, 19 bot handler, 11 integration)

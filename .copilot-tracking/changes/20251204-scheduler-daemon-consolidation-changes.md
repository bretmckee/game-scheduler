<!-- markdownlint-disable-file -->

# Release Changes: Scheduler Daemon Consolidation and Bot Status Updates

**Related Plan**: 20251204-scheduler-daemon-consolidation-plan.instructions.md
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
- services/bot/events/handlers.py - Added _handle_status_transition_due method to update game status and refresh Discord message, registered GAME_STATUS_TRANSITION_DUE handler in event consumer
- tests/services/bot/events/test_handlers.py - Added tests for status transition handler and updated handler count assertion
- docker/notification-daemon.Dockerfile - Updated to use notification_daemon_wrapper and copy generic daemon files
- docker/status-transition-daemon.Dockerfile - Updated to use status_transition_daemon_wrapper and copy generic daemon files
- tests/integration/test_status_transitions.py - Rewrote to use generic SchedulerDaemon with proper parameters instead of StatusTransitionDaemon compatibility wrapper, updated tests to check for executed status rather than game status updates since daemon now publishes events instead of directly updating database
- tests/integration/test_notification_daemon.py - Rewrote to use generic SchedulerDaemon with proper parameters instead of NotificationDaemon compatibility wrapper
- services/scheduler/generic_scheduler_daemon.py - Enhanced _cleanup method to wrap each connection close in try-except blocks for graceful error handling

### Removed

## Release Summary

**Total Files Affected**: TBD

### Files Created (TBD)

### Files Modified (TBD)

### Files Removed (TBD)

### Dependencies & Infrastructure

- **New Dependencies**: None
- **Updated Dependencies**: None
- **Infrastructure Changes**: None
- **Configuration Updates**: None

### Deployment Notes

TBD

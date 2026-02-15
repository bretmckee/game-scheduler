<!-- markdownlint-disable-file -->

# Release Changes: Integration Test Daemon Pattern Rewrite

**Related Plan**: 20251226-integration-test-daemon-rewrite.plan.md
**Implementation Date**: 2025-12-26

## Summary

Rewrite integration tests for notification daemon and status transition daemon to test running daemon services instead of creating conflicting SchedulerDaemon instances. Align with retry daemon test pattern using event-driven PostgreSQL LISTEN/NOTIFY mechanism.

## Changes

### Added

- tests/integration/conftest.py - Created shared fixtures with rabbitmq_url, rabbitmq_connection, and rabbitmq_channel for integration tests
- tests/shared/polling.py - Created shared polling utilities module with wait_for_db_condition_async and wait_for_db_condition_sync for polling database conditions with timeouts
- tests/shared/polling.py - Refactored to extract core polling logic into \_poll_until_condition_async and \_poll_until_condition_sync helpers, fixing timeout check to occur before database query

### Modified

- tests/integration/test_notification_daemon.py - Added get_queue_message_count and consume_one_message helper functions
- tests/integration/test_status_transitions.py - Added get_queue_message_count and consume_one_message helper functions
- tests/integration/test_notification_daemon.py - Rewrote test_daemon_processes_due_notification to test running daemon service without instantiating SchedulerDaemon
- tests/integration/test_notification_daemon.py - Updated TestNotificationDaemonIntegration class docstring to reflect testing of running daemon service
- tests/integration/test_notification_daemon.py - Removed SchedulerDaemon and NotificationSchedule imports, added QUEUE_BOT_EVENTS import
- tests/integration/test_notification_daemon.py - Replaced fixed time.sleep(2) with wait_for_db_condition_sync polling utility for reliable daemon processing verification
- tests/e2e/conftest.py - Refactored wait_for_db_condition to delegate to shared wait_for_db_condition_async from tests.shared.polling module
- tests/integration/test_notification_daemon.py - Rewrote test_daemon_waits_for_future_notification to test running daemon without instantiating SchedulerDaemon, verifying future notifications aren't processed prematurely
- Skipped Task 2.3 (test_daemon_marks_notification_as_processed) and Task 2.4 (test_daemon_publishes_correct_event_type) as these tests do not exist and functionality is already validated in test_daemon_processes_due_notification
- tests/integration/test_status_transitions.py - Removed unused imports (threading, daemon_module, build_status_transition_event, SchedulerDaemon, GameStatusSchedule), added QUEUE_BOT_EVENTS and wait_for_db_condition_sync imports
- tests/integration/test_status_transitions.py - Rewrote test_daemon_transitions_game_status_when_due to test running status-transition-daemon service without instantiating SchedulerDaemon, using wait_for_db_condition_sync for reliable validation
- tests/integration/test_status_transitions.py - Updated TestStatusTransitionDaemonIntegration class docstring to reflect testing of running daemon service
- tests/integration/test_status_transitions.py - Removed unused reset_shutdown_flag fixture
- tests/integration/test_status_transitions.py - Rewrote test_daemon_waits_for_future_transition to test running daemon without instantiating SchedulerDaemon, verifying future transitions aren't processed prematurely
- Skipped Task 3.3 (test_status_transition_daemon_handles_cancellation) as this test does not exist

### Removed

- tests/integration/test_notification_daemon.py - Removed test_daemon_connects_to_database test that instantiates SchedulerDaemon instead of testing running daemon service
- tests/integration/test_status_transitions.py - Removed test_daemon_handles_multiple_due_transitions test that creates own daemon instance with threading instead of testing running daemon service

### Added Queue Isolation (Phase 4)

- tests/integration/test_notification_daemon.py - Integrated queue cleanup into clean_notification_schedule fixture (deletes DB records, waits 0.5s, purges queue before/after tests)
- tests/integration/test_status_transitions.py - Integrated queue cleanup into clean_game_status_schedule fixture (deletes DB records, waits 0.5s, purges queue before/after tests)
- Added sleep delays to allow daemon to process any remaining records before purging queue
- Ensures proper cleanup order: database deletion → daemon processing → queue purge

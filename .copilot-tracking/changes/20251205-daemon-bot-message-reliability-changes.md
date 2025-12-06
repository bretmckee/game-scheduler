<!-- markdownlint-disable-file -->

# Release Changes: Daemon-Bot Message Reliability and Error Handling

**Related Plan**: 20251205-daemon-bot-message-reliability-plan.instructions.md
**Implementation Date**: 2025-12-05

## Summary

Fix critical message loss bug in bot consumer and implement daemon-based DLQ processing with per-message TTL for notifications to ensure reliable event delivery and data consistency.

## Changes

### Added

- alembic/versions/021_add_game_scheduled_at_to_notification_schedule.py - Database migration adding game_scheduled_at column to notification_schedule table with backfill

### Modified

- shared/models/notification_schedule.py - Added game_scheduled_at field to NotificationSchedule model
- services/api/services/notification_schedule.py - Updated populate_schedule to include game_scheduled_at when creating notifications
- tests/services/api/services/test_notification_schedule.py - Enhanced test assertions to verify game_scheduled_at field
- tests/integration/test_notification_daemon.py - Updated test fixtures to include game_scheduled_at in INSERT statements
- scripts/run-integration-tests.sh - Added init container to rebuild list to ensure migrations run

### Removed


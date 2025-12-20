<!-- markdownlint-disable-file -->

# Release Changes: Delayed Join Notification with Conditional Signup Instructions

**Related Plan**: 20251218-signup-instructions-dm-plan.instructions.md
**Implementation Date**: 2025-12-20

## Summary

Replace immediate join confirmation DMs with single 60-second delayed notification that conditionally includes signup instructions when present, using existing notification_schedule infrastructure.

## Changes

### Added

#### Database Migration
- [alembic/versions/bcecd82ff82f_add_notification_type_participant_id.py](alembic/versions/bcecd82ff82f_add_notification_type_participant_id.py) - New migration adding notification_type and participant_id columns
  - Adds `notification_type` column (String(50), default='reminder') for distinguishing reminder vs join notifications
  - Adds `participant_id` column (nullable FK to game_participants.id) for participant-specific notifications
  - Creates CASCADE delete constraint on participant_id (auto-cancels notification when participant leaves)
  - Adds index on participant_id for efficient lookups
  - Adds composite index on (notification_type, notification_time) for efficient daemon queries
  - Both upgrade() and downgrade() paths tested

#### Integration Tests
- [tests/integration/test_database_infrastructure.py](tests/integration/test_database_infrastructure.py#L150-L262) - Added three new tests
  - `test_notification_schedule_schema()` - Verifies all columns exist with correct types, nullability, and defaults
  - `test_notification_schedule_indexes()` - Verifies all required indexes including new ones
  - `test_notification_schedule_foreign_keys()` - Verifies both game_id and participant_id FKs with CASCADE delete

### Modified

#### Database Models
- [shared/models/notification_schedule.py](shared/models/notification_schedule.py#L37-L52) - Extended NotificationSchedule model
  - Added `notification_type: Mapped[str]` field with default='reminder'
  - Added `participant_id: Mapped[str | None]` field with FK to game_participants.id
  - Added `participant` relationship to GameParticipant model
  - Added TYPE_CHECKING import for GameParticipant
  - Updated docstring to document both notification types

#### Event System
- [shared/messaging/events.py](shared/messaging/events.py#L53-L57) - Renamed and updated event type and payload
  - Renamed `GAME_REMINDER_DUE` to `NOTIFICATION_DUE` for generalized notifications
  - Replaced `GameReminderDueEvent` with `NotificationDueEvent` model
  - Added `notification_type: str` field for routing ('reminder' or 'join_notification')
  - Added `participant_id: str | None` field for participant-specific notifications
  - Removed `reminder_minutes` field (kept only in database for schedule management)

#### Event Builders
- [services/scheduler/event_builders.py](services/scheduler/event_builders.py#L29-L57) - Renamed and updated event builder
  - Renamed `build_game_reminder_event` to `build_notification_event`
  - Updated to use `NotificationDueEvent` instead of `GameReminderDueEvent`
  - Populates `notification_type` and `participant_id` from schedule
  - Maintained TTL calculation logic for message expiration

#### Daemon Wrapper
- [services/scheduler/notification_daemon_wrapper.py](services/scheduler/notification_daemon_wrapper.py#L32-L73) - Updated event builder reference
  - Changed import from `build_game_reminder_event` to `build_notification_event`
  - Updated `event_builder` parameter in SchedulerDaemon instantiation
  - No other changes needed (daemon handles both notification types)

#### Schedule Creation
- [services/api/services/notification_schedule.py](services/api/services/notification_schedule.py#L137-L173) - Added join notification helper
  - New `schedule_join_notification()` function creates delayed notifications
  - Takes db, game_id, participant_id, game_scheduled_at, delay_seconds (default: 60)
  - Creates NotificationSchedule with notification_type='join_notification'
  - Sets notification_time to utc_now() + delay
  - CASCADE delete handles automatic cancellation when participant leaves
  - Added utc_now import from shared.models.base

- [services/api/services/games.py](services/api/services/games.py#L38-L883) - Updated API service for schedule creation
  - Added import for `schedule_join_notification`
  - `join_game()` creates schedule after participant commit (line ~883)
  - `_add_new_mentions()` creates schedules for Discord users only (lines ~558-583)
  - Schedules have 60-second delay before notification
  - No immediate success messages sent

- [services/bot/handlers/join_game.py](services/bot/handlers/join_game.py#L23-L95) - Removed immediate DM, added schedule creation
  - Added imports: timedelta, utc_now, NotificationSchedule
  - Removed immediate "You've joined" DM via send_success_message
  - Creates NotificationSchedule after participant commit
  - Sets notification_type='join_notification', 60-second delay
  - Button interaction updates view with join confirmation (no DM)
  - Schedule auto-cancelled if participant removed (CASCADE delete)

#### Bot Event Handlers
- [services/bot/events/handlers.py](services/bot/events/handlers.py#L40-L575) - Renamed handler, added routing, implemented join notifications
  - Updated import from `GameReminderDueEvent` to `NotificationDueEvent`
  - Updated `__init__` handler mapping: `NOTIFICATION_DUE` → `_handle_notification_due`
  - Updated consumer registration for `NOTIFICATION_DUE`
  - Renamed `_handle_game_reminder_due` to `_handle_notification_due` with routing logic
  - Routes 'reminder' type to `_handle_game_reminder()` (extracted existing logic)
  - Routes 'join_notification' type to `_handle_join_notification()` (new handler)
  - `_handle_game_reminder()` updated to use reminder_minutes=0 (not used in message formatting)
  - `_handle_join_notification()` queries participant, checks waitlist status
  - Conditional message: includes signup_instructions if present, generic message if not
  - Skips notification if participant no longer exists or is waitlisted

#### Unit Tests
- [tests/services/scheduler/test_event_builders.py](tests/services/scheduler/test_event_builders.py) - Updated all event builder tests (9 tests ✅)
  - Renamed class to `TestBuildNotificationEvent`
  - Updated all tests to use `build_notification_event`
  - Added test for join_notification event type
  - All tests passing with new event structure

- [tests/services/bot/events/test_handlers.py](tests/services/bot/events/test_handlers.py) - Updated bot handler tests (12 tests ✅)
  - Updated initialization test for `NOTIFICATION_DUE` event type
  - Updated 5 game reminder tests to use `_handle_notification_due` with `notification_type='reminder'`
  - Added 4 new join notification tests:
    - With signup instructions - verifies instructions included in DM
    - Without signup instructions - verifies generic message
    - Missing participant_id - verifies graceful handling
    - User not found - verifies logging when participant doesn't exist
  - All reminder and join notification tests passing

#### Integration Tests
- CASCADE delete behavior verified by existing database infrastructure tests (Phase 1)
- NotificationSchedule schema, indexes, and FK constraints validated in test_database_infrastructure.py
- No additional integration tests needed (redundant with Phase 1)

### Removed

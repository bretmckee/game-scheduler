<!-- markdownlint-disable-file -->
# Task Details: Scheduler Daemon Consolidation and Bot Status Updates

## Research Reference

**Source Research**: #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md

## Phase 1: Create Generic Scheduler Daemon

### Task 1.1: Create generic scheduler daemon base class

Create `services/scheduler/generic_scheduler_daemon.py` with parameterized scheduler that eliminates code duplication.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - New generic daemon implementation
- **Success**:
  - Generic daemon accepts configuration parameters for schedule type, event builder, and query functions
  - Core scheduling algorithm is unified and reusable
  - No buffer_seconds parameter (use exact time triggering)
  - Supports PostgreSQL LISTEN/NOTIFY for efficient wake-up
  - Publishes events to RabbitMQ when scheduled items are due
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 152-208) - Generic daemon design pattern and instantiation examples
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 116-150) - Shared algorithm pattern and duplication analysis
- **Dependencies**:
  - PostgreSQL database with LISTEN/NOTIFY support
  - RabbitMQ message broker
  - SQLAlchemy for database queries
  - Pika for RabbitMQ publishing

**Implementation Details**:
- Class constructor should accept: database_url, rabbitmq_url, notify_channel, model_class, time_field, status_field, event_builder, max_timeout
- Main loop queries next due item using generic query function
- Uses PostgreSQL listener to wake on schedule changes
- Processes due items by building event, publishing to RabbitMQ, marking processed in database
- All datetime operations use UTC timezone

### Task 1.2: Implement generic query functions

Create query functions that work with any schedule model class using reflection.

- **Files**:
  - services/scheduler/generic_scheduler_daemon.py - Add generic query methods
- **Success**:
  - get_next_due_item() queries MIN(time_field) WHERE status_field=False
  - mark_item_processed() updates status_field=True for given ID
  - Functions work with both NotificationSchedule and GameStatusSchedule models
  - Queries use proper UTC timezone handling
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 13-23) - Query function analysis showing identical patterns
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 116-150) - Query logic comparison table
- **Dependencies**:
  - Task 1.1 completion
  - SQLAlchemy model classes (NotificationSchedule, GameStatusSchedule)
  - Database session management

**Implementation Details**:
- Use SQLAlchemy's getattr() to access dynamic field names
- Query filters: status_field == False AND time_field IS NOT NULL
- Order by time_field ASC, limit 1 for next due item
- Update operations use model.id as primary key

### Task 1.3: Implement event builder pattern

Create event builder functions for each schedule type that construct appropriate event payloads.

- **Files**:
  - services/scheduler/event_builders.py - New file with builder functions
- **Success**:
  - build_game_reminder_event() creates GAME_REMINDER_DUE event from NotificationSchedule
  - build_status_transition_event() creates GAME_STATUS_TRANSITION_DUE event from GameStatusSchedule
  - Event builders follow consistent pattern and return Event objects
  - Payload schemas match event type requirements
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 152-208) - Event builder callable pattern
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 220-230) - GameStatusTransitionDueEvent payload specification
- **Dependencies**:
  - Task 1.1 completion
  - shared/messaging/events.py (Event, EventType)
  - Model classes with required fields

**Implementation Details**:
- Builders take schedule model instance as parameter
- Return Event object with event_type and data dictionary
- GameReminderDueEvent includes: game_id, notification_time
- GameStatusTransitionDueEvent includes: game_id, target_status, transition_time

## Phase 2: Add Status Transition Event Support

### Task 2.1: Add GAME_STATUS_TRANSITION_DUE event type and schema

Add new event type to messaging system for status transitions.

- **Files**:
  - shared/messaging/events.py - Add EventType.GAME_STATUS_TRANSITION_DUE
  - shared/schemas/events.py - Add GameStatusTransitionDueEvent schema
- **Success**:
  - GAME_STATUS_TRANSITION_DUE added to EventType enum
  - GameStatusTransitionDueEvent schema validates required fields
  - Schema includes game_id (UUID), target_status (str), transition_time (datetime)
  - Event type follows naming convention: "game.status_transition_due"
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 210-230) - Event type and payload specification
- **Dependencies**:
  - Existing event messaging infrastructure

**Implementation Details**:
- Add to EventType enum: GAME_STATUS_TRANSITION_DUE = "game.status_transition_due"
- Schema class inherits from BaseModel (Pydantic)
- Use UUID type for game_id, str for target_status, datetime for transition_time
- Add docstring explaining when this event is published

### Task 2.2: Implement bot handler for status transitions

Create bot event handler that updates game status in database and refreshes Discord message.

- **Files**:
  - services/bot/events/handlers.py - Add _handle_status_transition_due method
- **Success**:
  - Handler extracts game_id and target_status from event payload
  - Loads game from database with participants
  - Updates game.status to target_status and game.updated_at to current time
  - Commits database changes
  - Calls _refresh_game_message() to update Discord
  - Logs transitions and handles errors gracefully
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 232-260) - Bot handler implementation pattern
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 75-85) - Problem analysis showing missing event handling
- **Dependencies**:
  - Task 2.1 completion
  - Existing bot handler framework
  - _get_game_with_participants() helper method
  - _refresh_game_message() helper method

**Implementation Details**:
- Method signature: async def _handle_status_transition_due(self, data: dict[str, Any]) -> None
- Validate game exists before updating
- Check current status is SCHEDULED before transitioning
- Use UTC timezone for updated_at timestamp
- Log warning if game not found or already transitioned

### Task 2.3: Register status transition handler in bot

Register the new handler in bot's event consumer routing.

- **Files**:
  - services/bot/events/handlers.py - Update _register_event_handlers method
- **Success**:
  - GAME_STATUS_TRANSITION_DUE mapped to _handle_status_transition_due
  - Handler invoked when status transition events are published
  - Event routing works like existing GAME_REMINDER_DUE and GAME_UPDATED handlers
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 30-34) - Bot handler registration pattern
- **Dependencies**:
  - Task 2.2 completion

**Implementation Details**:
- Add to handler mapping: EventType.GAME_STATUS_TRANSITION_DUE: self._handle_status_transition_due
- Follow same pattern as other event type registrations
- Ensure async handling is properly configured

## Phase 3: Create Daemon Wrappers and Update Docker

### Task 3.1: Create notification daemon wrapper

Create thin wrapper script that instantiates generic daemon for notifications.

- **Files**:
  - services/scheduler/notification_daemon_wrapper.py - New wrapper script
- **Success**:
  - Script instantiates SchedulerDaemon with notification-specific parameters
  - Parameters: notify_channel="notification_schedule_changed", model_class=NotificationSchedule, time_field="notification_time", status_field="sent", event_builder=build_game_reminder_event
  - Reads database_url and rabbitmq_url from environment variables
  - Handles graceful shutdown on SIGTERM/SIGINT
  - Script is executable as daemon entry point
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 176-190) - Notification daemon instantiation example
- **Dependencies**:
  - Phase 1 completion (generic daemon and event builders)
  - Environment variables: DATABASE_URL, RABBITMQ_URL

**Implementation Details**:
- Import from generic_scheduler_daemon and event_builders
- Parse environment variables with fallback defaults
- Main function instantiates and runs daemon
- Signal handler for clean shutdown
- Logging configured for production use

### Task 3.2: Create status transition daemon wrapper

Create thin wrapper script that instantiates generic daemon for status transitions.

- **Files**:
  - services/scheduler/status_transition_daemon_wrapper.py - New wrapper script
- **Success**:
  - Script instantiates SchedulerDaemon with status-transition-specific parameters
  - Parameters: notify_channel="game_status_schedule_changed", model_class=GameStatusSchedule, time_field="transition_time", status_field="executed", event_builder=build_status_transition_event
  - Reads database_url and rabbitmq_url from environment variables
  - Handles graceful shutdown on SIGTERM/SIGINT
  - Script is executable as daemon entry point
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 192-206) - Status daemon instantiation example
- **Dependencies**:
  - Phase 1 completion (generic daemon and event builders)
  - Phase 2 completion (status transition event support)
  - Environment variables: DATABASE_URL, RABBITMQ_URL

**Implementation Details**:
- Import from generic_scheduler_daemon and event_builders
- Parse environment variables with fallback defaults
- Main function instantiates and runs daemon
- Signal handler for clean shutdown
- Logging configured for production use

### Task 3.3: Update Docker configurations

Update Dockerfiles and docker-compose to use new daemon wrappers.

- **Files**:
  - docker/notification-daemon.Dockerfile - Update entry point
  - docker/status-transition-daemon.Dockerfile - Update entry point
  - docker-compose.base.yml - Update service command paths
- **Success**:
  - Dockerfiles reference new wrapper scripts
  - Services start successfully with new architecture
  - Environment variables passed correctly
  - Logging output visible in docker logs
- **Research References**:
  - Existing Docker configurations for pattern matching
- **Dependencies**:
  - Task 3.1 completion
  - Task 3.2 completion

**Implementation Details**:
- Update CMD in Dockerfiles to run wrapper scripts
- Ensure Python module paths are correct
- Verify environment variables are passed through from docker-compose
- Test container startup with docker-compose up

## Phase 4: Update Integration Tests

### Task 4.1: Fix status transition daemon test constructor calls

Fix integration tests that incorrectly pass rabbitmq_url as second constructor parameter.

- **Files**:
  - tests/integration/test_status_transitions.py - Fix daemon instantiation
- **Success**:
  - Tests instantiate daemon with correct parameters matching new wrapper pattern
  - No ValueError from string-to-float conversion
  - All integration tests pass
  - Tests verify status transition functionality works end-to-end
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 38-45) - Integration test failure root cause
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 49-68) - Constructor signature mismatch details
- **Dependencies**:
  - Phase 3 completion

**Implementation Details**:
- Update daemon instantiation to use wrapper pattern or pass correct parameters
- Verify test fixtures provide both database_url and rabbitmq_url
- Run integration tests to confirm fixes work
- Update any other tests that instantiate daemons directly

### Task 4.2: Add generic scheduler daemon tests

Create comprehensive tests for generic scheduler daemon functionality.

- **Files**:
  - tests/services/scheduler/test_generic_scheduler_daemon.py - New test file
- **Success**:
  - Tests cover daemon initialization with different configurations
  - Tests verify query functions work with both schedule types
  - Tests check event publishing happens correctly
  - Tests verify PostgreSQL LISTEN/NOTIFY integration
  - Tests confirm marking items as processed works
  - Tests validate error handling and edge cases
- **Research References**:
  - Existing daemon tests for pattern reference
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 116-150) - Algorithm patterns to test
- **Dependencies**:
  - Phase 1 completion

**Implementation Details**:
- Use pytest fixtures for database and RabbitMQ setup
- Mock PostgreSQL listener for unit tests
- Test both notification and status transition configurations
- Verify event payloads match expected schemas
- Test timeout and wake-up behavior

### Task 4.3: Add bot handler tests for status transitions

Create tests for new bot status transition event handler.

- **Files**:
  - tests/services/bot/test_event_handlers.py - Add status transition handler tests
- **Success**:
  - Tests verify handler updates game status correctly
  - Tests check Discord message refresh is called
  - Tests validate error handling for missing games
  - Tests confirm database commits occur
  - Tests verify logging output
- **Research References**:
  - Existing bot handler tests for pattern reference
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 232-260) - Handler implementation details
- **Dependencies**:
  - Phase 2 completion

**Implementation Details**:
- Mock database session and game queries
- Mock _refresh_game_message to verify it's called
- Test with valid game_id and target_status
- Test error cases: game not found, wrong current status
- Verify UTC timezone handling in updated_at

## Phase 5: Clean Up Old Implementations

### Task 5.1: Remove old daemon implementations

Delete old notification_daemon.py and status_transition_daemon.py files.

- **Files**:
  - services/scheduler/notification_daemon.py - DELETE
  - services/scheduler/status_transition_daemon.py - DELETE
  - services/scheduler/schedule_queries.py - OPTIONAL DELETE (if not used elsewhere)
  - services/scheduler/status_schedule_queries.py - OPTIONAL DELETE (if not used elsewhere)
- **Success**:
  - Old implementations removed from codebase
  - No import errors from removal
  - Git history preserves old code for reference
  - Documentation updated to reflect new architecture
- **Research References**:
  - #file:../research/20251204-scheduler-daemon-consolidation-bot-status-updates-research.md (Lines 7-23) - Files to be replaced
- **Dependencies**:
  - All previous phases complete
  - All tests passing with new implementation

**Implementation Details**:
- Search codebase for any remaining imports of old daemon modules
- Update any documentation that references old daemon structure
- Commit deletion as separate atomic change
- Verify no regression after removal

### Task 5.2: Verify all tests pass

Run full test suite to ensure consolidation is successful.

- **Files**:
  - All test files in tests/ directory
- **Success**:
  - Unit tests pass: pytest tests/services/scheduler/ tests/services/bot/
  - Integration tests pass: pytest tests/integration/test_status_transitions.py
  - E2E tests pass if applicable
  - No test failures or regressions
  - Code coverage maintained or improved
- **Research References**:
  - Project test suite structure
- **Dependencies**:
  - All previous tasks complete

**Implementation Details**:
- Run: pytest tests/services/scheduler/ -v
- Run: pytest tests/integration/test_status_transitions.py -v
- Run: pytest tests/services/bot/test_event_handlers.py -v
- Fix any failures that emerge
- Verify Discord integration works in development environment

## Dependencies

- PostgreSQL LISTEN/NOTIFY infrastructure
- RabbitMQ event bus
- Bot event handler framework
- Schedule tables and triggers
- Python 3.11+
- SQLAlchemy ORM
- Pika RabbitMQ client

## Success Criteria

- All integration tests pass without constructor errors
- Discord messages update when game status transitions
- Single unified generic scheduler daemon (~150 lines)
- Bot handles all game state changes through events
- Zero code duplication between schedulers
- Test coverage maintained for all functionality

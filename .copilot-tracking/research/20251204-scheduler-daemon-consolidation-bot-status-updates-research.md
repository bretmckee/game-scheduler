<!-- markdownlint-disable-file -->
# Task Research Notes: Scheduler Daemon Consolidation and Bot Status Updates

## Research Executed

### File Analysis
- services/scheduler/notification_daemon.py
  - 252 lines implementing notification scheduling with PostgreSQL LISTEN/NOTIFY
  - Uses buffer_seconds parameter (10s early wake-up)
  - Publishes GAME_REMINDER_DUE events to RabbitMQ
  - Marks notifications as sent in database
- services/scheduler/status_transition_daemon.py
  - 242 lines implementing status transition scheduling with PostgreSQL LISTEN/NOTIFY
  - No buffer_seconds (exact time triggering)
  - Currently updates game status in database directly (no event publishing)
  - Missing RabbitMQ integration causing Discord update failures
- services/scheduler/schedule_queries.py
  - get_next_due_notification() - queries MIN(notification_time) with sent=False
  - mark_notification_sent() - updates sent=True
- services/scheduler/status_schedule_queries.py
  - get_next_due_transition() - queries MIN(transition_time) with executed=False
  - mark_transition_executed() - updates executed=True
- services/api/services/games.py
  - API publishes GAME_UPDATED events after all game modifications
  - Bot listens for GAME_UPDATED and refreshes Discord messages
  - This pattern should be used for status transitions too

### Code Search Results
- "GAME_UPDATED" event publishing pattern
  - API service publishes after game edits, participant changes, cancellations
  - Bot event handlers refresh Discord messages on GAME_UPDATED
  - Status transition daemon doesn't publish any events (root cause of issue)
- Bot event handlers (services/bot/events/handlers.py)
  - Registers handlers for: GAME_UPDATED, GAME_REMINDER_DUE, NOTIFICATION_SEND_DM, GAME_CREATED, PLAYER_REMOVED
  - No handler for GAME_STARTED or status transitions
  - Uses _refresh_game_message() to update Discord after events
- Integration test failures
  - test_daemon_waits_for_future_transition fails with ValueError
  - Tests pass rabbitmq_url to StatusTransitionDaemon(db_url, rabbitmq_url)
  - Constructor only accepts (database_url, max_timeout)
  - rabbitmq_url gets assigned to max_timeout causing float conversion error

### Project Conventions
- Standards referenced: Python project structure, async/sync patterns, event-driven architecture
- Instructions followed: Coding best practices, DRY principle, modularity

## Key Discoveries

### Problem 1: Integration Test Failure
```python
# Test code (line 541 in test_status_transitions.py)
daemon = StatusTransitionDaemon(db_url, rabbitmq_url)

# Constructor definition (status_transition_daemon.py:62)
def __init__(self, database_url: str, max_timeout: int = 900):
    self.database_url = database_url
    self.max_timeout = max_timeout  # Gets assigned rabbitmq_url string!

# Error at line 144:
wait_time = min(time_until_due, float(self.max_timeout))
# ValueError: could not convert string to float: 'amqp://gamebot_integration:integration_password@rabbitmq:5672/'
```

### Problem 2: Discord Status Updates Don't Work
Status transition daemon updates game.status in database but never publishes events:
```python
# Current code (status_transition_daemon.py:186-198)
game.status = transition.target_status
game.updated_at = current_time
mark_transition_executed(self.db, transition.id)
self.db.commit()
# Missing: No event publishing!
# Result: Bot never knows to refresh Discord message
```

API service pattern that should be followed:
```python
# API publishes after updates (games.py:824-836)
async def _publish_game_updated(self, game: game_model.GameSession) -> None:
    event = messaging_events.Event(
        event_type=messaging_events.EventType.GAME_UPDATED,
        data={"game_id": game.id, "message_id": game.message_id or "", "channel_id": game.channel_id},
    )
    await self.event_publisher.publish(event=event)
```

### Problem 3: Code Duplication Between Daemons

**Identical Core Logic (95% overlap):**

| Aspect | Notification Daemon | Status Transition Daemon |
|--------|---------------------|--------------------------|
| Listen channel | notification_schedule_changed | game_status_schedule_changed |
| Query function | get_next_due_notification() | get_next_due_transition() |
| Query logic | MIN(notification_time) WHERE sent=False | MIN(transition_time) WHERE executed=False |
| Mark function | mark_notification_sent(id) | mark_transition_executed(id) |
| Event publishing | GAME_REMINDER_DUE with GameReminderDueEvent | None (missing!) |
| Buffer seconds | 10s early wake-up | 0s (exact time) |
| Lines of code | 252 lines | 242 lines |

**Shared Algorithm Pattern:**
```python
# Both daemons follow identical pattern:
while not shutdown_requested:
    next_item = get_next_due_item(db)
    if not next_item:
        wait_time = max_timeout
    else:
        time_until_due = (next_item.due_time - utc_now()).total_seconds()
        if time_until_due <= buffer_seconds:
            process_item(next_item)  # Publish event + mark processed
            continue
        wait_time = min(time_until_due - buffer_seconds, max_timeout)
    
    listener.wait_for_notification(timeout=wait_time)
```

### Architectural Insight: Bot Should Handle Status Updates

**Current (broken) approach:**
1. Daemon queries schedule → finds due transition
2. Daemon updates game.status in database
3. Daemon marks transition executed
4. Bot never notified → Discord message never updated

**API service pattern (working):**
1. API updates game in database
2. API publishes GAME_UPDATED event
3. Bot receives event → loads game → refreshes Discord message

**Proposed approach (best):**
1. Daemon queries schedule → finds due transition
2. Daemon publishes GAME_STATUS_TRANSITION_DUE event
3. Daemon marks transition executed
4. Bot receives event → updates game.status → refreshes Discord message

**Benefits of bot handling updates:**
- Single source of truth: Bot handles all game state changes (joins, leaves, cancellations, status)
- Consistency: All game updates flow through same event handling path
- Simpler daemon: Pure scheduler that just sends "this is due now" messages
- Transactional integrity: Bot can update DB and Discord in one logical operation
- Error handling: Bot can handle rollback/retry if Discord update fails
- Less code duplication: Daemon doesn't need game model knowledge

### Buffer Seconds Analysis

**Notification daemon uses 10s buffer:**
- Wakes up 10 seconds before notification_time
- Rationale: "ensure timely delivery"
- Reality: Discord DM delays vary by minutes anyway
- Benefit: Minimal to none

**Status transition daemon uses 0s buffer:**
- Waits until exact transition_time
- Simpler logic, no buffer_seconds parameter
- Works perfectly fine

**Conclusion:** Buffer adds complexity without meaningful benefit. Eliminate it.

## Recommended Approach

### Solution: Unified Generic Scheduler Daemon

Create single parameterized daemon that handles both use cases:

```python
class SchedulerDaemon:
    """Generic event-driven scheduler daemon."""
    
    def __init__(
        self,
        database_url: str,
        rabbitmq_url: str,
        notify_channel: str,           # "notification_schedule_changed" or "game_status_schedule_changed"
        model_class: type,              # NotificationSchedule or GameStatusSchedule
        time_field: str,                # "notification_time" or "transition_time"
        status_field: str,              # "sent" or "executed"
        event_builder: Callable,        # Function to build event from schedule record
        max_timeout: int = 900,
    ):
        pass
    
    def _process_item(self, item):
        """Process scheduled item: build event, publish, mark processed."""
        event = self.event_builder(item)
        self.publisher.publish_dict(event_type=event.type, data=event.data)
        self._mark_processed(item.id)
        self.db.commit()
```

**Instantiation examples:**
```python
# Notification daemon instance
notification_daemon = SchedulerDaemon(
    database_url=db_url,
    rabbitmq_url=rmq_url,
    notify_channel="notification_schedule_changed",
    model_class=NotificationSchedule,
    time_field="notification_time",
    status_field="sent",
    event_builder=build_game_reminder_event,
)

# Status transition daemon instance
status_daemon = SchedulerDaemon(
    database_url=db_url,
    rabbitmq_url=rmq_url,
    notify_channel="game_status_schedule_changed",
    model_class=GameStatusSchedule,
    time_field="transition_time",
    status_field="executed",
    event_builder=build_status_transition_event,
)
```

### New Event Type: GAME_STATUS_TRANSITION_DUE

Add to EventType enum:
```python
class EventType(str, Enum):
    # Scheduling events
    GAME_REMINDER_DUE = "game.reminder_due"
    GAME_STATUS_TRANSITION_DUE = "game.status_transition_due"  # NEW
```

Event payload:
```python
class GameStatusTransitionDueEvent(BaseModel):
    """Payload for game.status_transition_due event."""
    game_id: UUID
    target_status: str  # "IN_PROGRESS", "COMPLETED", etc.
    transition_time: datetime
```

### Bot Handler Implementation

```python
# In services/bot/events/handlers.py
async def _handle_status_transition_due(self, data: dict[str, Any]) -> None:
    """Handle game.status_transition_due event by updating game status."""
    game_id = data.get("game_id")
    target_status = data.get("target_status")
    
    async with get_db_session() as db:
        game = await self._get_game_with_participants(db, game_id)
        if not game:
            logger.error(f"Game {game_id} not found for status transition")
            return
        
        if game.status != "SCHEDULED":
            logger.warning(f"Game {game_id} status is {game.status}, expected SCHEDULED")
            return
        
        # Update game status
        game.status = target_status
        game.updated_at = utc_now()
        await db.commit()
        
        logger.info(f"Transitioned game {game_id} to {target_status}")
        
        # Refresh Discord message
        await self._refresh_game_message(game_id)
```

## Implementation Guidance

### Objectives
- Consolidate two daemons into one generic scheduler
- Move status update logic from daemon to bot
- Fix integration test failures
- Enable Discord status updates

### Key Tasks

**Phase 1: Create Generic Scheduler Daemon**
1. Create services/scheduler/generic_scheduler_daemon.py with parameterized daemon class
2. Extract common query logic into generic functions
3. Implement event builder pattern for extensibility
4. Remove buffer_seconds parameter (use exact time triggering)

**Phase 2: Add Status Transition Event Handling to Bot**
1. Add GAME_STATUS_TRANSITION_DUE to EventType enum
2. Create GameStatusTransitionDueEvent model
3. Implement _handle_status_transition_due in bot event handlers
4. Register handler in bot event consumer

**Phase 3: Update Daemon Entry Points**
1. Create notification_daemon.py as thin wrapper calling generic daemon
2. Create status_transition_daemon.py as thin wrapper calling generic daemon
3. Update Dockerfiles to use new entry points
4. Update docker-compose.base.yml service definitions

**Phase 4: Update Tests**
1. Fix integration tests to not pass rabbitmq_url where not expected
2. Add tests for generic scheduler daemon
3. Update existing daemon tests to use new architecture
4. Add bot handler tests for status transitions

**Phase 5: Clean Up**
1. Remove old notification_daemon.py implementation
2. Remove old status_transition_daemon.py implementation
3. Remove duplicate query files (consolidate into generic queries)
4. Update documentation

### Dependencies
- PostgreSQL LISTEN/NOTIFY infrastructure (already exists)
- RabbitMQ event bus (already exists)
- Bot event handler framework (already exists)
- Schedule tables and triggers (already exist)

### Success Criteria
- Integration tests pass
- Discord messages update when game status transitions
- Single unified daemon codebase (~150 lines vs 494 lines)
- Bot handles all game state changes consistently
- No code duplication between schedulers

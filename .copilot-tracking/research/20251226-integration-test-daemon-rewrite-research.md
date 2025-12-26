<!-- markdownlint-disable-file -->
# Task Research Notes: Integration Test Daemon Pattern Rewrite

## Research Executed

### File Analysis
- tests/integration/test_database_infrastructure.py
  - Tests init script that sets up database schema and configuration
  - Pattern: Validates infrastructure setup WITHOUT creating daemon instances

- tests/integration/test_rabbitmq_infrastructure.py
  - Tests init_rabbitmq.py script that creates exchanges, queues, bindings
  - Pattern: Validates RabbitMQ infrastructure setup WITHOUT creating daemon instances

- tests/integration/test_retry_daemon.py (Line 29 comment: "These tests run against the actual retry-daemon container")
  - Tests the RUNNING retry-daemon service in docker-compose
  - Pattern: Publishes to DLQ, waits for daemon to process, asserts results
  - Key approach: Uses time.sleep() with RETRY_INTERVAL_SECONDS + buffer

- tests/integration/test_notification_daemon.py
  - PROBLEM: Creates own SchedulerDaemon instances (conflicts with running daemon)
  - Has 4 test functions that all instantiate SchedulerDaemon directly
  - Needs rewrite to test running notification-daemon service

- tests/integration/test_status_transitions.py
  - PROBLEM: Creates own SchedulerDaemon instances (3 occurrences at lines 268, 405, 486)
  - Needs rewrite to test running status-transition-daemon service

### Code Search Results
- "SchedulerDaemon(" in test_notification_daemon.py
  - Lines 102, 187, 333, 430: All create daemon instances
- "SchedulerDaemon(" in test_status_transitions.py
  - Lines 268, 405, 486: All create daemon instances
- "time.sleep" in test_retry_daemon.py
  - Pattern: `time.sleep(retry_interval + 2)` where retry_interval from env

### Project Conventions
- Integration tests run with compose.int.yaml which starts daemon services
- Test pattern: Infrastructure tests validate init script results
- Test pattern: Daemon tests should test running services, not create own instances
- Polling pattern: sleep(daemon_interval + buffer_seconds) then assert queue/database state

## Key Discoveries

### Integration Test Organization (5 Files Total)

1. **test_database_infrastructure.py** - Validates init script database setup
2. **test_rabbitmq_infrastructure.py** - Validates init script RabbitMQ setup
3. **test_retry_daemon.py** - Tests running retry-daemon service ✓ CORRECT PATTERN
4. **test_notification_daemon.py** - Creates own daemons ✗ NEEDS REWRITE
5. **test_status_transitions.py** - Creates own daemons ✗ NEEDS REWRITE

### Retry Daemon Test Pattern (Reference Implementation)

The retry_daemon tests demonstrate the correct pattern for testing running daemon services:

```python
def test_retry_daemon_republishes_from_dlq_without_ttl(self, rabbitmq_channel):
    """Test running daemon by publishing input and asserting output."""
    # 1. Create test data
    event = Event(
        event_type=EventType.NOTIFICATION_DUE,
        data={"game_id": str(uuid4()), "test": "no_ttl_republish"},
    )

    # 2. Publish input to queue/database that triggers daemon
    publish_to_dlq_with_metadata(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ, event)

    # 3. Wait for daemon to process (daemon polls every RETRY_INTERVAL_SECONDS)
    retry_interval = int(os.getenv("RETRY_INTERVAL_SECONDS", "15"))
    time.sleep(retry_interval + 2)  # Add 2s buffer

    # 4. Assert expected state changes
    dlq_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS_DLQ)
    primary_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)

    assert dlq_count == 0, "DLQ should be empty after retry daemon processes"
    assert primary_count == 1, "Primary queue should have republished message"
```

### Environment Variables and Daemon Wake Mechanisms

**Retry Daemon:**
- `RETRY_INTERVAL_SECONDS=15` - Polls DLQ every 15 seconds

**Notification & Status Transition Daemons:**
- **NO polling interval** - Uses PostgreSQL LISTEN/NOTIFY for event-driven wake-ups
- Wakes immediately when: INSERT triggers NOTIFY, scheduled time reached, or max_timeout (15min)
- Does NOT poll on a fixed interval

### Notification Daemon Current vs Target Pattern

**Current Pattern (WRONG - Creates Own Daemon):**
```python
def test_daemon_processes_due_notification(
    db_session, clean_notification_schedule, test_game_session, rabbitmq_url
):
    # Creates PostgresNotificationListener
    listener = PostgresNotificationListener(...)

    # Creates SchedulerDaemon instance (CONFLICTS WITH RUNNING SERVICE)
    daemon = SchedulerDaemon(
        name="test_notification_daemon",
        listener=listener,
        event_builder=build_notification_event,
        routing_key="game.reminder_due",
        interval=1,
        rabbitmq_url=rabbitmq_url,
    )

    # Runs daemon in thread (CONFLICTS!)
    daemon_thread = threading.Thread(target=daemon.run)
    daemon_thread.start()
```

**Target Pattern (CORRECT - Tests Running Service):**
```python
def test_daemon_processes_due_notification(
    db_session, clean_notification_schedule, test_game_session, rabbitmq_channel
):
    """Test that running notification-daemon processes due notifications."""
    # 1. Insert notification_schedule record with trigger_at in past
    # INSERT triggers PostgreSQL NOTIFY → daemon wakes immediately
    db_session.execute(
        text(
            "INSERT INTO notification_schedule "
            "(id, game_id, notification_type, trigger_at, is_processed) "
            "VALUES (:id, :game_id, :type, :trigger_at, :processed)"
        ),
        {
            "id": str(uuid4()),
            "game_id": test_game_session,
            "notification_type": "GAME_REMINDER",
            "trigger_at": datetime.now(UTC) - timedelta(minutes=5),  # Past trigger
            "is_processed": False,
        },
    )
    db_session.commit()

    # 2. Wait for daemon to wake and process (NOTIFY is immediate, add buffer for processing)
    time.sleep(2)  # Short wait for daemon to wake and process

    # 3. Assert notification marked processed in database
    result = db_session.execute(
        text("SELECT is_processed FROM notification_schedule WHERE game_id = :game_id"),
        {"game_id": test_game_session},
    ).fetchone()

    assert result[0] is True, "Notification should be marked processed"

    # 4. Assert message published to RabbitMQ
    message_count = get_queue_message_count(rabbitmq_channel, QUEUE_BOT_EVENTS)
    assert message_count == 1, "Should have published 1 notification event"
```

### Status Transition Daemon Pattern

Similar to notification daemon but uses:
- Table: `game_status_schedule`
- Queue: `bot_events` (same as notification)
- Routing key: `game.status_transition`
- Event type: `EventType.GAME_STATUS_TRANSITION_DUE`

## Recommended Approach

Rewrite test_notification_daemon.py and test_status_transitions.py to test running daemon services:

1. **Remove all SchedulerDaemon instantiation** - Tests should NOT create daemon instances
2. **Insert trigger data in database** - Use SQL INSERT with trigger_at in past
   - INSERT triggers PostgreSQL NOTIFY → daemon wakes immediately (event-driven)
3. **Wait briefly for processing** - `time.sleep(2)` for daemon to wake and process
   - NOT polling-based - daemon wakes on NOTIFY event from database trigger
4. **Assert database state changes** - Check `is_processed` flag set to True
5. **Assert RabbitMQ message published** - Verify message in bot_events queue
6. **Use rabbitmq_channel fixture** - For message count assertions (add to conftest if needed)

## Implementation Guidance

### Objectives
- Eliminate daemon instance creation in test_notification_daemon.py (4 occurrences)
- Eliminate daemon instance creation in test_status_transitions.py (3 occurrences)
- Rewrite tests to validate running notification-daemon and status-transition-daemon services
- Follow retry_daemon test pattern for consistency

### Key Tasks
1. Add `rabbitmq_channel` fixture to conftest.py if not present
2. Add helper functions: `get_queue_message_count()`, `consume_one_message()` (copy from test_retry_daemon.py)
3. Rewrite test_daemon_processes_due_notification to insert + wait + assert pattern
4. Rewrite test_daemon_waits_for_future_notification to verify daemon doesn't process future records
5. Rewrite remaining notification_daemon tests (2 more functions)
6. Rewrite all status_transitions tests (3 functions using daemon)
7. Remove threading, listener instantiation, daemon instantiation code

### Dependencies
- compose.int.yaml already runs notification-daemon and status-transition-daemon services
- PostgreSQL LISTEN/NOTIFY infrastructure set up by database triggers
- RabbitMQ and PostgreSQL infrastructure already available

### Success Criteria
- All tests pass without creating SchedulerDaemon instances
- Tests validate behavior of running daemon services
- Tests use minimal wait times (2s) since NOTIFY is event-driven, not polling
- No threading or subprocess management in tests
- Tests understand event-driven wake mechanism (NOTIFY) vs polling (retry daemon)

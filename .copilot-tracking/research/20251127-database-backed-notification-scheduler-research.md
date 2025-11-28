<!-- markdownlint-disable-file -->
# Task Research Notes: Database-Backed Event-Driven Notification Scheduler

## Research Executed

### Current Architecture Problems
- **Polling-based approach**: Queries all games every 5 minutes in 3-hour window
- **Fixed window limitation**: Hard-coded 180-minute lookahead prevents long-term notifications
- **Scalability issues**: Processing grows linearly with number of scheduled games
- **Celery ETA unreliability**: Tasks held in worker memory, lost on restart
- **No persistence**: Scheduled notifications lost if scheduler service restarts

### Celery ETA Task Persistence Research
- #fetch:"https://docs.celeryq.dev/en/stable/userguide/calling.html#eta-and-countdown"
  - Tasks with ETA are immediately fetched by worker and held in memory
  - Warning: "those tasks may accumulate in the worker and make a significant impact on the RAM usage"
  - Not recommended for distant future scheduling
  - Worker restart loses all ETA tasks (already acknowledged from queue)
- #fetch:"https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/rabbitmq.html"
  - RabbitMQ queues are durable but ETA tasks are acknowledged immediately
  - `task_acks_late=True` helps but doesn't solve ETA memory storage problem
  - Recommendation: "For longer durations, consider using database-backed periodic tasks"

### PostgreSQL Event Notification Research
- #fetch:"https://www.postgresql.org/docs/current/sql-notify.html"
  - LISTEN/NOTIFY provides lightweight pub/sub within PostgreSQL
  - Transactional: notifications only sent on COMMIT
  - 8KB payload limit (sufficient for game_id + metadata)
  - Notifications delivered to all active listeners immediately
  - Not durable: lost if no listeners connected (acceptable with fallback)
- #fetch:"https://www.postgresql.org/docs/current/sql-listen.html"
  - Sessions execute LISTEN to subscribe to channels
  - Can trigger from database triggers automatically
  - Minimal overhead, built-in PostgreSQL feature

### Project Database Configuration
- **shared/database.py**
  - Already uses asyncpg for async services (API, Bot)
  - Already uses psycopg2 for sync services (Scheduler)
  - Connection pooling with `pool_pre_ping=True`
  - Both async and sync engines configured
- **pyproject.toml dependencies**
  - asyncpg>=0.29.0 (async postgres driver)
  - psycopg2-binary>=2.9.0 (sync postgres driver with LISTEN/NOTIFY support)
  - sqlalchemy[asyncio]>=2.0.0 (ORM with full async support)

### Existing Alembic Migration Pattern
- **alembic/versions/** contains 13 migration files
  - Follows sequential numbering: 001, 002, 003, etc.
  - Most recent: 011_add_expected_duration_minutes.py
  - Uses descriptive names with version prefix

## Key Discoveries

### Priority Queue Pattern with Event-Driven Wake-ups

The optimal architecture combines:
1. **Single MIN query**: Query next notification due time from database
2. **Sleep until due**: Wait for that specific time (not polling all games)
3. **Event-driven wake-ups**: PostgreSQL NOTIFY triggers immediate re-calculation
4. **Self-healing**: Restart recovery is just one MIN() query
5. **Periodic safety checks**: Fallback polling every 5 minutes catches missed events

### Database Schema Design

```sql
CREATE TABLE notification_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id UUID NOT NULL REFERENCES game_sessions(id) ON DELETE CASCADE,
    reminder_minutes INTEGER NOT NULL,
    notification_time TIMESTAMP NOT NULL,
    sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Ensure one notification per game per reminder time
    UNIQUE(game_id, reminder_minutes)
);

-- Critical index for MIN() query performance
CREATE INDEX idx_notification_schedule_next_due 
ON notification_schedule(notification_time) 
WHERE sent = FALSE;

-- Index for cleanup queries
CREATE INDEX idx_notification_schedule_game_id 
ON notification_schedule(game_id);
```

### PostgreSQL Trigger for Real-Time Notifications

```sql
CREATE OR REPLACE FUNCTION notify_schedule_changed()
RETURNS TRIGGER AS $$
BEGIN
    -- Only notify if change affects near-term schedule
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') AND 
       NEW.notification_time <= NOW() + INTERVAL '10 minutes' AND
       NEW.sent = FALSE THEN
        PERFORM pg_notify(
            'notification_schedule_changed',
            json_build_object(
                'operation', TG_OP,
                'game_id', NEW.game_id,
                'notification_time', NEW.notification_time
            )::text
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER notification_schedule_trigger
AFTER INSERT OR UPDATE OR DELETE ON notification_schedule
FOR EACH ROW
EXECUTE FUNCTION notify_schedule_changed();
```

### Scheduler Loop Algorithm

```python
async def notification_scheduler_loop():
    """
    Main scheduler loop using minimum value pattern.
    
    Algorithm:
    1. Query for MIN(notification_time) WHERE notification_time > NOW()
    2. Calculate wait time until that notification is due
    3. Wait for earliest of: due time, postgres NOTIFY, or 5-min timeout
    4. Process all notifications now due (batch processing)
    5. Loop repeats - re-queries for next minimum
    
    Recovery: On restart, immediately queries MIN() and resumes
    """
    
    # Establish LISTEN connection for event-driven wake-ups
    listen_conn = await get_postgres_listen_connection()
    await listen_conn.execute("LISTEN notification_schedule_changed")
    
    while True:
        # 1. Get next notification due
        next_notification = await get_next_due_notification()
        
        if not next_notification:
            # No notifications scheduled, wait for event or periodic check
            wait_time = 300  # 5 minutes
        else:
            # Calculate seconds until notification is due (with 10s buffer)
            time_until_due = (next_notification.notification_time - utcnow()).total_seconds()
            wait_time = max(0, time_until_due - 10)
        
        # 2. Wait for earliest trigger
        wakeup_reason = await wait_for_event_or_timeout(
            listen_conn,
            timeout=wait_time,
            max_timeout=300  # Safety: recheck every 5 min regardless
        )
        
        logger.info(f"Woke up due to: {wakeup_reason}")
        
        # 3. Process all notifications now due (batch processing)
        processed_count = await process_due_notifications()
        
        logger.info(f"Processed {processed_count} notifications")
        
        # 4. Loop continues, re-queries minimum
```

### Game Event Handlers

```python
async def on_game_created_or_updated(game: GameSession):
    """
    Recalculate notification schedule when game is created/updated.
    
    Triggered by:
    - API creates new game
    - API updates game scheduled_at or reminder_minutes
    - Channel/Guild default reminder_minutes changed
    """
    
    # Resolve reminder minutes using inheritance chain
    reminder_minutes = resolve_reminder_minutes(game)
    
    # Clear existing schedule for this game
    await db.execute(
        "DELETE FROM notification_schedule WHERE game_id = :game_id",
        {"game_id": game.id}
    )
    
    # Insert new schedule entries
    now = datetime.utcnow()
    for reminder_min in reminder_minutes:
        notification_time = game.scheduled_at - timedelta(minutes=reminder_min)
        
        # Only schedule future notifications
        if notification_time > now:
            await db.execute(
                """
                INSERT INTO notification_schedule 
                    (game_id, reminder_minutes, notification_time)
                VALUES (:game_id, :reminder_min, :notification_time)
                ON CONFLICT (game_id, reminder_minutes) 
                DO UPDATE SET 
                    notification_time = EXCLUDED.notification_time,
                    sent = FALSE
                """,
                {
                    "game_id": game.id,
                    "reminder_min": reminder_min,
                    "notification_time": notification_time
                }
            )
    
    await db.commit()
    # Postgres trigger automatically sends NOTIFY to scheduler
```

### psycopg2 LISTEN/NOTIFY Implementation

```python
import select
import psycopg2
import psycopg2.extensions

class PostgresNotificationListener:
    """
    Synchronous PostgreSQL LISTEN/NOTIFY client for scheduler service.
    
    Uses psycopg2 (already in dependencies) for LISTEN connections.
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
        
    def connect(self):
        """Establish connection with autocommit for LISTEN."""
        self.conn = psycopg2.connect(self.database_url)
        self.conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
        )
        
    def listen(self, channel: str):
        """Subscribe to notification channel."""
        cursor = self.conn.cursor()
        cursor.execute(f"LISTEN {channel};")
        cursor.close()
        
    def wait_for_notification(self, timeout: float) -> tuple[bool, dict | None]:
        """
        Wait for notification or timeout.
        
        Returns:
            (received, payload) tuple
            - received: True if notification received, False if timeout
            - payload: Parsed JSON payload if received, None otherwise
        """
        if select.select([self.conn], [], [], timeout) == ([], [], []):
            # Timeout occurred
            return False, None
        
        # Notification received
        self.conn.poll()
        
        if self.conn.notifies:
            notify = self.conn.notifies.pop(0)
            payload = json.loads(notify.payload) if notify.payload else {}
            return True, payload
        
        return False, None
```

### Batch Processing with FOR UPDATE SKIP LOCKED

```python
async def process_due_notifications():
    """
    Process all notifications due now using pessimistic locking.
    
    FOR UPDATE SKIP LOCKED prevents race conditions if multiple
    scheduler instances run (future horizontal scaling).
    """
    
    # Query all notifications due within next minute (includes processing buffer)
    result = await db.execute(
        """
        SELECT id, game_id, reminder_minutes
        FROM notification_schedule
        WHERE notification_time <= NOW() + INTERVAL '1 minute'
          AND sent = FALSE
        ORDER BY notification_time ASC
        FOR UPDATE SKIP LOCKED
        """
    )
    
    notifications = result.fetchall()
    processed_count = 0
    
    for notification in notifications:
        try:
            # Publish game.reminder_due event to RabbitMQ
            await publish_game_reminder_due(
                game_id=notification.game_id,
                reminder_minutes=notification.reminder_minutes
            )
            
            # Mark as sent
            await db.execute(
                """
                UPDATE notification_schedule 
                SET sent = TRUE 
                WHERE id = :id
                """,
                {"id": notification.id}
            )
            await db.commit()
            processed_count += 1
            
        except Exception as e:
            logger.error(
                f"Failed to process notification {notification.id}: {e}",
                exc_info=True
            )
            await db.rollback()
    
    return processed_count
```

## Recommended Approach

### Database-Backed Event-Driven Notification Scheduler

**Architecture**:
- Store notification schedule in `notification_schedule` table
- Scheduler queries MIN(notification_time) for next due notification
- Sleeps until that time (not polling entire database)
- PostgreSQL NOTIFY wakes scheduler on table changes
- Periodic 5-minute recheck for safety

**Advantages**:
1. **Scalability**: Single MIN() query regardless of total games
2. **Unlimited horizon**: Support notifications weeks/months in advance
3. **Persistence**: All state in database, survives restarts
4. **Self-healing**: Restart recovery is one MIN() query
5. **Real-time**: LISTEN/NOTIFY for immediate response to changes
6. **Reliability**: Periodic fallback catches missed notifications
7. **Simplicity**: No complex in-memory state management

**Performance Characteristics**:
- Query cost: O(1) with proper index on notification_time
- Memory usage: O(1) - only current minimum in memory
- Processing: Batch processes all due notifications together
- Horizontal scaling: FOR UPDATE SKIP LOCKED prevents conflicts

## Implementation Guidance

### Objectives
- Replace polling-based notification checker with event-driven MIN() pattern
- Use PostgreSQL LISTEN/NOTIFY for real-time schedule updates
- Persist notification schedule in database table
- Support unlimited notification windows (24 hours, 1 week, etc.)
- Ensure zero data loss on scheduler restart

### Key Tasks
1. Create notification_schedule table via Alembic migration
2. Add PostgreSQL trigger for LISTEN/NOTIFY on schedule changes
3. Implement scheduler loop with MIN() query and wait pattern
4. Add psycopg2 LISTEN connection handler
5. Update game create/update handlers to populate schedule table
6. Remove old polling-based check_notifications task
7. Update tests for new architecture

### Dependencies
- psycopg2-binary>=2.9.0 (already installed)
- asyncpg>=0.29.0 (already installed)
- sqlalchemy[asyncio]>=2.0.0 (already installed)
- No new external dependencies required

### Success Criteria
- Scheduler processes notifications with <10 second latency
- Supports notification windows of unlimited duration
- Survives restart without losing scheduled notifications
- Responds to game changes within 1 second
- Periodic safety checks catch any missed notifications
- Single MIN() query scales to millions of games

### Migration Strategy
1. Deploy notification_schedule table (no breaking changes)
2. Start populating schedule table alongside old system
3. Deploy new scheduler with dual mode (old + new)
4. Monitor for correctness and performance
5. Switch to new scheduler exclusively
6. Remove old polling code after validation period

## External Research

- #fetch:"https://docs.celeryq.dev/en/stable/userguide/calling.html#eta-and-countdown"
  - Celery ETA tasks held in worker memory
  - Lost on restart, not recommended for distant future
  - Recommendation: use database-backed scheduling

- #fetch:"https://www.postgresql.org/docs/current/sql-notify.html"
  - LISTEN/NOTIFY for lightweight pub/sub
  - Transactional, 8KB payload, immediate delivery
  - Pattern: Triggers can call pg_notify() automatically

- #fetch:"https://www.postgresql.org/docs/current/sql-listen.html"
  - LISTEN registers session as listener
  - Must use connection pooling carefully
  - Reconnect logic needed for robustness

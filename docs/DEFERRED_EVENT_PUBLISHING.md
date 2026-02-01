# Deferred Event Publishing

## Overview

Deferred event publishing is a transactional pattern that ensures RabbitMQ events are published **only after** database transactions commit successfully. This prevents race conditions where event consumers receive messages about database changes that aren't yet visible.

## The Problem

When events are published during a transaction (before commit), consumers can receive messages about data that doesn't exist yet from their perspective:

```python
# ❌ WRONG - Race Condition
async def create_game(db: AsyncSession):
    game = GameSession(...)
    db.add(game)
    await db.flush()  # Game has ID but transaction not committed

    # Publish event while transaction still open
    await event_publisher.publish(game_created_event)

    # Route handler returns
    # THEN database.get_db() commits

# Bot receives message and queries database
# Transaction not committed yet → Game not found!
```

**Timeline of the race condition:**
1. ⏱️ 0ms: API creates game, flushes to DB (transaction open)
2. ⏱️ 5ms: API publishes `game.created` to RabbitMQ
3. ⏱️ 8ms: Bot receives message, queries for game
4. ⏱️ 10ms: Bot query fails (transaction not committed)
5. ⏱️ 15ms: API transaction commits (game now visible)

## The Solution

Deferred publishing queues events during the transaction and publishes them **after commit** via SQLAlchemy event listeners:

```python
# ✅ CORRECT - Deferred Publishing
async def create_game(db: AsyncSession):
    game = GameSession(...)
    db.add(game)
    await db.flush()

    # Queue event for publishing after commit
    event_publisher.publish_deferred(game_created_event)

    # Route handler returns
    # database.get_db() commits
    # THEN after_commit listener publishes events

# Bot receives message and queries database
# Transaction already committed → Game found!
```

**Timeline with deferred publishing:**
1. ⏱️ 0ms: API creates game, flushes to DB (transaction open)
2. ⏱️ 5ms: API queues event (stored in `session.info`)
3. ⏱️ 10ms: API transaction commits
4. ⏱️ 12ms: `after_commit` hook publishes event to RabbitMQ
5. ⏱️ 15ms: Bot receives message, queries for game
6. ⏱️ 18ms: Bot query succeeds (transaction committed)

## Architecture

### Components

1. **DeferredEventPublisher** (`shared/messaging/deferred_publisher.py`)
   - Wraps regular `EventPublisher`
   - Stores events in `session.info["_deferred_events"]` during transaction
   - Provides `publish_deferred()` method (synchronous, no `await`)

2. **SQLAlchemy Event Listeners** (`shared/database.py`)
   - `after_commit`: Publishes all deferred events
   - `after_rollback`: Discards all deferred events

3. **Service Layer** (`services/api/services/games.py`)
   - Uses `DeferredEventPublisher` instead of `EventPublisher`
   - Calls `publish_deferred()` instead of `await publish()`

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ Route Handler (Transaction Boundary)                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │ Service Layer                                      │     │
│  │                                                     │     │
│  │  game = GameSession(...)                           │     │
│  │  db.add(game)                                      │     │
│  │  await db.flush()  ← SQL sent, transaction open   │     │
│  │                                                     │     │
│  │  event = Event(...)                                │     │
│  │  event_publisher.publish_deferred(event)           │     │
│  │    ↓                                               │     │
│  │    ↓ Stores in session.info["_deferred_events"]   │     │
│  │                                                     │     │
│  │  return game                                       │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  await session.commit()  ← Transaction commits               │
│         ↓                                                    │
│         ↓ Triggers after_commit listener                    │
│         ↓                                                    │
│  ┌────────────────────────────────────────────────────┐     │
│  │ after_commit Hook                                  │     │
│  │                                                     │     │
│  │  events = session.info["_deferred_events"]         │     │
│  │  for event in events:                              │     │
│  │      await event_publisher.publish(event)          │     │
│  │                                                     │     │
│  │  clear session.info                                │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                         ↓
                         ↓ Events published to RabbitMQ
                         ↓
              ┌──────────────────────┐
              │ Bot / Consumer       │
              │                      │
              │ Receives event       │
              │ Queries database     │
              │ ✓ Finds game         │
              └──────────────────────┘
```

## Usage

### Service Layer

Services use `DeferredEventPublisher` and call `publish_deferred()`:

```python
class GameService:
    def __init__(
        self,
        db: AsyncSession,
        event_publisher: DeferredEventPublisher,  # Note: DeferredEventPublisher
        ...
    ):
        self.db = db
        self.event_publisher = event_publisher

    async def create_game(self, game_data: GameCreateRequest) -> GameSession:
        """
        Create game session.

        Does not commit. Caller must commit transaction.
        Events are published after commit.
        """
        game = GameSession(...)
        self.db.add(game)
        await self.db.flush()

        # Queue event for deferred publishing
        event = Event(
            event_type=EventType.GAME_CREATED,
            data={"game_id": game.id, ...}
        )
        self.event_publisher.publish_deferred(event=event)  # No await!

        logger.info("Deferred game.created event for game %s", game.id)

        return game
```

### Dependency Injection

Routes provide `DeferredEventPublisher` via dependency injection:

```python
async def _get_game_service(
    db: AsyncSession = Depends(database.get_db_with_user_guilds()),
) -> GameService:
    """Get game service with deferred event publishing."""
    base_publisher = EventPublisher()
    deferred_publisher = DeferredEventPublisher(
        db=db,
        event_publisher=base_publisher,
    )

    return GameService(
        db=db,
        event_publisher=deferred_publisher,
        ...
    )
```

### Testing

Mock `DeferredEventPublisher` and verify `publish_deferred` is called:

```python
@pytest.fixture
def mock_event_publisher():
    """Mock deferred event publisher."""
    publisher = AsyncMock(spec=DeferredEventPublisher)
    publisher.publish_deferred = MagicMock()  # Synchronous method
    return publisher

def test_create_game_publishes_event(game_service, mock_event_publisher):
    """Verify game creation queues event for deferred publishing."""
    game = await game_service.create_game(game_data)

    # Verify deferred publishing was called
    mock_event_publisher.publish_deferred.assert_called_once()

    # Verify event type
    call_args = mock_event_publisher.publish_deferred.call_args
    event = call_args.kwargs['event']
    assert event.event_type == EventType.GAME_CREATED
```

## Implementation Details

### Session Storage

Events are stored in SQLAlchemy's `session.info` dictionary, which is:
- Thread-safe
- Automatically cleared when session closes
- Designed for custom metadata storage

```python
def publish_deferred(self, event: Event, routing_key: str | None = None) -> None:
    """Queue event for publishing after commit."""
    if "_deferred_events" not in self.db.info:
        self.db.info["_deferred_events"] = []

    self.db.info["_deferred_events"].append({
        "event": event,
        "routing_key": routing_key,
    })
```

### Event Listeners

SQLAlchemy event listeners hook into transaction lifecycle:

```python
@event.listens_for(AsyncSession.sync_session_class, "after_commit")
def publish_deferred_events_after_commit(session: Session) -> None:
    """Publish events after successful commit."""
    events = DeferredEventPublisher.get_deferred_events(session)

    if not events:
        return

    logger.info("Publishing %d deferred events after commit", len(events))

    # Publish asynchronously
    async def _publish_all():
        event_publisher = EventPublisher()
        await event_publisher.connect()

        for deferred_event in events:
            await event_publisher.publish(
                event=deferred_event["event"],
                routing_key=deferred_event["routing_key"],
            )

        await event_publisher.close()
        DeferredEventPublisher.clear_deferred_events(session)

    asyncio.create_task(_publish_all())

@event.listens_for(AsyncSession.sync_session_class, "after_rollback")
def clear_deferred_events_after_rollback(session: Session) -> None:
    """Discard events after rollback."""
    events = DeferredEventPublisher.get_deferred_events(session)

    if events:
        logger.info("Discarding %d deferred events after rollback", len(events))
        DeferredEventPublisher.clear_deferred_events(session)
```

### Asynchronous Publishing

Events are published asynchronously using `asyncio.create_task()`:
- Doesn't block the HTTP response
- Runs in background after commit completes
- Failures logged but don't affect transaction

## When to Use Deferred Publishing

### ✅ Use Deferred Publishing When:

- Publishing events about database changes
- Events describe data that must be visible to consumers
- Service layer modifies database within transactions
- Using FastAPI's `Depends(get_db())` transaction management

### ❌ Don't Use Deferred Publishing When:

- Events are informational only (not tied to database state)
- Publishing from outside transaction context
- Event order must be guaranteed before HTTP response
- Need synchronous confirmation of publishing

## Relationship to Transaction Management

Deferred publishing integrates with the project's transaction management pattern:

```python
# Route handler - Transaction boundary
@router.post("/games")
async def create_game(
    game_data: GameCreateRequest,
    db: AsyncSession = Depends(get_db),  # Transaction starts here
    game_service: GameService = Depends(_get_game_service),
) -> GameResponse:
    # Service modifies database and queues events
    game = await game_service.create_game(game_data)

    # get_db() commits transaction here
    # after_commit hook publishes events here

    return game
```

See [TRANSACTION_MANAGEMENT.md](TRANSACTION_MANAGEMENT.md) for complete transaction patterns.

## Rollback Behavior

On transaction rollback, deferred events are automatically discarded:

```python
@router.post("/games")
async def create_game(...):
    try:
        game = await game_service.create_game(game_data)
        # Queue contains: [game.created event]

        await other_service.do_something()  # Raises exception

    except Exception:
        # get_db() calls session.rollback()
        # after_rollback hook clears deferred events
        # No events published - consistent with database state
        raise
```

## Benefits

1. **Eliminates Race Conditions**: Consumers never see events for uncommitted data
2. **Maintains Consistency**: Events and database state always aligned
3. **Automatic Cleanup**: Rollback discards events automatically
4. **Backward Compatible**: Non-deferred publishers still work for other use cases
5. **Testing Friendly**: Easy to mock and verify event publishing

## Troubleshooting

### Events Not Publishing

**Symptom**: Events queued but never published

**Possible Causes**:
1. Transaction never commits (exception raised)
2. Event listener not registered (missing import)
3. Publishing fails silently (check logs)

**Debug Steps**:
```python
# Enable debug logging
logger.setLevel(logging.DEBUG)

# Check session.info
print(f"Deferred events: {len(db.info.get('_deferred_events', []))}")

# Verify listener registration
from sqlalchemy import event
listeners = event.contains(AsyncSession.sync_session_class, "after_commit")
print(f"after_commit listeners registered: {listeners}")
```

### Events Published Multiple Times

**Symptom**: Bot receives duplicate events

**Possible Causes**:
1. Service called multiple times in same transaction
2. Event listener registered multiple times

**Debug Steps**:
```python
# Check how many times service is called
logger.info("create_game called: %s", game.id)

# Count events in queue
events = db.info.get('_deferred_events', [])
logger.info("Total deferred events: %d", len(events))
```

## Migration Guide

To convert existing immediate publishing to deferred:

1. **Update Service Constructor**:
   ```python
   # Before
   event_publisher: EventPublisher

   # After
   event_publisher: DeferredEventPublisher
   ```

2. **Change Publish Calls**:
   ```python
   # Before
   await self.event_publisher.publish(event=event)

   # After
   self.event_publisher.publish_deferred(event=event)  # No await
   ```

3. **Update Dependency Injection**:
   ```python
   # Before
   event_publisher = EventPublisher()

   # After
   base_publisher = EventPublisher()
   event_publisher = DeferredEventPublisher(db=db, event_publisher=base_publisher)
   ```

4. **Update Tests**:
   ```python
   # Before
   mock_publisher = AsyncMock(spec=EventPublisher)
   mock_publisher.publish.assert_called_once()

   # After
   mock_publisher = AsyncMock(spec=DeferredEventPublisher)
   mock_publisher.publish_deferred.assert_called_once()
   ```

## References

- [Transaction Management](TRANSACTION_MANAGEMENT.md) - FastAPI transaction patterns
- [SQLAlchemy Events](https://docs.sqlalchemy.org/en/20/core/event.html) - Event system documentation
- [RabbitMQ Best Practices](https://www.rabbitmq.com/reliability.html) - Message reliability patterns

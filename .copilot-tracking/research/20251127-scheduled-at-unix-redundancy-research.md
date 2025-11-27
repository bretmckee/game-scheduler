<!-- markdownlint-disable-file -->
# Task Research Notes: scheduled_at_unix Field Redundancy Analysis

## Research Executed

### File Analysis
- `shared/schemas/game.py`
  - `GameResponse` contains both `scheduled_at: str` (ISO 8601) and `scheduled_at_unix: int` fields
  - Both fields represent the same timestamp in different formats
- `shared/messaging/events.py`
  - `GameCreatedEvent` also contains both `scheduled_at: datetime` and `scheduled_at_unix: int`
- `services/api/services/games.py`
  - All instances compute `scheduled_at_unix` as `int(game.scheduled_at.timestamp())`
- `services/api/routes/games.py`
  - Routes compute `scheduled_at_unix` from `scheduled_at_utc.timestamp()`
- `services/bot/events/handlers.py`
  - Bot handlers compute `scheduled_at_unix` from `game.scheduled_at.timestamp()`
- `services/bot/events/publisher.py`
  - Publisher accepts both fields as separate parameters

### Code Search Results
- `scheduled_at_unix` field usage
  - Found in 25+ locations across codebase
  - All creation sites follow pattern: `scheduled_at_unix=int(datetime_obj.timestamp())`
  - No location performs complex logic - all are trivial conversions
- Frontend usage
  - `frontend/src/types/index.ts` defines field but never uses it
  - Only appears in test fixture `frontend/src/pages/__tests__/EditGame.test.tsx`

### Pattern Analysis
```python
# Pattern found in 6 locations:
scheduled_at_unix=int(game.scheduled_at.timestamp())
```

Locations:
1. `services/api/services/games.py:682` - Game creation event
2. `services/api/services/games.py:815` - Waitlist promotion notification
3. `services/api/routes/games.py:348` - API response creation
4. `services/bot/events/handlers.py:409` - Bot event handling
5. `tests/shared/messaging/test_events.py:91` - Test fixture
6. `tests/services/bot/events/test_publisher.py:82` - Test fixture

### External Research
- Unix timestamp conversion is a standard Python datetime operation
- Discord's timestamp formatting: `<t:unix_timestamp:F>` requires Unix epoch seconds
- No performance benefit to pre-computing: `timestamp()` is O(1) operation

## Key Discoveries

### Redundancy Confirmed
The `scheduled_at_unix` field is redundant because:

1. **Trivial Conversion**: Converting datetime to Unix timestamp is a one-line operation:
   ```python
   unix_timestamp = int(datetime_obj.timestamp())
   ```

2. **Always Computable**: Every location that has access to `scheduled_at` can compute the Unix timestamp

3. **Consistent Pattern**: All 6 creation sites use identical conversion logic - no variation or special cases

4. **No Performance Benefit**: The `timestamp()` method is an O(1) operation on datetime objects

5. **Frontend Unused**: TypeScript types define the field but no code actually uses it

### Where Unix Timestamps Are Actually Needed

**Discord Message Formatting**:
```python
# services/api/services/games.py:819
f"scheduled for <t:{scheduled_at_unix}:F>. "
```

**RabbitMQ Event Messages**:
```python
# shared/messaging/events.py:72
class GameCreatedEvent(BaseModel):
    scheduled_at: datetime
    scheduled_at_unix: int  # Sent to message consumers
```

**Notification Events**:
```python
# services/api/services/games.py:827
notification_event = messaging_events.NotificationSendDMEvent(
    game_time_unix=scheduled_at_unix,
    # ...
)
```

### Impact Analysis

**Files Requiring Changes**:
1. `shared/schemas/game.py` - Remove field from `GameResponse`
2. `shared/messaging/events.py` - Remove field from `GameCreatedEvent`
3. `services/api/services/games.py` - Compute Unix timestamp at point of use
4. `services/api/routes/games.py` - Remove from response construction
5. `services/bot/events/publisher.py` - Remove parameter, compute internally
6. `services/bot/events/handlers.py` - Remove from event construction
7. `frontend/src/types/index.ts` - Remove from TypeScript interface
8. Test files - Update fixtures

**Consumers Requiring Updates**:
- Any code consuming `GameCreatedEvent` from RabbitMQ
- Frontend code (already doesn't use it)
- Discord message formatting code (compute at point of use)

## Recommended Approach

Remove `scheduled_at_unix` field entirely and compute Unix timestamps at point of use.

### Benefits
1. **Single Source of Truth**: Only one timestamp representation in data models
2. **Reduced Data Transfer**: Smaller JSON payloads in API responses
3. **Less Maintenance**: No need to keep two fields in sync
4. **Clearer Intent**: Conversion happens where Unix format is needed
5. **Type Safety**: Frontend won't expect field that shouldn't be there

### Implementation Strategy

**Phase 1: Update Schemas and Events**
- Remove `scheduled_at_unix` from `GameResponse` in `shared/schemas/game.py`
- Remove `scheduled_at_unix` from `GameCreatedEvent` in `shared/messaging/events.py`

**Phase 2: Update API Layer**
- In `services/api/services/games.py`:
  - Remove `scheduled_at_unix` from event construction
  - Compute Unix timestamp inline where needed for Discord formatting
- In `services/api/routes/games.py`:
  - Remove `scheduled_at_unix` from response construction

**Phase 3: Update Bot Layer**
- In `services/bot/events/publisher.py`:
  - Remove `scheduled_at_unix` parameter from `publish_game_created()`
  - Compute Unix timestamp from `scheduled_at` string parameter
- In `services/bot/events/handlers.py`:
  - Remove `scheduled_at_unix` from event construction
  - Event consumers compute Unix timestamp from `scheduled_at` datetime

**Phase 4: Update Frontend**
- Remove `scheduled_at_unix` from TypeScript `Game` interface
- Remove from test fixtures

**Phase 5: Update Tests**
- Update all test fixtures to remove `scheduled_at_unix`
- Update assertions in timezone tests to compute expected Unix timestamp

### Conversion Helper Pattern

For consistency, use this pattern wherever Unix timestamp is needed:

```python
from datetime import datetime

def to_unix_timestamp(dt: datetime) -> int:
    """Convert datetime to Unix timestamp (seconds since epoch)."""
    return int(dt.timestamp())

# Usage in Discord formatting:
unix_ts = to_unix_timestamp(game.scheduled_at)
message = f"Game starts <t:{unix_ts}:F>"

# Usage in event construction:
event_data = SomeEvent(
    game_id=game.id,
    game_time_unix=to_unix_timestamp(game.scheduled_at),
)
```

## Implementation Guidance

- **Objectives**: 
  - Remove redundant `scheduled_at_unix` field from all schemas
  - Compute Unix timestamps only where needed for Discord/events
  - Maintain all existing functionality with cleaner data model

- **Key Tasks**:
  1. Remove field from `GameResponse` and `GameCreatedEvent` schemas
  2. Update all locations that construct these objects
  3. Add inline conversion where Unix timestamp is actually used
  4. Update frontend TypeScript types
  5. Update all test fixtures and assertions

- **Dependencies**: 
  - No external dependencies required
  - Changes are backward compatible at API level (field removal)
  - Frontend already doesn't use the field

- **Success Criteria**:
  - All tests pass after changes
  - API responses no longer include `scheduled_at_unix`
  - Discord message formatting still works correctly
  - RabbitMQ events still contain necessary timestamp data
  - No duplication of timestamp information in data models

<!-- markdownlint-disable-file -->
# Task Research Notes: Reducing Complexity of GameService::create_game()

## Research Executed

### File Analysis
- `services/api/services/games.py` (lines 87-430)
  - Function size: 344 lines
  - Cyclomatic complexity: 24 (threshold: 25)
  - Cognitive complexity: 48 (threshold: 49)
  - Worst offender in entire codebase by both metrics

### Code Structure Analysis
- Deep nesting with multiple conditional paths
- Host override logic with bot manager permission checks
- Participant resolution with validation
- Template field resolution with multiple ternary operations
- Database record creation in loops with type discrimination
- Schedule creation with conditional logic
- Multiple await points for database operations

### External Research
- Martin Fowler's "Refactoring" - Extract Method pattern
- Robert Martin's "Clean Code" - Single Responsibility Principle
- Cognitive Complexity whitepaper (SonarSource) - Nested conditions penalty

## Key Discoveries

### Function Overview
**Location**: `services/api/services/games.py:87-430`
**Purpose**: Create new game session from template with optional pre-populated participants
**Current State**: Monolithic function handling 8+ distinct responsibilities

### Complexity Breakdown by Section

#### 1. Host Override Logic (Lines 149-233)
**Size**: ~85 lines
**Cognitive Impact**: ~15 points
**Cyclomatic Impact**: ~8 paths

Deep nesting structure:
```python
if game_data.host and game_data.host.strip():
    # Check bot manager permission
    is_bot_manager = await role_service.check_bot_manager_permission(...)
    if not is_bot_manager:
        raise ValueError(...)

    # Resolve host mention
    (resolved_hosts, validation_errors) = await self.participant_resolver.resolve_initial_participants(...)
    if validation_errors:
        raise resolver_module.ValidationError(...)
    if not resolved_hosts:
        raise ValueError(...)

    # Validate host type
    if resolved_hosts[0].get("type") != "discord":
        raise resolver_module.ValidationError(...)

    # Get or create host user
    host_user_result = await self.db.execute(...)
    resolved_host_user = host_user_result.scalar_one_or_none()
    if resolved_host_user is None:
        # Create new user record
        resolved_host_user = user_model.User(...)
        self.db.add(resolved_host_user)
        await self.db.flush()

    actual_host_user_id = resolved_host_user.id
```

**Complexity Factors**:
- 5 levels of nesting
- Multiple database queries within nested conditions
- Error handling for validation failures
- Type discrimination logic
- User creation fallback

#### 2. Template Field Resolution (Lines 251-279)
**Size**: ~29 lines
**Cognitive Impact**: ~6 points
**Cyclomatic Impact**: ~7 paths

Stacked ternary operations:
```python
max_players = resolve_max_players(
    game_data.max_players if game_data.max_players is not None else template.max_players
)
reminder_minutes = (
    game_data.reminder_minutes
    if game_data.reminder_minutes is not None
    else (template.reminder_minutes or [60, 15])
)
expected_duration_minutes = (
    game_data.expected_duration_minutes
    if game_data.expected_duration_minutes is not None
    else template.expected_duration_minutes
)
where = game_data.where if game_data.where is not None else template.where
signup_instructions = (
    game_data.signup_instructions
    if game_data.signup_instructions is not None
    else template.signup_instructions
)
```

**Complexity Factors**:
- 6+ ternary operations
- Nested ternary with `or` fallback
- Field-by-field resolution logic
- No clear pattern extraction

#### 3. Signup Method Validation (Lines 281-292)
**Size**: ~12 lines
**Cognitive Impact**: ~3 points
**Cyclomatic Impact**: ~2 paths

```python
signup_method = (
    game_data.signup_method
    or template.default_signup_method
    or SignupMethod.SELF_SIGNUP.value
)

if template.allowed_signup_methods:
    if signup_method not in template.allowed_signup_methods:
        allowed_str = ", ".join(template.allowed_signup_methods)
        raise ValueError(
            f"Signup method '{signup_method}' not allowed for this template. "
            f"Allowed methods: {allowed_str}"
        )
```

#### 4. Participant Resolution (Lines 294-308)
**Size**: ~15 lines
**Cognitive Impact**: ~4 points
**Cyclomatic Impact**: ~2 paths

```python
valid_participants: list[dict[str, Any]] = []
if game_data.initial_participants:
    (
        valid_participants,
        validation_errors,
    ) = await self.participant_resolver.resolve_initial_participants(
        guild_config.guild_id,
        game_data.initial_participants,
        access_token,
    )

    if validation_errors:
        raise resolver_module.ValidationError(
            invalid_mentions=validation_errors,
            valid_participants=[p["original_input"] for p in valid_participants],
        )
```

#### 5. Game Session Creation (Lines 310-355)
**Size**: ~46 lines
**Cognitive Impact**: ~4 points
**Cyclomatic Impact**: ~1 path

Mostly straightforward object creation with timestamp conversion:
```python
if game_data.scheduled_at.tzinfo is not None:
    scheduled_at_naive = game_data.scheduled_at.astimezone(datetime.UTC).replace(tzinfo=None)
else:
    scheduled_at_naive = game_data.scheduled_at

game = game_model.GameSession(
    id=game_model.generate_uuid(),
    title=game_data.title,
    description=game_data.description,
    # ... 15+ more fields
)

self.db.add(game)
await self.db.flush()
```

#### 6. Participant Creation Loop (Lines 357-374)
**Size**: ~18 lines
**Cognitive Impact**: ~5 points
**Cyclomatic Impact**: ~2 paths

Loop with type discrimination:
```python
for position, participant_data in enumerate(valid_participants, start=1):
    if participant_data["type"] == "discord":
        user = await self.participant_resolver.ensure_user_exists(
            self.db, participant_data["discord_id"]
        )
        participant = participant_model.GameParticipant(
            game_session_id=game.id,
            user_id=user.id,
            display_name=None,
            position_type=ParticipantType.HOST_ADDED,
            position=position,
        )
    else:  # placeholder
        participant = participant_model.GameParticipant(
            game_session_id=game.id,
            user_id=None,
            display_name=participant_data["display_name"],
            position_type=ParticipantType.HOST_ADDED,
            position=position,
        )
    self.db.add(participant)
```

**Complexity Factors**:
- Loop adds cognitive complexity
- Type discrimination within loop
- Database operation for discord users
- Conditional object creation

#### 7. Game Reload and Notification Scheduling (Lines 376-394)
**Size**: ~19 lines
**Cognitive Impact**: ~2 points
**Cyclomatic Impact**: ~0 paths

```python
result = await self.db.execute(
    select(game_model.GameSession)
    .where(game_model.GameSession.id == game.id)
    .options(
        selectinload(game_model.GameSession.participants).selectinload(
            participant_model.GameParticipant.user
        )
    )
)
game = result.scalar_one()

await self._schedule_join_notifications_for_game(game)

schedule_service = notification_schedule_service.NotificationScheduleService(self.db)
await schedule_service.populate_schedule(game, reminder_minutes)
```

#### 8. Status Schedule Creation (Lines 396-418)
**Size**: ~23 lines
**Cognitive Impact**: ~4 points
**Cyclomatic Impact**: ~1 path

Conditional schedule setup:
```python
if game.status == game_model.GameStatus.SCHEDULED.value:
    # Create IN_PROGRESS transition at scheduled time
    in_progress_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.IN_PROGRESS.value,
        transition_time=game.scheduled_at,
        executed=False,
    )
    self.db.add(in_progress_schedule)

    # Calculate completion time with fallback
    duration_minutes = expected_duration_minutes or DEFAULT_GAME_DURATION_MINUTES
    completion_time = game.scheduled_at + datetime.timedelta(minutes=duration_minutes)

    # Create COMPLETED transition
    completed_schedule = game_status_schedule_model.GameStatusSchedule(
        id=str(uuid.uuid4()),
        game_id=game.id,
        target_status=game_model.GameStatus.COMPLETED.value,
        transition_time=completion_time,
        executed=False,
    )
    self.db.add(completed_schedule)
```

**Complexity Factors**:
- Conditional creation of 2 schedules
- Duration calculation with fallback
- Duplicate object creation pattern

#### 9. Finalization (Lines 420-430)
**Size**: ~11 lines
**Cognitive Impact**: ~1 point
**Cyclomatic Impact**: ~1 path

```python
await self.db.commit()

game = await self.get_game(game.id)
if game is None:
    raise ValueError("Failed to reload created game")

await self._publish_game_created(game, channel_config)

return game
```

## Recommended Approach

### Strategy: Extract Method Refactoring

Break the 344-line monolithic function into focused, single-responsibility methods.

### Phase 1: Host Resolution Extraction

**New Method**: `_resolve_game_host()`
```python
async def _resolve_game_host(
    self,
    game_data: game_schemas.GameCreateRequest,
    guild_config: guild_model.GuildConfiguration,
    requester_user_id: str,
    access_token: str,
) -> tuple[str, user_model.User]:
    """
    Resolve game host, handling override for bot managers.

    Returns:
        Tuple of (host_user_id, host_user_object)
    """
```

**Benefits**:
- Removes 85 lines from main function
- Reduces cyclomatic complexity by ~8
- Reduces cognitive complexity by ~15
- Isolated permission checking logic
- Testable in isolation

**Complexity Reduction**:
- Main function: cyclomatic 24→16, cognitive 48→33
- New method: cyclomatic ~8, cognitive ~15

### Phase 2: Template Field Resolution Extraction

**New Method**: `_resolve_template_fields()`
```python
def _resolve_template_fields(
    self,
    game_data: game_schemas.GameCreateRequest,
    template: template_model.GameTemplate,
) -> dict[str, Any]:
    """
    Resolve game fields from request data and template defaults.

    Returns:
        Dictionary of resolved field values
    """
```

**Benefits**:
- Removes 29 lines from main function
- Reduces cyclomatic complexity by ~7
- Reduces cognitive complexity by ~6
- Clear data transformation logic
- Easy to test with various input combinations

**Complexity Reduction**:
- Main function: cyclomatic 16→9, cognitive 33→27
- New method: cyclomatic ~7, cognitive ~6

### Phase 3: Participant Record Creation Extraction

**New Method**: `_create_participant_records()`
```python
async def _create_participant_records(
    self,
    game_id: str,
    valid_participants: list[dict[str, Any]],
) -> None:
    """
    Create participant records for pre-filled participants.

    Handles both Discord users and placeholder participants.
    """
```

**Benefits**:
- Removes 18 lines from main function
- Reduces cyclomatic complexity by ~2
- Reduces cognitive complexity by ~5
- Isolates type discrimination logic
- Testable with mock participants

**Complexity Reduction**:
- Main function: cyclomatic 9→7, cognitive 27→22
- New method: cyclomatic ~2, cognitive ~5

### Phase 4: Schedule Creation Extraction

**New Method**: `_create_game_status_schedules()`
```python
async def _create_game_status_schedules(
    self,
    game: game_model.GameSession,
    expected_duration_minutes: int | None,
) -> None:
    """
    Create status transition schedules for scheduled games.

    Creates IN_PROGRESS and COMPLETED transitions.
    """
```

**Benefits**:
- Removes 23 lines from main function
- Reduces cyclomatic complexity by ~1
- Reduces cognitive complexity by ~4
- Isolated schedule creation logic
- Can be reused for rescheduling

**Complexity Reduction**:
- Main function: cyclomatic 7→6, cognitive 22→18
- New method: cyclomatic ~1, cognitive ~4

### Phase 5: Final Structure

After all extractions, `create_game()` becomes orchestration:

```python
async def create_game(
    self,
    game_data: game_schemas.GameCreateRequest,
    host_user_id: str,
    access_token: str,
    thumbnail_data: bytes | None = None,
    thumbnail_mime_type: str | None = None,
    image_data: bytes | None = None,
    image_mime_type: str | None = None,
) -> game_model.GameSession:
    """
    Create new game session from template with optional pre-populated participants.
    """
    # Validate and load template
    template, guild_config, channel_config = await self._load_game_dependencies(
        game_data.template_id
    )

    # Resolve host (may override for bot managers)
    actual_host_user_id, host_user = await self._resolve_game_host(
        game_data, guild_config, host_user_id, access_token
    )

    # Check host permissions
    await self._validate_host_permissions(
        host_user, guild_config, template, access_token
    )

    # Resolve field values from request and template
    resolved_fields = self._resolve_template_fields(game_data, template)

    # Resolve and validate initial participants
    valid_participants = await self._resolve_and_validate_participants(
        game_data, guild_config, access_token
    )

    # Create game session
    game = await self._create_game_session(
        game_data, template, guild_config, channel_config,
        host_user, resolved_fields,
        thumbnail_data, thumbnail_mime_type, image_data, image_mime_type
    )

    # Create participant records
    await self._create_participant_records(game.id, valid_participants)

    # Reload with relationships
    game = await self._reload_game_with_relationships(game.id)

    # Schedule notifications and status transitions
    await self._schedule_game_notifications(game, resolved_fields["reminder_minutes"])
    await self._create_game_status_schedules(game, resolved_fields["expected_duration_minutes"])

    # Commit and publish
    await self.db.commit()
    game = await self.get_game(game.id)
    await self._publish_game_created(game, channel_config)

    return game
```

**Final Metrics**:
- Main function: ~80-100 lines (vs 344)
- Cyclomatic complexity: ~6-8 (vs 24)
- Cognitive complexity: ~10-15 (vs 48)
- All extracted methods: complexity < 10

## Implementation Guidance

### Objectives
1. Reduce `create_game()` complexity below threshold (cyclomatic < 15, cognitive < 20)
2. Create focused, testable helper methods
3. Maintain all existing functionality
4. Preserve error handling behavior
5. Enable progressive threshold reduction

### Key Tasks

**Step 1: Create Test Harness** (Prerequisites)
1. Review existing tests for `create_game()`
2. Ensure comprehensive coverage before refactoring
3. Add missing test cases if needed
4. Run tests to establish baseline

**Step 2: Extract Host Resolution** (First Extraction)
1. Create `_resolve_game_host()` method
2. Move lines 149-233 to new method
3. Update main function to call new method
4. Run tests to verify no behavior changes
5. Verify complexity reduction

**Step 3: Extract Template Field Resolution**
1. Create `_resolve_template_fields()` method
2. Move lines 251-279 to new method
3. Return dictionary of resolved fields
4. Update main function to use returned values
5. Run tests and verify

**Step 4: Extract Participant Creation**
1. Create `_create_participant_records()` method
2. Move lines 357-374 to new method
3. Update main function to call new method
4. Run tests and verify

**Step 5: Extract Schedule Creation**
1. Create `_create_game_status_schedules()` method
2. Move lines 396-418 to new method
3. Update main function to call new method
4. Run tests and verify

**Step 6: Optional Further Extraction**
1. Consider extracting dependency loading (template, guild, channel)
2. Consider extracting game session creation (object construction)
3. Consider extracting notification scheduling
4. Each extraction should be validated with tests

**Step 7: Update Complexity Thresholds**
1. Run complexity analysis on refactored code
2. Lower thresholds to new maximum values
3. Commit changes with updated thresholds

### Dependencies
- Existing test suite for `create_game()`
- SQLAlchemy async session behavior
- Participant resolver service
- Role verification service
- Notification schedule service

### Success Criteria
1. All existing tests pass ✅
2. Cyclomatic complexity < 15 ✅
3. Cognitive complexity < 20 ✅
4. All extracted methods have complexity < 10 ✅
5. No changes to public API or behavior ✅
6. Code is more readable and maintainable ✅

### Testing Strategy
- Run full test suite after each extraction
- Focus on `test_games.py` integration tests
- Verify error handling paths still work
- Test with various input combinations:
  - With/without host override
  - With/without initial participants
  - With/without template defaults
  - Various signup methods
  - Discord users vs placeholders

### Risks and Mitigations

**Risk**: Breaking database transaction behavior
**Mitigation**: Keep all `await self.db.flush()` and `await self.db.commit()` in same locations

**Risk**: Changing error messages or exception types
**Mitigation**: Copy error handling exactly from original code

**Risk**: Introducing subtle bugs in complex logic
**Mitigation**: Extract one method at a time, test thoroughly, commit frequently

**Risk**: Making code less readable with too many small methods
**Mitigation**: Only extract methods with clear single responsibilities, maintain meaningful names

## Alternative Approaches Considered

### Alternative 1: Split into Multiple Service Methods
Instead of private helper methods, create separate public service methods like `create_game_with_host_override()`, `create_game_simple()`.

**Rejected Because**:
- Creates confusing API with multiple entry points
- Doesn't reduce complexity, just distributes it
- Harder to maintain consistent behavior

### Alternative 2: Use Builder Pattern
Create a `GameSessionBuilder` class to handle incremental construction.

**Rejected Because**:
- Adds significant complexity (new class, state management)
- Overkill for this use case
- Harder to understand flow
- Not idiomatic Python/FastAPI pattern

### Alternative 3: Use Strategy Pattern for Host Resolution
Create separate strategy classes for different host resolution types.

**Rejected Because**:
- Over-engineering for two simple cases (normal vs override)
- Adds boilerplate without clear benefit
- Makes code harder to follow

### Alternative 4: Leave as-is, Just Add Comments
Document sections with comments instead of extracting methods.

**Rejected Because**:
- Doesn't reduce complexity metrics
- Comments can become stale
- Doesn't improve testability
- Doesn't enable threshold reduction

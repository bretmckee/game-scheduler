<!-- markdownlint-disable-file -->
# Task Research Notes: Further Reduction of create_game() Method

## Research Executed

### File Analysis
- services/api/services/games.py (lines 333-511)
  - Method length: 179 lines after Phase 1-5 refactoring
  - Statement count: 46 statements (via AST analysis)
  - Cyclomatic complexity: 10 (down from original 24)
  - Cognitive complexity: 10 (down from original 48)
  - Status: Passes all linter checks (C901, PLR0912, PLR0915)

### Code Structure Analysis
Analyzed remaining concerns in create_game() after initial refactoring:
- Load template/guild/channel configs: 38 lines (3 DB queries + validation)
- Resolve host and check permissions: 14 lines (calls extracted method)
- Resolve template fields: 6 lines (calls extracted method)
- Resolve initial participants: 17 lines (participant validation logic)
- Create game session object: 35 lines (timezone handling + 20-parameter construction)
- Persist and reload game: 19 lines (DB operations + eager loading)
- Schedule setup: 9 lines (3 different schedule operations)
- Commit and reload: 4 lines (transaction finalization)
- Publish event: 2 lines (event publishing)

### Complexity Tool Verification
```bash
# Radon cyclomatic complexity
uv run radon cc services/api/services/games.py -s
# Result: create_game - B (10)

# Complexipy cognitive complexity
uv run pre-commit run complexipy --files services/api/services/games.py --verbose
# Result: create_game - 10

# Ruff linter checks
uv run ruff check services/api/services/games.py --select C901,PLR0912,PLR0915
# Result: All checks passed
```

### Project Conventions
- Python instructions: #file:../../.github/instructions/python.instructions.md
- Extract Method pattern already used: `_resolve_game_host()`, `_resolve_template_fields()`, `_create_participant_records()`, `_create_game_status_schedules()`
- Service layer pattern: Business logic in service, models as data containers

## Key Discoveries

### Current State Analysis

**After Phases 1-5 Refactoring:**
- Original: 344 lines, complexity 24, cognitive 48
- Current: 179 lines, complexity 10, cognitive 10
- **Reduction: 48% smaller, 58% less cyclomatic complexity, 79% less cognitive complexity**
- **Goals achieved**: ✅ Cyclomatic < 15, ✅ Cognitive < 20

**Why Still 179 Lines:**
Method orchestrates complex business process with:
- 3 dependency loading queries (template, guild, channel)
- Host resolution with permission checking
- Template field resolution
- Participant validation and resolution
- Game object construction with 20 parameters
- Database persistence with eager loading
- 3 schedule setup operations
- Event publishing

### Refactoring Opportunities Analysis

#### Opportunity 1: Extract Dependency Loading (HIGH IMPACT - 38 lines)

**Current Code:**
```python
# Get template
template_result = await self.db.execute(
    select(template_model.GameTemplate).where(...)
)
template = template_result.scalar_one_or_none()
if template is None:
    raise ValueError(...)

# Get guild config for permission checks
guild_result = await self.db.execute(
    select(guild_model.GuildConfiguration).where(...)
)
guild_config = guild_result.scalar_one_or_none()
if guild_config is None:
    raise ValueError(...)

# Get channel config
channel_result = await self.db.execute(
    select(channel_model.ChannelConfiguration).where(...)
)
channel_config = channel_result.scalar_one_or_none()
if channel_config is None:
    raise ValueError(...)
```

**Proposed Extraction:**
```python
async def _load_game_dependencies(
    self, template_id: str
) -> tuple[
    template_model.GameTemplate,
    guild_model.GuildConfiguration,
    channel_model.ChannelConfiguration
]:
    """Load and validate template, guild, and channel configurations."""
    # Implementation with all 3 queries
    return template, guild_config, channel_config
```

**Benefits:**
- Reduces create_game() by ~35 lines
- Groups related data loading operations
- Single responsibility: dependency loading
- Easy to test independently

**Impact:** HIGH - Largest single extraction opportunity

#### Opportunity 2: Extract Game Object Builder (HIGH IMPACT - 35 lines)

**Current Code: 20-parameter GameSession construction with timezone handling**

**Proposed Extraction (Option 1 - 9 parameters):**
```python
def _build_game_session(
    self,
    game_data: game_schemas.GameCreateRequest,
    template: template_model.GameTemplate,
    guild_config: guild_model.GuildConfiguration,
    host_user: user_model.User,
    resolved_fields: dict[str, Any],
    thumbnail_data: bytes | None,
    thumbnail_mime_type: str | None,
    image_data: bytes | None,
    image_mime_type: str | None,
) -> game_model.GameSession:
    """Build GameSession instance with normalized data."""
    # Extract from template inside the method
    channel_id = template.channel_id
    notify_role_ids = template.notify_role_ids
    allowed_player_role_ids = template.allowed_player_role_ids

    # Timezone normalization + construction
```

**Proposed Extraction (Option 2 - 6 parameters) ✅ RECOMMENDED:**
```python
@dataclass
class GameMediaAttachments:
    """Media attachments for game creation."""
    thumbnail_data: bytes | None = None
    thumbnail_mime_type: str | None = None
    image_data: bytes | None = None
    image_mime_type: str | None = None

def _build_game_session(
    self,
    game_data: game_schemas.GameCreateRequest,
    template: template_model.GameTemplate,
    guild_config: guild_model.GuildConfiguration,
    host_user: user_model.User,
    resolved_fields: dict[str, Any],
    media: GameMediaAttachments,
) -> game_model.GameSession:
    """Build GameSession instance with normalized data."""
    # Extract from template
    channel_id = template.channel_id
    notify_role_ids = template.notify_role_ids
    allowed_player_role_ids = template.allowed_player_role_ids

    # Timezone normalization + construction
```

**Call site:**
```python
media = GameMediaAttachments(
    thumbnail_data=thumbnail_data,
    thumbnail_mime_type=thumbnail_mime_type,
    image_data=image_data,
    image_mime_type=image_mime_type,
)

game = self._build_game_session(
    game_data,
    template,
    guild_config,
    host_user,
    resolved_fields,
    media,
)
```

**Benefits:**
- Reduces create_game() by ~33 lines
- Encapsulates timezone normalization logic
- Isolates 20-parameter GameSession construction
- **Only 6 parameters** (using media object) or 9 (without)
- Groups media attachments logically
- Makes it clear media is optional as a unit
- Matches existing pattern (non-async helper methods)

**Impact:** HIGH - Second largest extraction opportunity

**Constructor Pattern Analysis:**
- ❌ Builder Pattern: Heavyweight (~50 lines boilerplate), conflicts with SQLAlchemy ORM
- ❌ Factory Method on Model: Violates separation of concerns, couples model to business logic
- ✅ Private Helper Method: Pythonic, follows existing codebase pattern
- ✅ Parameter Object for Media: Excellent for grouping related optional parameters

**Parameter Reduction Strategy:**
The goal is to reduce the ~20 parameters in GameSession construction to a manageable number for the helper method:

1. **Extract from passed objects** (saves 3 params):
   - `channel_id`, `notify_role_ids`, `allowed_player_role_ids` can be extracted from `template` inside the helper
   - Don't pass what you can derive!

2. **Group related parameters** (saves 3 params):
   - Use `GameMediaAttachments` dataclass to group 4 media parameters into 1
   - Clear that media is optional as a unit
   - Easy to add validation

**Result:** 6 clean parameters instead of 12+

**Parameter Count Comparison:**
- GameSession constructor: 20 parameters
- Helper without optimization: 12 parameters (proposed initially)
- Helper with extraction: 9 parameters (extract from template)
- Helper with media grouping: **6 parameters ✅ RECOMMENDED**

**Domain Model Analysis:**
- GameSession has 24 fields across 8 concerns
- **Should NOT be decomposed via composition:**
  - Event entities are naturally "wide" (Google Calendar: 40+ fields)
  - Fields are cohesive - all answer "What is this game event?"
  - No independent lifecycle
  - Industry norm for event systems
- **But CAN use Parameter Object for helper method parameters** - this is about reducing parameter count to the construction helper, not changing the domain model

#### Opportunity 3: Extract Schedule Orchestration (MEDIUM IMPACT - 9 lines)

**Proposed Extraction:**
```python
async def _setup_game_schedules(
    self,
    game: game_model.GameSession,
    reminder_minutes: list[int],
    expected_duration_minutes: int | None,
) -> None:
    """Set up all game schedules (join notifications, reminders, status transitions)."""
    # 3 schedule operations
```

**Benefits:**
- Reduces create_game() by ~7 lines
- Groups all schedule-related operations
- Clear intent: "set up all schedules"

**Impact:** MEDIUM - Moderate improvement in clarity

#### Opportunity 4: Extract Persistence Logic (MEDIUM IMPACT - 23 lines)

**Concerns:**
- Splits transaction boundary across methods
- Less clear when commit happens
- May reduce clarity of data lifecycle

**Impact:** MEDIUM - Modest value, may reduce transaction clarity

#### Opportunity 5: Extract Participant Validation (LOW IMPACT - 17 lines)

**Assessment:**
- The if-block is already fairly clear
- Extraction adds little readability benefit

**Impact:** LOW - Minimal value

## Recommended Approach

### Phase A: Extract Top 2 (Opportunities 1 + 2)
**Target**: ~65-75 lines ✅ **Excellent maintainability**

1. Extract `_load_game_dependencies()` - saves ~35 lines
2. Extract `_build_game_session()` - saves ~33 lines
3. Final length: ~75 lines

### Phase B: Add Schedule Orchestration (Opportunity 3)
**Target**: ~55-65 lines ✅ **Ideal length**

4. Extract `_setup_game_schedules()` - saves ~7 lines
5. Final length: ~60 lines

### Phase C: Consider Persistence (Opportunity 4) - Optional
**Target**: ~40-50 lines ⚠️ **Risk of over-extraction**

6. Extract `_persist_and_reload_game()` - saves ~15 lines
7. Final length: ~45 lines

**Caution:** May obscure transaction boundaries

## Alternative Patterns Rejected

### Builder Pattern for GameSession Construction
- Heavyweight (~50 lines of boilerplate)
- Conflicts with SQLAlchemy ORM
- Non-Pythonic for data models

### Factory Method on GameSession Model
- Violates separation of concerns
- Couples model to business logic
- Anti-pattern in Domain-Driven Design

### Domain Model Decomposition via Composition
- GameSession is appropriately modeled as aggregate root
- 24 fields is reasonable for event entity
- No independent lifecycle for sub-components
- Industry norm (Google Calendar: 40+, Outlook: 50+ fields)

### Parameter Object Pattern (Full Context Wrapper)
- Wrapping all parameters in single context object is over-abstraction
- Creates single-use wrapper that hides what inputs are needed
- Makes testing harder and reduces clarity
- **BUT**: Parameter Object for media attachments IS appropriate
  - Groups 4 related optional parameters into 1
  - Clear semantic meaning
  - Reduces parameter count from 9 to 6

## Summary

The create_game() method has been successfully refactored from 344 lines to 179 lines, achieving complexity goals. Further reduction opportunities:

**Recommended:**
- ✅ Phase A: Extract dependency loading + game builder → ~75 lines
  - Use 6-parameter version of `_build_game_session()` with `GameMediaAttachments` dataclass
  - Extract template fields inside helper (channel_id, notify_role_ids, allowed_player_role_ids)
- ✅ Phase B: Extract schedule orchestration → ~60 lines

**Optional:**
- ⚠️ Phase C: Extract persistence logic → ~45 lines

**Not Recommended:**
- ❌ Domain model decomposition via SQLAlchemy composite columns
- ❌ Builder pattern (conflicts with SQLAlchemy ORM)
- ❌ Factory methods on model (violates separation of concerns)
- ❌ Full context wrapper object (over-abstraction)

**Recommended Pattern:**
- ✅ Parameter Object for media (groups 4 related params)
- ✅ Extract derived values inside helper methods
- ✅ Keep domain model unchanged

Focus should be on clear orchestration while keeping complexity low, not achieving shortest possible line count.

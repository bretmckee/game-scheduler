<!-- markdownlint-disable-file -->

# Task Details: Further Reduction of create_game() Method

## Research Reference

**Source Research**: #file:../research/20260115-create-game-further-reduction-research.md

## Phase A: Extract Dependency Loading and Game Builder

### Task A.1: Create GameMediaAttachments dataclass

Create a dataclass to group the 4 media attachment parameters into a single parameter object.

- **Files**:
  - services/api/services/games.py - Add dataclass at module level
- **Success**:
  - GameMediaAttachments dataclass created with 4 optional fields
  - Fields: thumbnail_data, thumbnail_mime_type, image_data, image_mime_type
  - Follows Python dataclass conventions
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 95-130) - GameMediaAttachments specification
- **Dependencies**:
  - None

### Task A.2: Extract _load_game_dependencies() helper method

Extract the 38 lines of dependency loading (template, guild config, channel config) into a dedicated helper method.

- **Files**:
  - services/api/services/games.py - Add new private async method
- **Success**:
  - Method signature: `async def _load_game_dependencies(self, template_id: str) -> tuple[GameTemplate, GuildConfiguration, ChannelConfiguration]`
  - Loads template, guild config, and channel config
  - Raises ValueError if any dependency is missing
  - Clear docstring explaining purpose
  - Reduces create_game() by ~35 lines
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 52-92) - Dependency loading extraction specification
- **Dependencies**:
  - None

### Task A.3: Add unit tests for _load_game_dependencies()

Create comprehensive unit tests for the dependency loading helper method.

- **Files**:
  - tests/services/api/test_games_service.py - Add new test functions
- **Success**:
  - Test _load_game_dependencies() with valid template_id
  - Test _load_game_dependencies() with missing template (ValueError)
  - Test _load_game_dependencies() with missing guild config (ValueError)
  - Test _load_game_dependencies() with missing channel config (ValueError)
  - All tests use appropriate mocks and fixtures
  - Tests follow project testing conventions
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 52-92) - Dependency loading specification
- **Dependencies**:
  - Task A.2 (_load_game_dependencies)

### Task A.4: Extract _build_game_session() helper method

Extract the 35 lines of GameSession object construction into a dedicated helper method using 6 parameters.

- **Files**:
  - services/api/services/games.py - Add new private method
- **Success**:
  - Method signature: `def _build_game_session(self, game_data: GameCreateRequest, template: GameTemplate, guild_config: GuildConfiguration, host_user: User, resolved_fields: dict[str, Any], media: GameMediaAttachments) -> GameSession`
  - Extracts channel_id, notify_role_ids, allowed_player_role_ids from template inside method
  - Handles timezone normalization
  - Constructs GameSession with all 20 parameters
  - Returns GameSession instance
  - Clear docstring explaining purpose
  - Reduces create_game() by ~33 lines
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 95-180) - Game builder extraction with parameter reduction strategy
- **Dependencies**:
  - Task A.1 (GameMediaAttachments dataclass)

### Task A.5: Add unit tests for _build_game_session()

Create comprehensive unit tests for the game builder helper method.

- **Files**:
  - tests/services/api/test_games_service.py - Add new test functions
- **Success**:
  - Test _build_game_session() with all parameters
  - Test _build_game_session() with media attachments
  - Test _build_game_session() without media attachments
  - Test _build_game_session() timezone normalization
  - All tests use appropriate mocks and fixtures
  - Tests follow project testing conventions
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 95-180) - Game builder specification
- **Dependencies**:
  - Task A.4 (_build_game_session)

### Task A.6: Refactor create_game() to use new helper methods

Update create_game() to call the new helper methods, reducing overall method length.

- **Files**:
  - services/api/services/games.py (lines 333-511) - Update create_game() method
- **Success**:
  - Replace dependency loading code with call to _load_game_dependencies()
  - Create GameMediaAttachments instance from 4 media parameters
  - Replace game construction code with call to _build_game_session()
  - Method reduced from 179 lines to ~110 lines
  - All existing functionality preserved
  - All parameters and return types unchanged
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 279-295) - Phase A implementation summary
- **Dependencies**:
  - Task A.2 (_load_game_dependencies)
  - Task A.4 (_build_game_session)

### Task A.7: Remove redundant create_game() tests

Identify and remove tests of create_game() that now duplicate coverage provided by helper method tests.

- **Files**:
  - tests/services/api/test_games_service.py - Review and clean up tests
- **Success**:
  - Remove tests that specifically validate dependency loading behavior (now in _load_game_dependencies tests)
  - Remove tests that specifically validate game construction logic (now in _build_game_session tests)
  - Retain integration-level tests that verify end-to-end behavior
  - No decrease in overall test coverage
  - Document which tests were removed and why in changes file
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 279-295) - Refactoring summary
- **Dependencies**:
  - Task A.3 (tests for _load_game_dependencies)
  - Task A.5 (tests for _build_game_session)

## Phase B: Extract Schedule Orchestration

### Task B.1: Extract _setup_game_schedules() helper method

Extract the 9 lines of schedule setup into a dedicated helper method.

- **Files**:
  - services/api/services/games.py - Add new private async method
- **Success**:
  - Method signature: `async def _setup_game_schedules(self, game: GameSession, reminder_minutes: list[int], expected_duration_minutes: int | None) -> None`
  - Calls schedule_join_notifications()
  - Calls schedule_reminders() if reminder_minutes provided
  - Calls schedule_status_transitions() if expected_duration_minutes provided
  - Clear docstring explaining purpose
  - Reduces create_game() by ~7 lines
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 182-200) - Schedule orchestration extraction
- **Dependencies**:
  - Phase A completion

### Task B.2: Add unit tests for _setup_game_schedules()

Create unit tests for the schedule orchestration helper method.

- **Files**:
  - tests/services/api/test_games_service.py - Add new test functions
- **Success**:
  - Test _setup_game_schedules() calls all 3 schedule methods
  - Test _setup_game_schedules() with reminder_minutes provided
  - Test _setup_game_schedules() without reminder_minutes
  - Test _setup_game_schedules() with expected_duration_minutes
  - Test _setup_game_schedules() without expected_duration_minutes
  - All tests use appropriate mocks
  - Tests verify correct parameters passed to schedule methods
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 182-200) - Schedule orchestration specification
- **Dependencies**:
  - Task B.1 (_setup_game_schedules)

### Task B.3: Refactor create_game() to use schedule helper

Update create_game() to call the schedule orchestration helper method.

- **Files**:
  - services/api/services/games.py (lines 333-511) - Update create_game() method
- **Success**:
  - Replace 3 schedule operation calls with single call to _setup_game_schedules()
  - Method reduced from ~110 lines to ~60-65 lines
  - All existing functionality preserved
  - All parameters and return types unchanged
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 297-303) - Phase B implementation summary
- **Dependencies**:
  - Task B.1 (_setup_game_schedules)

## Phase C: Validation and Metrics

### Task C.1: Run complexity metrics verification

Verify that the refactored code meets complexity targets.

- **Files**:
  - services/api/services/games.py - Analyze with complexity tools
- **Success**:
  - Cyclomatic complexity < 15 (run: `uv run ruff check services/api/services/games.py --select C901`)
  - Cognitive complexity < 20 (run: `uv run pre-commit run complexipy --files services/api/services/games.py --verbose`)
  - Method length 60-75 lines
  - Document metrics in changes file
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 13-26) - Complexity tool verification examples
- **Dependencies**:
  - Phase B completion

### Task C.2: Verify all tests pass with full coverage

Run test suite and verify coverage is maintained or improved.

- **Files**:
  - tests/services/api/test_games_service.py - Run test suite
- **Success**:
  - All existing tests pass
  - All new tests pass
  - Coverage maintained or improved for games.py
  - No integration test failures
  - Document test results in changes file
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 279-327) - Implementation summary with testing requirements
- **Dependencies**:
  - All Phase A and B tasks complete

### Task C.3: Run linter checks

Verify all code passes linter checks.

- **Files**:
  - services/api/services/games.py - Run linter
- **Success**:
  - All ruff checks pass (run: `uv run ruff check services/api/services/games.py`)
  - No C901 (complexity) violations
  - No PLR0912 (too many branches) violations
  - No PLR0915 (too many statements) violations
  - Code follows all Python conventions
- **Research References**:
  - #file:../research/20260115-create-game-further-reduction-research.md (Lines 18-26) - Linter verification
- **Dependencies**:
  - Phase B completion

## Dependencies

- SQLAlchemy ORM for database operations
- pytest for testing framework
- ruff linter with C901 (cyclomatic complexity) check
- complexipy for cognitive complexity analysis

## Success Criteria

- create_game() method length: 60-75 lines (down from 179)
- Cyclomatic complexity < 15 (currently 10, should remain low)
- Cognitive complexity < 20 (currently 10, should remain low)
- All existing tests pass
- New helper methods have comprehensive unit tests
- Redundant tests removed without coverage loss
- All linter checks pass
- Code follows Python conventions

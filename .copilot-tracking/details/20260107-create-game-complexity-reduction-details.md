<!-- markdownlint-disable-file -->

# Task Details: Reducing Complexity of GameService::create_game()

## Research Reference

**Source Research**: #file:../research/20260107-create-game-complexity-reduction-research.md

## Phase 1: Test Harness Validation

### Task 1.1: Review existing test coverage for `create_game()`

Review all tests in `tests/services/api/test_games.py` that exercise the `create_game()` method to ensure comprehensive coverage before refactoring.

- **Files**:
  - tests/services/api/test_games.py - Test suite for GameService
- **Success**:
  - Identified all test cases covering `create_game()` functionality
  - Verified tests cover host override, initial participants, template defaults, various signup methods
  - Confirmed tests cover both Discord users and placeholder participants
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 392-411) - Testing strategy details
- **Dependencies**:
  - None

### Task 1.2: Run tests to establish baseline

Execute the full test suite to establish a passing baseline before any refactoring changes.

- **Files**:
  - tests/services/api/test_games.py - Tests to execute
- **Success**:
  - All tests pass without errors
  - Baseline established for comparison after refactoring
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 392-411) - Testing strategy
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Host Resolution Extraction

### Task 2.1: Create `_resolve_game_host()` method

Extract lines 149-233 from `create_game()` into a new private method that handles host resolution with bot manager override logic.

- **Files**:
  - services/api/services/games.py - Add new method before `create_game()`
- **Success**:
  - New method created with signature: `async def _resolve_game_host(self, game_data, guild_config, requester_user_id, access_token) -> tuple[str, user_model.User]`
  - Method returns tuple of (host_user_id, host_user_object)
  - All permission checking, validation, and user creation logic preserved
  - Method complexity: cyclomatic ~8, cognitive ~15
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 54-109) - Host override logic breakdown
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 230-263) - Phase 1 extraction details
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Update `create_game()` to call new method

Replace the host resolution logic in `create_game()` with a call to `_resolve_game_host()`.

- **Files**:
  - services/api/services/games.py - Modify `create_game()` method
- **Success**:
  - Lines 149-233 replaced with single method call
  - Returned values properly assigned to `actual_host_user_id` and `host_user`
  - No functional changes to behavior
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 230-263) - Phase 1 details
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Verify tests pass and complexity reduced

Run tests and verify complexity metrics improved after host resolution extraction.

- **Files**:
  - tests/services/api/test_games.py - Execute tests
  - services/api/services/games.py - Check complexity
- **Success**:
  - All tests pass without modification
  - `create_game()` cyclomatic complexity reduced from 24 to ~16
  - `create_game()` cognitive complexity reduced from 48 to ~33
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 257-263) - Expected complexity reduction
- **Dependencies**:
  - Task 2.2 completion

## Phase 3: Template Field Resolution Extraction

### Task 3.1: Create `_resolve_template_fields()` method

Extract lines 251-279 from `create_game()` into a new private method that resolves field values from request data and template defaults.

- **Files**:
  - services/api/services/games.py - Add new method before `create_game()`
- **Success**:
  - New method created with signature: `def _resolve_template_fields(self, game_data, template) -> dict[str, Any]`
  - Method returns dictionary with keys: max_players, reminder_minutes, expected_duration_minutes, where, signup_instructions, signup_method
  - All ternary operations and fallback logic preserved
  - Method complexity: cyclomatic ~7, cognitive ~6
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 111-156) - Template field resolution breakdown
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 265-284) - Phase 2 extraction details
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Update `create_game()` to use resolved fields dictionary

Replace the template field resolution logic in `create_game()` with a call to `_resolve_template_fields()` and use the returned dictionary.

- **Files**:
  - services/api/services/games.py - Modify `create_game()` method
- **Success**:
  - Lines 251-279 replaced with single method call
  - Dictionary values accessed throughout remainder of function
  - No functional changes to behavior
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 265-284) - Phase 2 details
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Verify tests pass and complexity reduced

Run tests and verify complexity metrics improved after template field extraction.

- **Files**:
  - tests/services/api/test_games.py - Execute tests
  - services/api/services/games.py - Check complexity
- **Success**:
  - All tests pass without modification
  - `create_game()` cyclomatic complexity reduced from ~16 to ~9
  - `create_game()` cognitive complexity reduced from ~33 to ~27
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 278-284) - Expected complexity reduction
- **Dependencies**:
  - Task 3.2 completion

## Phase 4: Participant Record Creation Extraction

### Task 4.1: Create `_create_participant_records()` method

Extract lines 357-374 from `create_game()` into a new private method that creates participant records for pre-filled participants.

- **Files**:
  - services/api/services/games.py - Add new method before `create_game()`
- **Success**:
  - New method created with signature: `async def _create_participant_records(self, game_id, valid_participants) -> None`
  - Method handles both Discord users and placeholder participants
  - Type discrimination logic preserved
  - Database flush operations preserved in correct locations
  - Method complexity: cyclomatic ~2, cognitive ~5
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 201-234) - Participant creation loop breakdown
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 286-305) - Phase 3 extraction details
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Update `create_game()` to call new method

Replace the participant creation loop in `create_game()` with a call to `_create_participant_records()`.

- **Files**:
  - services/api/services/games.py - Modify `create_game()` method
- **Success**:
  - Lines 357-374 replaced with single method call
  - No functional changes to behavior
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 286-305) - Phase 3 details
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Verify tests pass and complexity reduced

Run tests and verify complexity metrics improved after participant creation extraction.

- **Files**:
  - tests/services/api/test_games.py - Execute tests
  - services/api/services/games.py - Check complexity
- **Success**:
  - All tests pass without modification
  - `create_game()` cyclomatic complexity reduced from ~9 to ~7
  - `create_game()` cognitive complexity reduced from ~27 to ~22
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 299-305) - Expected complexity reduction
- **Dependencies**:
  - Task 4.2 completion

## Phase 5: Status Schedule Creation Extraction

### Task 5.1: Create `_create_game_status_schedules()` method

Extract lines 396-418 from `create_game()` into a new private method that creates status transition schedules for scheduled games.

- **Files**:
  - services/api/services/games.py - Add new method before `create_game()`
- **Success**:
  - New method created with signature: `async def _create_game_status_schedules(self, game, expected_duration_minutes) -> None`
  - Method creates IN_PROGRESS and COMPLETED transition schedules
  - Conditional logic for scheduled games preserved
  - Duration fallback logic preserved
  - Method complexity: cyclomatic ~1, cognitive ~4
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 256-290) - Status schedule creation breakdown
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 307-326) - Phase 4 extraction details
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Update `create_game()` to call new method

Replace the status schedule creation logic in `create_game()` with a call to `_create_game_status_schedules()`.

- **Files**:
  - services/api/services/games.py - Modify `create_game()` method
- **Success**:
  - Lines 396-418 replaced with single method call
  - No functional changes to behavior
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 307-326) - Phase 4 details
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Verify tests pass and complexity reduced

Run tests and verify complexity metrics improved after schedule creation extraction.

- **Files**:
  - tests/services/api/test_games.py - Execute tests
  - services/api/services/games.py - Check complexity
- **Success**:
  - All tests pass without modification
  - `create_game()` cyclomatic complexity reduced from ~7 to ~6
  - `create_game()` cognitive complexity reduced from ~22 to ~18
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 320-326) - Expected complexity reduction
- **Dependencies**:
  - Task 5.2 completion

## Phase 6: Optional Further Refinements

### Task 6.1: Consider additional extractions

Evaluate whether additional extractions would improve readability without over-fragmenting the code.

- **Files**:
  - services/api/services/games.py - Review remaining code
- **Success**:
  - Evaluated dependency loading extraction (template, guild, channel)
  - Evaluated game session creation extraction (object construction)
  - Evaluated notification scheduling extraction
  - Decided on final structure balancing readability and maintainability
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 328-377) - Phase 5 final structure
- **Dependencies**:
  - Phase 5 completion

### Task 6.2: Verify final complexity metrics

Run final complexity analysis to confirm all targets met.

- **Files**:
  - services/api/services/games.py - Analyze complexity
- **Success**:
  - `create_game()` cyclomatic complexity < 15 (target met)
  - `create_game()` cognitive complexity < 20 (target met)
  - All extracted methods have complexity < 10
  - Function length reduced from 344 to ~80-100 lines
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 367-377) - Final metrics
- **Dependencies**:
  - Task 6.1 completion

## Phase 7: Update Complexity Thresholds

### Task 7.1: Update Ruff configuration with new thresholds

Lower complexity thresholds in pyproject.toml to new maximum values to prevent future regressions.

- **Files**:
  - pyproject.toml - Update Ruff configuration
- **Success**:
  - Cyclomatic complexity threshold reduced to 15 or lower
  - Cognitive complexity threshold reduced to 20 or lower
  - Configuration changes committed
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 379-390) - Threshold update guidance
- **Dependencies**:
  - Phase 6 completion

### Task 7.2: Verify all checks pass with new thresholds

Run full linting suite to ensure no other files exceed new thresholds.

- **Files**:
  - All Python files in codebase
- **Success**:
  - Ruff checks pass without warnings
  - Pre-commit hooks pass
  - No other files exceed new thresholds
- **Research References**:
  - #file:../research/20260107-create-game-complexity-reduction-research.md (Lines 379-390) - Threshold verification
- **Dependencies**:
  - Task 7.1 completion

## Dependencies

- Existing test suite for `create_game()` in tests/services/api/test_games.py
- SQLAlchemy async session behavior understanding
- Participant resolver service implementation
- Role verification service implementation
- Notification schedule service implementation
- Ruff linting tool installed and configured

## Success Criteria

- All existing tests pass without modification
- Cyclomatic complexity reduced from 24 to below 15
- Cognitive complexity reduced from 48 to below 20
- All extracted methods have complexity below 10
- No changes to public API or behavior
- Code is more readable and maintainable
- Function length reduced from 344 to ~80-100 lines
- Complexity thresholds updated to prevent regression

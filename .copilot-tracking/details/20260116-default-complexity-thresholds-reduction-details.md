<!-- markdownlint-disable-file -->

# Task Details: Reduce Complexity Thresholds to Default Values

## Research Reference

**Source Research**: #file:../research/20260116-default-complexity-thresholds-reduction-research.md

## Phase 1: High-Priority Dual Violations (8 functions)

Target functions violating both cyclomatic (>10) and cognitive (>15) thresholds for maximum impact.

**Expected Impact**: Reduce thresholds from C901:17→12 and complexipy:20→17 after completion.

**Refactoring Pattern**: Apply Extract Method pattern from create_game() success (Lines 118-127 in research).

### Task 1.1: Refactor routes/games.py `update_game` (C:14/Cog:20)

Extract validation, permission checks, and response building into separate methods.

- **Files**:
  - services/api/routes/games.py - Refactor update_game endpoint function
  - tests/services/api/routes/test_games.py - Add unit tests for extracted methods
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for each extracted helper method with 100% coverage
  - All existing integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 19, 48) - Function identified in violations
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 118-127) - Proven refactoring techniques
- **Dependencies**:
  - Existing integration test coverage for update_game endpoint

### Task 1.2: Refactor services/display_names.py `resolve_display_names_and_avatars` (C:12/Cog:19)

Extract Discord API interaction and caching logic into focused helper methods.

- **Files**:
  - services/api/services/display_names.py - Refactor resolve_display_names_and_avatars method
  - tests/services/api/services/test_display_names.py - Add unit tests for extracted methods
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for Discord API fetching, caching, and fallback logic
  - All existing tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 20, 51) - Function identified in dual violations
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 109-111) - Display name resolution complexity cluster
- **Dependencies**:
  - Discord.py async patterns
  - Redis caching patterns

### Task 1.3: Refactor services/games.py `_update_game_fields` (C:13/Cog:16)

Extract field validation and conditional update logic into separate validation and update methods.

- **Files**:
  - services/api/services/games.py - Refactor _update_game_fields method
  - tests/services/api/services/test_games.py - Add unit tests for field validation helpers
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for each field type validation (datetime, player count, description, etc.)
  - All game update integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 22, 147) - Dual violation in GameService
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 99-103) - GameService complexity cluster
- **Dependencies**:
  - Task 1.5 may share extracted methods

### Task 1.4: Refactor services/games.py `_update_prefilled_participants` (C:11/Cog:17)

Extract participant validation, ordering, and role handling into focused helper methods.

- **Files**:
  - services/api/services/games.py - Refactor _update_prefilled_participants method
  - tests/services/api/services/test_games.py - Add unit tests for participant handling
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for participant validation, ordering logic, and role verification
  - All prefilled participant tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 23, 148) - Dual violation in GameService
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 99-103) - GameService systemic complexity
- **Dependencies**:
  - Participant ordering schema from previous work

### Task 1.5: Refactor services/games.py `update_game` (C:13/Cog:17)

Extract transaction management, notification triggering, and state validation into separate methods.

- **Files**:
  - services/api/services/games.py - Refactor update_game service method
  - tests/services/api/services/test_games.py - Add unit tests for transaction and notification helpers
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for state validation, notification logic, and transaction boundaries
  - All game update integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 24, 149) - Dual violation, appears twice in list
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 99-103) - GameService requires systemic refactoring
- **Dependencies**:
  - Tasks 1.3 and 1.4 should be completed first to avoid conflicts

### Task 1.6: Refactor services/participant_resolver.py `resolve_initial_participants` (C:12/Cog:20)

Extract participant type resolution (users, roles, prefilled) and validation into separate methods.

- **Files**:
  - services/api/services/participant_resolver.py - Refactor resolve_initial_participants method
  - tests/services/api/services/test_participant_resolver.py - Add unit tests for each resolution type
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for user participant resolution, role resolution, and prefilled participant handling
  - All participant resolution integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 25, 47, 150) - Dual violation with highest cognitive complexity in Phase 1
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 113-114) - Identified as high on both metrics
- **Dependencies**:
  - None, can be done independently

### Task 1.7: Refactor events/handlers.py `_handle_player_removed` (C:12/Cog:18)

Extract notification logic, promotion handling, and message update logic into focused methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _handle_player_removed method
  - tests/services/bot/events/test_handlers.py - Add unit tests for removal notification and promotion
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for player removal notifications, waitlist promotion, and message updates
  - All player removal integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 27, 151) - Dual violation in EventHandlers
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - EventHandlers complexity cluster
- **Dependencies**:
  - Discord.py async patterns for message updates

### Task 1.8: Refactor formatters/game_message.py `create_game_embed` (C:14/Cog:17)

Extract embed field creation (participants, waitlist, details) into separate builder methods.

- **Files**:
  - services/bot/formatters/game_message.py - Refactor create_game_embed method
  - tests/services/bot/formatters/test_game_message.py - Add unit tests for each embed section
- **Success**:
  - Cyclomatic complexity ≤10
  - Cognitive complexity ≤15
  - Unit tests for participant list formatting, waitlist display, game details, and footer
  - All message formatting tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 28, 152) - Highest cyclomatic complexity in Phase 1
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 118-127) - Builder pattern approach
- **Dependencies**:
  - Discord.py embed API patterns

### Task 1.9: Update pyproject.toml thresholds (17→12, 20→17)

Update linter thresholds after all Phase 1 refactoring complete.

- **Files**:
  - pyproject.toml - Update C901 max-complexity from 17 to 12, complexipy threshold from 20 to 17
- **Success**:
  - `uv run ruff check` passes with no C901 violations at threshold 12
  - `uv run pre-commit run complexipy --all-files` passes with no violations at threshold 17
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 5-12) - Current vs. target thresholds
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 146-149) - Phase 1 expected impact
- **Dependencies**:
  - All Phase 1 refactoring tasks (1.1-1.8) must be complete

## Phase 2: Remaining Cyclomatic Violations (2 functions)

Target the last two functions violating only cyclomatic threshold to reach C901=10 (default).

### Task 2.1: Refactor services/games.py `_resolve_game_host` (C:11/Cog:~10)

Extract host type validation (user vs. prefilled) into guard clauses and helper methods.

- **Files**:
  - services/api/services/games.py - Refactor _resolve_game_host method
  - tests/services/api/services/test_games.py - Add unit tests for host resolution logic
- **Success**:
  - Cyclomatic complexity ≤10
  - Unit tests for user host resolution, prefilled host validation, and error cases
  - All game creation tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 21, 154) - Cyclomatic-only violation
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 99-103) - Part of GameService cluster
- **Dependencies**:
  - Phase 1 GameService refactoring completed

### Task 2.2: Refactor events/handlers.py `_handle_game_reminder` (C:11/Cog:~11)

Extract message formatting and participant notification logic into separate methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _handle_game_reminder method
  - tests/services/bot/events/test_handlers.py - Add unit tests for reminder message formatting
- **Success**:
  - Cyclomatic complexity ≤10
  - Unit tests for reminder message creation, participant mentions, and scheduling
  - All reminder notification tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 26, 155) - Cyclomatic-only violation
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - EventHandlers cluster
- **Dependencies**:
  - Discord.py message formatting patterns

### Task 2.3: Update pyproject.toml cyclomatic threshold (12→10)

Update cyclomatic complexity threshold to default value after Phase 2 completion.

- **Files**:
  - pyproject.toml - Update C901 max-complexity from 12 to 10
- **Success**:
  - `uv run ruff check` passes with no C901 violations at default threshold 10
  - Zero cyclomatic complexity violations in entire codebase
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 10-11) - Target default threshold
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 157-159) - Phase 2 expected impact
- **Dependencies**:
  - Tasks 2.1 and 2.2 must be complete

## Phase 3: High Cognitive Complexity (8 functions, 20-27)

Target functions with cognitive complexity 20-27 to enable threshold reduction to 17.

### Task 3.1: Refactor services/display_names.py `resolve_display_names` (Cog:27)

Extract batch Discord API fetching and error handling into focused async helper methods.

- **Files**:
  - services/api/services/display_names.py - Refactor resolve_display_names method
  - tests/services/api/services/test_display_names.py - Add unit tests for batch fetching
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for batch API calls, error recovery, and partial success handling
  - All display name resolution tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 41, 163) - Highest cognitive complexity in Phase 3
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 109-111) - Display name resolution cluster
- **Dependencies**:
  - Task 1.2 completed (related method)

### Task 3.2: Refactor events/handlers.py `_handle_game_updated` (Cog:26)

Extract field change detection, notification logic, and message update into separate methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _handle_game_updated method
  - tests/services/bot/events/test_handlers.py - Add unit tests for update detection and notifications
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for change detection, participant notifications, and message synchronization
  - All game update event tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 43, 164) - Second highest in Phase 3
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - EventHandlers complexity cluster
- **Dependencies**:
  - Discord.py event handling patterns

### Task 3.3: Refactor events/handlers.py `_handle_game_cancelled` (Cog:24)

Extract participant notification, message deletion, and cleanup logic into separate methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _handle_game_cancelled method
  - tests/services/bot/events/test_handlers.py - Add unit tests for cancellation workflow
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for participant notifications, message cleanup, and error handling
  - All game cancellation tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 44, 165) - Cognitive complexity 24
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - Part of EventHandlers cluster
- **Dependencies**:
  - Message cleanup patterns from Phase 1

### Task 3.4: Refactor services/games.py `_resolve_template_fields` (Cog:23)

Extract template field merging, validation, and default application into helper methods.

- **Files**:
  - services/api/services/games.py - Refactor _resolve_template_fields method
  - tests/services/api/services/test_games.py - Add unit tests for template field resolution
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for field merging logic, template defaults, and override validation
  - All template-based game creation tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 45, 166) - Cognitive complexity 23
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 99-103) - GameService systemic complexity
- **Dependencies**:
  - Phase 1 GameService refactoring completed

### Task 3.5: Refactor events/handlers.py `_handle_join_notifications` (Cog:21)

Extract notification type determination and message formatting into separate methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _handle_join_notifications method
  - tests/services/bot/events/test_handlers.py - Add unit tests for join notification logic
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for promotion notifications, standard joins, and waitlist additions
  - All join notification tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 46, 167) - Cognitive complexity 21
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - EventHandlers cluster
- **Dependencies**:
  - Notification patterns from Phase 1

### Task 3.6: Refactor commands/list_games.py `list_games_command` (Cog:20)

Extract game filtering, sorting, and embed generation into separate methods.

- **Files**:
  - services/bot/commands/list_games.py - Refactor list_games_command function
  - tests/services/bot/commands/test_list_games.py - Add unit tests for filtering and formatting
- **Success**:
  - Cognitive complexity ≤17
  - Unit tests for date filtering, game sorting, and embed pagination
  - All list games command tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 49, 168) - Cognitive complexity 20
- **Dependencies**:
  - Discord.py command patterns

### Task 3.7: Verify Phase 1 functions if not yet at Cog≤17

Review Phase 1 refactored functions to ensure cognitive complexity is at or below 17.

- **Files**:
  - All Phase 1 refactored files - Verify complexity metrics
- **Success**:
  - All Phase 1 functions confirmed at cognitive complexity ≤17
  - Re-refactor any functions still above threshold
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 169-170) - Phase 3 may include Phase 1 functions
- **Dependencies**:
  - Phase 1 complete

### Task 3.8: Update pyproject.toml cognitive threshold (maintain at 17)

Verify cognitive complexity threshold at 17 after Phase 3 completion.

- **Files**:
  - pyproject.toml - Confirm complexipy threshold at 17
- **Success**:
  - `uv run pre-commit run complexipy --all-files` passes with no violations above 17
  - All Phase 3 functions at cognitive complexity ≤17
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 171-172) - Phase 3 expected impact
- **Dependencies**:
  - All Phase 3 refactoring tasks complete

## Phase 4: Medium Cognitive Complexity (6+ functions, 16-19)

Target remaining functions with cognitive complexity 16-19 to reach default threshold of 15.

### Task 4.1: Refactor services/roles.py `check_user_roles` (Cog:19)

Extract role fetching, permission validation, and error handling into separate methods.

- **Files**:
  - services/api/services/roles.py - Refactor check_user_roles method
  - tests/services/api/services/test_roles.py - Add unit tests for role verification
- **Success**:
  - Cognitive complexity ≤15
  - Unit tests for role fetching, permission checks, and error scenarios
  - All role verification tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 52, 176) - Cognitive complexity 19
- **Dependencies**:
  - Discord.py role API patterns

### Task 4.2: Refactor data_access/database_users.py `create_database_users` (Cog:19)

Extract user existence checking, role creation, and permission granting into helper methods.

- **Files**:
  - shared/data_access/database_users.py - Refactor create_database_users function
  - tests/shared/data_access/test_database_users.py - Add unit tests for user creation workflow
- **Success**:
  - Cognitive complexity ≤15
  - Unit tests for user existence checks, role setup, and permission grants
  - All database user initialization tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 50, 177) - Cognitive complexity 19
- **Dependencies**:
  - PostgreSQL role management patterns

### Task 4.3: Refactor events/handlers.py `_refresh_game_message` (Cog:18)

Extract message fetching, embed regeneration, and error recovery into separate methods.

- **Files**:
  - services/bot/events/handlers.py - Refactor _refresh_game_message method
  - tests/services/bot/events/test_handlers.py - Add unit tests for message refresh logic
- **Success**:
  - Cognitive complexity ≤15
  - Unit tests for message fetching, embed updates, and error handling
  - All message refresh tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 54, 178) - Cognitive complexity 18
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 105-107) - EventHandlers cluster
- **Dependencies**:
  - Phase 1 message formatting refactoring

### Task 4.4: Refactor services/guild_service.py `sync_user_guilds` (Cog:18)

Extract guild comparison, database synchronization, and cleanup logic into separate methods.

- **Files**:
  - services/api/services/guild_service.py - Refactor sync_user_guilds function
  - tests/services/api/services/test_guild_service.py - Add unit tests for guild sync workflow
- **Success**:
  - Cognitive complexity ≤15
  - Unit tests for guild comparison, additions, removals, and error cases
  - All guild synchronization tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 55, 179) - Cognitive complexity 18
- **Dependencies**:
  - Discord.py guild API patterns

### Task 4.5: Refactor remaining functions with Cog:16-17

Identify and refactor any remaining functions with cognitive complexity 16-17.

- **Files**:
  - Various files - Identify from research lines 53, 56-57
  - Corresponding test files - Add unit tests
- **Success**:
  - All identified functions reduced to cognitive complexity ≤15
  - Unit tests added for all extracted methods
  - All integration tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 53, 56-57, 180) - Functions with cognitive 16-17
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 22, 53) - routes/games.py _build_game_response (Cog:16)
- **Dependencies**:
  - Tasks 4.1-4.4 complete

### Task 4.6: Update pyproject.toml cognitive threshold (17→15)

Update cognitive complexity threshold to default value after Phase 4 completion.

- **Files**:
  - pyproject.toml - Update complexipy threshold from 17 to 15
- **Success**:
  - `uv run pre-commit run complexipy --all-files` passes with no violations at default threshold 15
  - Zero cognitive complexity violations in entire codebase
  - **PRIMARY GOAL ACHIEVED**: Both thresholds at default values (C901=10, complexipy=15)
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 12, 182-183) - Target default threshold
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 281-283) - Phase 4 success criteria
- **Dependencies**:
  - All Phase 4 refactoring tasks complete

## Phase 5: Extreme Outliers - Optional (3 utility functions)

Target test utilities and scripts with extreme cognitive complexity. This phase is optional as it involves non-production code.

### Task 5.1: Refactor retry_daemon.py `_process_dlq` (Cog:39)

Extract message parsing, retry logic, and error handling into separate methods.

- **Files**:
  - services/retry/retry_daemon.py - Refactor _process_dlq method
  - tests/services/retry/test_retry_daemon.py - Add unit tests for DLQ processing
- **Success**:
  - Cognitive complexity significantly reduced (target ≤20 for daemon code)
  - Unit tests for message parsing, retry attempts, and dead-letter handling
  - All retry daemon tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 38, 187) - Highest cognitive complexity (39)
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 191-192) - Lower priority for utility code
- **Dependencies**:
  - RabbitMQ message handling patterns

### Task 5.2: Refactor tests/e2e/shared/discord.py `seed_messages` (Cog:37)

Extract test setup stages, message creation, and validation into helper methods.

- **Files**:
  - tests/e2e/shared/discord.py - Refactor seed_messages method
  - No unit tests needed (this is test utility code)
- **Success**:
  - Cognitive complexity significantly reduced (target ≤20 for test utilities)
  - E2E test setup remains functional
  - All E2E tests passing
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 39, 188) - Second highest complexity (37)
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 191-192) - Test code lower priority
- **Dependencies**:
  - E2E test infrastructure

### Task 5.3: Refactor scripts/verify_button_states.py `verify_game_buttons` (Cog:30)

Extract button state checking, validation logic, and reporting into focused functions.

- **Files**:
  - scripts/verify_button_states.py - Refactor verify_game_buttons function
  - No unit tests needed (this is a one-off script)
- **Success**:
  - Cognitive complexity reduced to ≤20
  - Script functionality preserved
  - Script execution validates button states correctly
- **Research References**:
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 40, 189) - Cognitive complexity 30
  - #file:../research/20260116-default-complexity-thresholds-reduction-research.md (Lines 191-192) - Script code lowest priority
- **Dependencies**:
  - None, standalone script

## Dependencies

- Existing comprehensive test suite with integration and E2E tests
- Ruff linter with C901 (McCabe cyclomatic complexity) rule configured
- Complexipy cognitive complexity tool via pre-commit hooks
- SQLAlchemy async patterns for database operations
- Discord.py async patterns for bot event handling
- Python 3.11+ with type hints and dataclasses
- UV for Python dependency management and test execution

## Success Criteria

**Phase 1 Complete**:
- 8 dual-violation functions refactored to C≤12, Cog≤17
- Thresholds updated: C901:17→12, complexipy:20→17
- All integration tests passing
- Unit tests added for all extracted methods

**Phase 2 Complete**:
- 2 cyclomatic-only violations resolved
- Cyclomatic threshold at default: C901=10
- All tests passing

**Phase 3 Complete**:
- 8 high cognitive complexity functions reduced to ≤17
- Cognitive threshold maintained at 17
- All tests passing

**Phase 4 Complete (PRIMARY GOAL)**:
- All cognitive complexity violations resolved
- Both thresholds at default values: C901=10, complexipy=15
- Zero complexity violations across entire production codebase
- All tests passing with 100% coverage maintained

**Phase 5 Complete (Optional)**:
- Test utilities and scripts refactored
- Potential for further threshold tightening if desired

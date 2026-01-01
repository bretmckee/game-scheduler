<!-- markdownlint-disable-file -->

# Task Details: Centralized Query Layer for Deduplication and Security

## Research Reference

**Source Research**: #file:../research/20260101-centralized-query-layer-deduplication-security-research.md

## Phase 1: Foundation - Create Guild Query Wrapper Functions

### Task 1.1: Create `shared/data_access/` directory structure

Create the foundational directory structure and __init__.py files for the new centralized query layer.

- **Files**:
  - `shared/data_access/__init__.py` - Package initialization, exports guild_queries
  - `shared/data_access/guild_queries.py` - Core async wrapper functions (to be populated in subsequent tasks)
- **Success**:
  - Directory structure exists
  - __init__.py imports work correctly
  - No functional changes yet (empty wrapper file)
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 142-265) - Architecture and wrapper function examples
- **Dependencies**: None
- **Testing**: Import test to verify module structure

### Task 1.2: Implement core game operation wrappers (5 functions)

Create wrapper functions for game CRUD operations with required guild_id parameters and RLS context setting.

- **Files**:
  - `shared/data_access/guild_queries.py` - Add: get_game_by_id, list_games, create_game, update_game, delete_game
- **Success**:
  - All 5 functions implemented with required guild_id parameter
  - Each function sets RLS context: `SET LOCAL app.current_guild_id = :guild_id`
  - Each function explicitly filters by guild_id in WHERE clause
  - Proper type hints and docstrings
  - Error handling for not found cases
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 154-202) - Game operation wrapper examples with RLS context
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 48-58) - Duplication audit showing 8+ game query locations
- **Dependencies**: Task 1.1 completion
- **Testing**: Unit tests with mocked database session, verify guild_id filtering, test error cases

### Task 1.3: Implement participant operation wrappers (3 functions)

Create wrapper functions for participant operations that validate game ownership before performing participant actions.

- **Files**:
  - `shared/data_access/guild_queries.py` - Add: add_participant, remove_participant, list_user_games
- **Success**:
  - All 3 functions implemented with required guild_id parameter
  - Functions use get_game_by_id to validate guild ownership before participant operations
  - list_user_games properly joins GameSession and GameParticipant with guild filtering
  - Proper error handling for invalid game_id
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 204-234) - Participant operation wrapper examples
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 59-61) - Security audit showing participant query patterns
- **Dependencies**: Task 1.2 completion (uses get_game_by_id)
- **Testing**: Unit tests verifying game ownership validation, participant CRUD operations, user game listing with guild filter

### Task 1.4: Implement template operation wrappers (4 functions)

Create wrapper functions for game template operations with guild_id enforcement.

- **Files**:
  - `shared/data_access/guild_queries.py` - Add: get_template_by_id, list_templates, create_template, update_template
- **Success**:
  - All 4 functions implemented with required guild_id parameter
  - Each function sets RLS context and filters by guild_id
  - Consolidates 15+ inline template queries identified in duplication audit
  - Proper error handling for template not found
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 236-265) - Template operation wrapper examples
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 44-47) - Duplication audit showing 15+ template query locations
- **Dependencies**: Task 1.1 completion
- **Testing**: Unit tests for template CRUD operations, verify guild filtering on list_templates

### Task 1.5: Add comprehensive unit tests for all wrapper functions

Create comprehensive test suite covering all wrapper functions with focus on guild isolation enforcement.

- **Files**:
  - `tests/shared/data_access/test_guild_queries.py` - Complete test suite for all wrapper functions
- **Success**:
  - 100% code coverage on guild_queries.py
  - Tests verify guild_id is required (TypeError if missing)
  - Tests verify RLS context is set correctly
  - Tests verify guild_id filtering in queries
  - Tests cover error cases (not found, invalid guild_id, etc.)
  - Tests use mocked AsyncSession to avoid database dependencies
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 267-291) - Benefits section emphasizing testing improvements
  - #file:../../.github/instructions/coding-best-practices.instructions.md (Lines 123-146) - Testing standards requiring unit tests alongside code
- **Dependencies**: Tasks 1.2, 1.3, 1.4 completion
- **Testing**: Run pytest with coverage report, verify 100% coverage

### Task 1.6: Add integration tests for guild query wrappers

Create integration tests that exercise all 12 wrapper functions against a real PostgreSQL database before migrating production code to use them.

- **Files**:
  - `tests/integration/test_guild_queries.py` - New integration test suite covering all wrapper functions
  - Uses existing integration test infrastructure (conftest.py, scripts/run-integration-tests.sh)
- **Test Coverage**:
  - **Game Operations** (5 functions):
    - `get_game_by_id`: Verify returns game from correct guild only, None for wrong guild
    - `list_games`: Verify returns only specified guild's games, respects channel filter
    - `create_game`: Verify guild_id correctly set, RLS context applied
    - `update_game`: Verify rejects updates to other guild's games, validates ownership
    - `delete_game`: Verify rejects deletes of other guild's games, validates ownership
  - **Participant Operations** (3 functions):
    - `add_participant`: Verify validates game belongs to guild before adding
    - `remove_participant`: Verify validates game belongs to guild before removing
    - `list_user_games`: Verify returns only user's games from specified guild
  - **Template Operations** (4 functions):
    - `get_template_by_id`: Verify returns template from correct guild only
    - `list_templates`: Verify returns only specified guild's templates
    - `create_template`: Verify guild_id correctly set, RLS context applied
    - `update_template`: Verify rejects updates to other guild's templates
- **Test Data Setup**:
  - Create two guilds (guild_a, guild_b) with distinct UUIDs
  - Create games, participants, templates in both guilds
  - Use realistic game data (titles, descriptions, dates, player counts)
  - Clean up test data after each test
- **Security Validations**:
  - Cross-guild access attempts return None or raise ValueError
  - List operations never return cross-guild data
  - RLS context (`SET LOCAL app.current_guild_id`) correctly set before each query
  - Validate filtering by guild_id in WHERE clauses is effective
- **Error Handling Tests**:
  - Empty string guild_id raises ValueError
  - Empty string game_id/template_id raises ValueError
  - Non-existent IDs return None or raise appropriate errors
  - Database constraint violations handled gracefully
- **Performance Validation**:
  - Measure wrapper overhead per query (target: < 5ms)
  - Verify RLS context setting doesn't significantly impact query performance
  - Confirm no N+1 query issues in list operations
- **Success Criteria**:
  - All 12 wrapper functions tested against real database
  - 100% of security validations pass (zero cross-guild data leakage)
  - All error cases handled correctly
  - Performance acceptable for production use
  - Tests run successfully via `scripts/run-integration-tests.sh`
  - Provides confidence to proceed with migration of 37+ call sites
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 711-732) - Integration test rationale and threat model
  - #file:../../tests/integration/test_database_infrastructure.py (Lines 1-100) - Existing integration test pattern to follow
  - #file:../../.github/instructions/integration-tests.instructions.md - Integration test execution requirements
- **Dependencies**: Tasks 1.1-1.4 completion (all wrapper functions implemented)
- **Testing**: Execute via `scripts/run-integration-tests.sh`, verify all tests pass, review coverage report

## Phase 2: API Migration - High Priority Routes

### Task 2.1a: Create integration tests for games route (pre-migration baseline)

Create integration tests for games API endpoints that verify current behavior before migration.

- **Files**:
  - `tests/integration/test_games_route_guild_isolation.py` - New integration test suite for games endpoints
- **Test Coverage**:
  - Test all game CRUD operations through API endpoints
  - Verify cross-guild game access returns 404/403
  - Verify list_games only returns games from correct guild
  - Verify create_game sets correct guild_id
  - Verify update_game validates guild ownership
  - Verify delete_game validates guild ownership
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation (direct database queries)
  - Tests establish behavioral baseline for migration
  - Tests document expected guild isolation behavior
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 627-660) - Integration test requirements
  - #file:../../tests/integration/test_guild_queries.py - Integration test pattern to follow
- **Dependencies**: Phase 1 completion (wrapper functions available for comparison)
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 2.1b

### Task 2.1b: Migrate games route to use guild_queries wrappers

Replace inline database queries in games route with centralized guild_queries wrapper functions.

- **Files**:
  - `services/api/routes/games.py` - Replace 8+ inline queries with guild_queries calls
  - Update imports to use `from shared.data_access import guild_queries`
  - Remove direct imports of GameSession model (if any)
- **Success**:
  - All game retrieval uses guild_queries.get_game_by_id
  - Game listing uses guild_queries.list_games
  - Game creation uses guild_queries.create_game
  - Game updates use guild_queries.update_game
  - Game deletion uses guild_queries.delete_game
  - All integration tests from Task 2.1a still pass
  - No direct GameSession queries remain in file
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 293-309) - Before/after migration examples
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 311-322) - Migration targets with priority order
- **Dependencies**: Task 2.1a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 2.1a - all must still pass, verify guild_queries functions are called

### Task 2.2a: Create integration tests for templates route (pre-migration baseline)

Create integration tests for templates API endpoints that verify current behavior before migration.

- **Files**:
  - `tests/integration/test_templates_route_guild_isolation.py` - New integration test suite for templates endpoints
- **Test Coverage**:
  - Test all template CRUD operations through API endpoints
  - Verify cross-guild template access returns 404/403
  - Verify list_templates only returns templates from correct guild
  - Verify create_template sets correct guild_id
  - Verify update_template validates guild ownership
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation
  - Tests establish behavioral baseline for migration
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 627-660) - Integration test requirements
- **Dependencies**: Task 2.1b completion
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 2.2b

### Task 2.2b: Migrate templates route to use guild_queries wrappers

Replace inline template queries with centralized wrapper functions.

- **Files**:
  - `services/api/routes/templates.py` - Replace 6+ inline template queries with guild_queries calls
  - Update imports to remove direct GameTemplate model access
- **Success**:
  - Template retrieval uses guild_queries.get_template_by_id
  - Template listing uses guild_queries.list_templates
  - Template creation uses guild_queries.create_template
  - Template updates use guild_queries.update_template
  - All integration tests from Task 2.2a still pass
  - Consolidates 15+ inline queries.get_guild_by_id() + template patterns
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 236-265) - Template wrapper function examples
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 44-47) - Duplication audit findings for templates
- **Dependencies**: Task 2.2a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 2.2a - all must still pass

### Task 2.3a: Create integration tests for guilds route (pre-migration baseline)

Create integration tests for guilds API endpoints that verify current behavior before migration.

- **Files**:
  - `tests/integration/test_guilds_route_guild_isolation.py` - New integration test suite for guilds endpoints
- **Test Coverage**:
  - Test guild configuration retrieval through API endpoints
  - Verify cross-guild configuration access returns 404/403
  - Verify list operations only return data from correct guild
  - Test guild configuration updates validate guild ownership
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation
  - Tests establish behavioral baseline for migration
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 627-660) - Integration test requirements
- **Dependencies**: Task 2.2b completion
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 2.3b

### Task 2.3b: Migrate guilds route to use guild_queries wrappers

Replace guild and configuration queries with centralized wrappers.

- **Files**:
  - `services/api/routes/guilds.py` - Replace 6+ guild/config queries with guild_queries calls
  - May require adding guild configuration wrappers to guild_queries.py if not present
- **Success**:
  - All guild data retrieval uses centralized functions
  - Guild configuration queries consolidated
  - All integration tests from Task 2.3a still pass
  - No direct database model imports
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 311-322) - Migration priority targets
- **Dependencies**: Task 2.3a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 2.3a - all must still pass

### Task 2.4a: Create integration tests for channels route (pre-migration baseline)

Create integration tests for channels API endpoints that verify current behavior before migration.

- **Files**:
  - `tests/integration/test_channels_route_guild_isolation.py` - New integration test suite for channels endpoints
- **Test Coverage**:
  - Test all channel operations through API endpoints
  - Verify cross-guild channel access returns 404/403
  - Verify list operations only return channels from correct guild
  - Test channel configuration updates validate guild ownership
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation
  - Tests establish behavioral baseline for migration
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 627-660) - Integration test requirements
- **Dependencies**: Task 2.3b completion
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 2.4b

### Task 2.4b: Migrate channels route to use guild_queries wrappers

Replace channel queries with centralized wrappers.

- **Files**:
  - `services/api/routes/channels.py` - Replace 5+ channel queries with guild_queries calls
  - May require adding channel wrappers to guild_queries.py
- **Success**:
  - Channel queries consolidated
  - All integration tests from Task 2.4a still pass
  - Guild filtering enforced for all channel operations
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 40-42) - Duplication audit showing channel query patterns
- **Dependencies**: Task 2.4a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 2.4a - all must still pass

### Task 2.5a: Create integration tests for permissions dependencies (pre-migration baseline)

Create integration tests for permission checks that verify current behavior before migration.

- **Files**:
  - `tests/integration/test_permissions_guild_isolation.py` - New integration test suite for permission checks
- **Test Coverage**:
  - Test permission checks enforce guild boundaries
  - Verify users cannot access other guilds' resources
  - Test permission checks for games, templates, channels
  - Measure performance of permission checks (baseline for comparison)
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation
  - Tests establish behavioral baseline for migration
  - Performance baseline established for permission checks
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 627-660) - Integration test requirements
- **Dependencies**: Task 2.4b completion
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 2.5b

### Task 2.5b: Migrate permissions dependencies to use guild_queries wrappers

Replace permission check queries with centralized wrappers.

- **Files**:
  - `services/api/dependencies/permissions.py` - Replace 10+ permission check queries with guild_queries calls
- **Success**:
  - All permission checks use centralized query layer
  - All integration tests from Task 2.5a still pass
  - Guild isolation enforced in permission validation
  - No performance regression (verified against Task 2.5a baseline)
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 36-43) - Duplication audit showing permission query locations
- **Dependencies**: Task 2.5a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 2.5a - all must still pass, verify no performance degradation

## Phase 3: Bot and Scheduler Migration (Test-First Approach)

### Task 3.1a: Create integration tests for bot handlers (pre-migration baseline)

Create integration tests for bot handlers that verify current database query behavior before migration.

- **Files**:
  - `tests/integration/test_bot_handlers_guild_isolation.py` - New integration test suite for bot handlers
- **Test Coverage**:
  - Test bot commands that query games, templates, participants
  - Mock Discord interaction context with different guild_ids
  - Verify bot in Guild A only accesses Guild A data
  - Verify bot commands handle guild_id extraction from interaction.guild_id
  - Test cross-guild access attempts fail gracefully
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation (direct database queries)
  - Tests establish behavioral baseline for bot handlers
  - Tests document expected guild isolation in bot context
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 661-680) - Bot testing requirements
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 324-339) - Bot migration patterns
- **Dependencies**: Phase 2 completion (API routes migrated and tested)
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 3.1b

### Task 3.1b: Migrate bot handlers to use guild_queries (async)

Replace implicit Discord guild context queries with explicit guild_queries calls.

- **Files**:
  - `services/bot/` - All bot handler files that query database
  - Common pattern: Extract guild_id from `interaction.guild_id` and pass to guild_queries
- **Success**:
  - All bot database queries use guild_queries functions
  - Guild context explicitly passed (better than implicit Discord context)
  - All integration tests from Task 3.1a still pass
  - No direct model imports in bot handlers
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 324-339) - Bot migration examples showing explicit guild_id
- **Dependencies**: Task 3.1a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 3.1a - all must still pass

### Task 3.2a: Create unit tests for synchronous wrapper variants (TDD)

Create unit tests for synchronous guild_queries wrappers before implementation.

- **Files**:
  - `tests/shared/data_access/test_guild_queries_sync.py` - Unit test suite for sync wrappers
- **Test Coverage**:
  - Test sync versions of game operations (get, list, create, update, delete)
  - Test sync versions of notification and status query operations
  - Verify guild_id is required parameter
  - Verify RLS context is set correctly (`SET LOCAL app.current_guild_id`)
  - Verify guild_id filtering in WHERE clauses
  - Test error handling (not found, invalid guild_id)
  - Use mocked sync Session to avoid database dependencies
- **Success**:
  - Complete test suite written (tests will fail initially - TDD approach)
  - Tests define expected behavior for sync wrappers
  - Tests mirror async wrapper test patterns from Task 1.5
  - Ready to guide implementation in Task 3.2b
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 341-358) - Sync wrapper specifications
  - #file:../../tests/shared/data_access/test_guild_queries.py - Async test pattern to mirror
- **Dependencies**: Task 3.1b completion
- **Testing**: Tests written but will fail until Task 3.2b implements sync wrappers

### Task 3.2b: Create synchronous wrapper variants for scheduler

Implement synchronous versions of guild_queries for scheduler's sync Session usage.

- **Files**:
  - `shared/data_access/guild_queries_sync.py` - Synchronous versions of key wrapper functions
  - Focus on functions used by scheduler: game status queries, notification queries
- **Success**:
  - Sync versions of needed functions implemented
  - All unit tests from Task 3.2a pass
  - Same security guarantees as async versions (required guild_id, RLS context)
  - Clear naming distinction between async and sync functions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 341-358) - Sync wrapper example for scheduler
- **Dependencies**: Task 3.2a completion (tests written)
- **Testing**: Run unit tests from Task 3.2a - all must pass

### Task 3.3a: Enhance scheduler integration tests for guild isolation (pre-migration baseline)

Enhance existing scheduler integration tests to verify guild isolation before migration.

- **Files**:
  - `tests/integration/test_notification_daemon.py` - Add multi-guild isolation tests
  - `tests/integration/test_status_transitions.py` - Add multi-guild isolation tests
- **Test Coverage**:
  - Test notification daemon processes events from multiple guilds in isolation
  - Test status transition daemon processes games from multiple guilds separately
  - Verify Guild A notifications don't affect Guild B
  - Verify Guild A status transitions don't affect Guild B
  - Test simultaneous pending events from multiple guilds
  - Measure daemon processing performance (baseline for comparison)
  - Test with real database using multiple guilds
- **Success**:
  - All tests pass with current implementation (direct database queries)
  - Tests establish behavioral baseline for scheduler daemons
  - Multi-guild scenarios documented and tested
  - Tests can be re-run after migration to verify no regressions
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 681-700) - Scheduler testing requirements
  - Existing tests: #file:../../tests/integration/test_notification_daemon.py, #file:../../tests/integration/test_status_transitions.py
- **Dependencies**: Task 3.2b completion (sync wrappers available)
- **Testing**: Run via `scripts/run-integration-tests.sh`, all tests must pass before proceeding to 3.3b

### Task 3.3b: Migrate scheduler daemons to use guild_queries_sync

Replace scheduler daemon queries with synchronous wrapper functions.

- **Files**:
  - `services/scheduler/` - All daemon files that query database
  - `services/scheduler/notification_daemon.py` - Notification scheduling queries
  - `services/scheduler/status_transition_daemon.py` - Status transition queries
- **Success**:
  - All scheduler queries use guild_queries_sync functions
  - All integration tests from Task 3.3a still pass
  - Same consolidation and security benefits as async code
  - No performance regression (verified against Task 3.3a baseline)
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 341-358) - Scheduler migration approach
- **Dependencies**: Task 3.3a completion (baseline tests passing)
- **Testing**: Run integration tests from Task 3.3a - all must still pass, verify no performance degradation

## Phase 4: Verification and Database Security

### Task 4.1: Verify 100% migration completion

Audit entire codebase to ensure no direct model queries remain outside allowed locations.

- **Files**:
  - Search all Python files in `services/` and `tests/` for direct model imports
  - Verify imports of GameSession, GameTemplate, GameParticipant, NotificationSchedule only in allowed locations
- **Success**:
  - No imports of protected models outside: guild_queries.py, guild_queries_sync.py, shared/models/, alembic/
  - All 37+ original query locations migrated
  - All tests still pass
  - Manual audit confirms no queries bypassing wrapper layer
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 360-373) - Verification checklist
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 375-379) - Why import check is strongest enforcement
- **Dependencies**: Phases 1-3 completion
- **Testing**: Run full test suite (unit + integration + e2e), automated import search

### Task 4.2: Create and apply RLS migration

Create Alembic migration to enable Row Level Security policies on all tables.

- **Files**:
  - `alembic/versions/XXXXXX_enable_rls_guild_isolation.py` - New migration file
  - Enable RLS on: game_sessions, game_templates, game_participants, notification_schedule
  - Create policies filtering by app.current_guild_id
- **Success**:
  - RLS enabled on all guild-scoped tables
  - Policies enforce guild_id filtering at database level
  - Migration runs successfully up and down
  - No queries break (wrappers already set RLS context correctly)
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 381-418) - RLS SQL examples
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 420-429) - Why this is low risk after wrapper migration
- **Dependencies**: Task 4.1 completion (verify wrappers work before adding RLS)
- **Testing**: Apply migration, run full test suite, verify no RLS violations

### Task 4.3: Add integration tests for RLS enforcement

Create integration tests that verify RLS policies block cross-guild access attempts.

- **Files**:
  - `tests/integration/test_rls_enforcement.py` - New test file
  - Tests attempt cross-guild queries with wrong RLS context
  - Tests verify RLS blocks access even if query doesn't filter by guild_id
- **Success**:
  - Tests verify RLS context set correctly by wrappers
  - Tests confirm cross-guild queries are blocked by database
  - Tests document expected RLS behavior
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 431-437) - RLS benefits including audit trail
- **Dependencies**: Task 4.2 completion
- **Testing**: Run new RLS integration tests, verify they detect violations

### Task 4.4: Create end-to-end guild isolation validation tests

Create comprehensive e2e tests verifying guild isolation across all components in realistic workflows.

- **Files**:
  - `tests/e2e/test_guild_isolation_e2e.py` - New e2e test suite
  - Tests complete workflows spanning API, bot, and scheduler
- **Success**:
  - **Scenario 1**: Game created via API (Guild A) → Bot sees it in Guild A only, not in Guild B
  - **Scenario 2**: Notification scheduled (Guild A) → Daemon processes for Guild A only, Guild B unaffected
  - **Scenario 3**: User joins game (Guild A) → Participant changes not visible in Guild B
  - **Scenario 4**: Multiple guilds operating simultaneously → No cross-contamination detected
  - **Scenario 5**: Scheduler processes events for both guilds → Correct isolation maintained
  - All workflows function correctly with guild isolation enforced
  - Performance acceptable for multi-guild deployments
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 701-735) - E2E testing requirements for complete validation
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 736-755) - Why e2e tests are critical for security features
- **Dependencies**: Tasks 2.6, 3.4, 3.5, 4.3 completion (all components tested individually)
- **Testing**: Run e2e tests in environment matching production, verify complete workflows, measure end-to-end performance

## Phase 5: Architectural Enforcement

### Task 5.1: Create linting script to prevent model imports

Create static analysis script that prevents direct model imports outside allowed locations.

- **Files**:
  - `scripts/lint_guild_queries.py` - AST-based import checker
  - Checks for imports of: GameSession, GameTemplate, GameParticipant, NotificationSchedule, GameStatusSchedule
  - Allows imports only in: shared/data_access/, shared/models/, alembic/
- **Success**:
  - Script correctly identifies violations
  - Script exits with error code on violations
  - Clear error messages show file:line and explain fix (use guild_queries instead)
  - Script runs fast enough for pre-commit hook
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 439-479) - Complete linting script example with dual benefit explanation
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 498-503) - Dual benefits of linting
- **Dependencies**: Task 4.1 completion (start from clean state)
- **Testing**: Test script on known violations, verify detection; test on clean code, verify no false positives

### Task 5.2: Add pre-commit hook for query layer enforcement

Integrate linting script into pre-commit framework to prevent regressions.

- **Files**:
  - `.pre-commit-config.yaml` - Add enforce-query-layer hook
  - Configure to run on Python files in services/ and tests/
- **Success**:
  - Pre-commit hook runs on relevant files
  - Commits blocked if violations detected
  - Hook runs efficiently (doesn't slow down commits significantly)
  - Documentation updated to explain hook purpose
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 481-491) - Pre-commit configuration example
- **Dependencies**: Task 5.1 completion
- **Testing**: Test pre-commit hook locally, attempt commit with violation (should fail), attempt commit without violation (should succeed)

### Task 5.3: Update documentation with architecture guidelines

Document the centralized query layer architecture for future developers.

- **Files**:
  - `docs/CENTRALIZED_QUERY_LAYER.md` - New architecture documentation
  - Explain wrapper functions, guild isolation enforcement, RLS safety net
  - Include examples of correct and incorrect patterns
  - Document allowed vs disallowed import locations
  - Update main README.md to reference new architecture doc
- **Success**:
  - Clear explanation of architecture and rationale
  - Examples help developers understand proper usage
  - Documentation explains both deduplication and security benefits
  - Onboarding documentation updated
- **Research References**:
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 505-531) - Success metrics showing dual benefits
  - #file:../research/20260101-centralized-query-layer-deduplication-security-research.md (Lines 533-556) - Comparison showing efficiency of combined approach
- **Dependencies**: All other tasks complete
- **Testing**: Review documentation with fresh eyes, verify examples are accurate

## Dependencies

- SQLAlchemy 2.x with async support (already in project)
- PostgreSQL 12+ (already in project)
- pytest and pytest-asyncio (already in project)
- pre-commit framework (need to verify if already configured)

## Success Criteria

- All wrapper functions implemented with 100% unit test coverage
- All 37+ original query locations migrated to use wrappers
- Integration tests verify guild isolation in API routes, bot handlers, and scheduler daemons
- End-to-end tests validate complete workflows maintain guild isolation
- All tests pass (unit, integration, e2e) with no cross-guild data leakage
- RLS enabled and enforced at database level with integration test validation
- Linting prevents future violations
- Documentation complete and accurate
- Zero optional guild_id parameters remain
- Maintenance burden reduced from 37 to 10-12 locations
- Performance acceptable (wrapper overhead < 5ms, multi-guild e2e workflows functional)

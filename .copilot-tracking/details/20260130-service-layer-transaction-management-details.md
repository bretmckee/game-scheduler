<!-- markdownlint-disable-file -->

# Task Details: Service Layer Transaction Management and Atomicity

## Research Reference

**Source Research**: #file:../research/20260130-service-layer-transaction-management-research.md

## Phase 1: Guild and Channel Service Refactoring

### Task 1.1: Remove commits from guild_service.py

Remove premature commit calls from guild configuration operations to restore transaction atomicity.

- **Files**:
  - [services/api/services/guild_service.py](../../services/api/services/guild_service.py) - Remove commits at lines 54 and 78
- **Success**:
  - `create_guild_config()` uses flush instead of commit
  - `update_guild_config()` removes commit call
  - Functions add docstring note: "Does not commit. Caller must commit transaction."
  - `sync_user_guilds()` orchestrator remains atomic
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 9-17) - Guild service analysis
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 79-100) - Architectural pattern violation examples
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 170-192) - Recommended refactoring approach
- **Dependencies**:
  - None - standalone refactoring

### Task 1.2: Remove commits from channel_service.py

Remove premature commit calls from channel configuration operations.

- **Files**:
  - [services/api/services/channel_service.py](../../services/api/services/channel_service.py) - Remove commits at lines 52 and 77
- **Success**:
  - `create_channel_config()` uses flush instead of commit
  - `update_channel_config()` removes commit call
  - Functions add docstring note about transaction expectations
  - Channel creation remains functional within guild sync orchestration
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 19-23) - Channel service analysis
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 102-110) - Multi-step atomicity requirements
- **Dependencies**:
  - Task 1.1 completion recommended for testing consistency

### Task 1.3: Update guild and channel service tests

Update unit tests to verify correct transaction behavior.

- **Files**:
  - [tests/services/test_guild_service.py](../../tests/services/test_guild_service.py) - Update commit assertions
  - [tests/services/test_channel_service.py](../../tests/services/test_channel_service.py) - Update commit assertions
- **Success**:
  - Remove `mock_db.commit.assert_awaited_once()` assertions
  - Add `mock_db.commit.assert_not_awaited()` where appropriate
  - Tests verify flush is called for ID generation
  - All existing functionality tests still pass
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 145-157) - Test suite implications
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 204-212) - Test update guidance
- **Dependencies**:
  - Tasks 1.1 and 1.2 completion

## Phase 2: Template Service Refactoring

### Task 2.1: Remove commits from template_service.py

Remove all 6 commit calls from template CRUD operations.

- **Files**:
  - [services/api/services/template_service.py](../../services/api/services/template_service.py) - Remove all `await self.db.commit()` calls
- **Success**:
  - All template operations (create, update, delete, reorder, set_default) use flush where needed
  - No commit calls remain in service class
  - Template ordering operations remain atomic
  - Docstrings updated for transaction expectations
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 25-29) - Template service analysis
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 118-125) - Template operation atomicity requirements
- **Dependencies**:
  - None - independent service refactoring

### Task 2.2: Update template service tests

Update template service test assertions for correct transaction behavior.

- **Files**:
  - [tests/services/test_template_service.py](../../tests/services/test_template_service.py) - Update all commit assertions
- **Success**:
  - All 6 test functions updated to not expect commits
  - Tests verify service operations complete successfully
  - Mock commit assertions removed or inverted
  - Template ordering tests validate state changes without commits
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 145-157) - Test verification of incorrect behavior
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Game Service Refactoring

### Task 3.1: Remove commits from games.py service

Remove all 6 commit calls from game and participant operations while preserving flush usage.

- **Files**:
  - [services/api/services/games.py](../../services/api/services/games.py) - Remove commits at lines 633, 1373, 1445, 1533, 1547, 1620
- **Success**:
  - `create_game()` removes commit at line 633
  - `update_game()` removes commit at line 1373
  - `add_participant()` removes commit at line 1445
  - `remove_participant()` removes commits at lines 1533, 1547, 1620
  - Game creation with participants remains atomic
  - Participant promotions remain atomic with notifications
  - Docstrings updated for transaction expectations
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 31-38) - Game service analysis
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 127-133) - Game operation atomicity requirements
- **Dependencies**:
  - None - independent service refactoring

### Task 3.2: Verify flush usage remains appropriate

Audit all 6 flush calls in games.py to ensure they serve ID generation purposes.

- **Files**:
  - [services/api/services/games.py](../../services/api/services/games.py) - Verify flushes at lines 188, 288, 607, 888, 989, 1054
- **Success**:
  - Each flush call has clear purpose documented (ID generation for FK relationships)
  - No unnecessary flush calls remain
  - Flush operations don't interfere with transaction boundaries
  - Foreign key relationships work correctly with flush-then-reference pattern
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 135-143) - Flush vs commit explanation
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 194-202) - Flush usage best practices
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Update game service tests

Update extensive game service test suite to validate correct transaction behavior.

- **Files**:
  - [tests/services/test_games.py](../../tests/services/test_games.py) - Update all commit assertions
  - [tests/services/test_participant_operations.py](../../tests/services/test_participant_operations.py) - Update commit assertions if exists
- **Success**:
  - All game operation tests updated to not expect commits
  - Participant operation tests verify atomicity without checking commits
  - Promotion logic tests validate state changes correctly
  - All existing functionality tests pass
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 145-157) - Test suite implications
- **Dependencies**:
  - Tasks 3.1 and 3.2 completion

## Phase 4: Route Handler Verification

### Task 4.1: Audit all mutation endpoints for proper dependency usage

Verify all routes that modify data use FastAPI dependency injection correctly.

- **Files**:
  - [services/api/routes/guilds.py](../../services/api/routes/guilds.py) - Verify dependency usage
  - [services/api/routes/channels.py](../../services/api/routes/channels.py) - Verify dependency usage
  - [services/api/routes/templates.py](../../services/api/routes/templates.py) - Verify dependency usage
  - [services/api/routes/games.py](../../services/api/routes/games.py) - Verify dependency usage
- **Success**:
  - All POST/PUT/PATCH/DELETE endpoints use `Depends(get_db)` or `Depends(get_db_with_user_guilds())`
  - No manual commit or rollback calls in route handlers
  - Error handling preserves transaction boundaries
  - Transaction lifecycle managed by dependency
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 40-48) - Database dependency analysis
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 214-221) - Route handler verification guidance
- **Dependencies**:
  - Phases 1-3 completion for accurate testing

### Task 4.2: Verify transaction boundaries in orchestrator functions

Ensure complex multi-step operations maintain atomicity after service refactoring.

- **Files**:
  - [services/api/services/guild_service.py](../../services/api/services/guild_service.py) - Test `sync_user_guilds()` atomicity
  - [services/api/services/games.py](../../services/api/services/games.py) - Test game creation with participants
- **Success**:
  - `sync_user_guilds()` creates guild+channels+template atomically or rolls back
  - Game creation with participants is atomic
  - Participant removal with promotion is atomic
  - Error in any step rolls back entire operation
  - No orphaned records from partial failures
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 50-60) - Incident analysis showing partial failure
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 112-116) - Data integrity risks
- **Dependencies**:
  - Phases 1-3 completion

## Phase 5: Integration Testing

### Task 5.1: Create atomicity test suite

Build integration tests that verify multi-step operations are atomic.

- **Files**:
  - [tests/integration/test_guild_sync_atomicity.py](../../tests/integration/test_guild_sync_atomicity.py) - New file for guild sync tests
  - [tests/integration/test_game_creation_atomicity.py](../../tests/integration/test_game_creation_atomicity.py) - New file for game tests
  - [tests/integration/test_participant_atomicity.py](../../tests/integration/test_participant_atomicity.py) - New file for participant tests
- **Success**:
  - Tests verify guild sync with channel creation failure rolls back guild
  - Tests verify game creation with participant failure rolls back game
  - Tests verify participant removal with notification failure rolls back removal
  - All multi-step operations proven atomic
  - Production incident scenario (guild without channels) cannot reoccur
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 50-60) - Production incident details
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 223-230) - Integration test guidance
- **Dependencies**:
  - Phase 4 completion

### Task 5.2: Add rollback scenario tests

Create tests that explicitly verify rollback behavior on errors.

- **Files**:
  - [tests/integration/test_transaction_rollback.py](../../tests/integration/test_transaction_rollback.py) - New file for rollback tests
- **Success**:
  - Tests force errors at various points in multi-step operations
  - Database state verified to be unchanged after rollback
  - No partial data persists after errors
  - All service types (guild, channel, template, game) tested
  - Rollback behavior consistent across all operations
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 232-238) - Rollback testing strategy
- **Dependencies**:
  - Task 5.1 completion

## Phase 6: Documentation and Guidelines

### Task 6.1: Document transaction management patterns

Create documentation for transaction management best practices.

- **Files**:
  - [docs/TRANSACTION_MANAGEMENT.md](../../docs/TRANSACTION_MANAGEMENT.md) - New documentation file
  - [.github/instructions/fastapi-transaction-patterns.instructions.md](../../.github/instructions/fastapi-transaction-patterns.instructions.md) - New instruction file
- **Success**:
  - Documentation explains route-level transaction boundaries
  - Clear examples of correct service layer patterns
  - Guidance on when to use flush vs commit
  - Error handling patterns documented
  - Instructions file enforces patterns for future development
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 240-249) - Documentation guidance
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 159-168) - SQLAlchemy best practices
- **Dependencies**:
  - Phases 1-5 completion for accurate examples

### Task 6.2: Add service layer docstring conventions

Establish docstring pattern for service functions regarding transactions.

- **Files**:
  - All service files in [services/api/services/](../../services/api/services/) - Add docstring notes
- **Success**:
  - All service functions that modify data include transaction note
  - Standard phrasing: "Does not commit. Caller must commit transaction."
  - Flush usage documented where applicable
  - Consistent documentation pattern across all services
- **Research References**:
  - #file:../research/20260130-service-layer-transaction-management-research.md (Lines 194-202) - Example refactor with docstring
- **Dependencies**:
  - Phases 1-3 completion

## Dependencies

- SQLAlchemy 2.0 async patterns
- FastAPI dependency injection
- pytest with AsyncMock

## Success Criteria

- All 17 service layer commits removed
- Transaction atomicity restored across all operations
- Test suite validates correct behavior
- Documentation guides future development
- Production incident scenario cannot reoccur

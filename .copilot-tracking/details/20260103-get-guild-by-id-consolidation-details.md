<!-- markdownlint-disable-file -->

# Task Details: get_guild_by_id Consolidation

## Research Reference

**Source Research**: #file:../research/20260103-get-guild-by-id-consolidation-research.md

## Phase 1: Test-First Implementation of Helper Function

### Task 1.1: Write comprehensive unit tests for require_guild_by_id (marked xfail)

Write test suite covering all scenarios BEFORE implementing the function. Mark all tests with `@pytest.mark.xfail(reason="require_guild_by_id not yet implemented")`.

- **Files**:
  - tests/services/api/database/test_queries_require_guild.py (CREATE NEW)
- **Test Cases**:
  1. Test guild exists + RLS context set + user authorized → returns guild_config
  2. Test guild exists + RLS context set + user NOT authorized → raises HTTPException(404)
  3. Test guild does NOT exist → raises HTTPException(404)
  4. Test guild exists + NO RLS context (None) + can fetch guilds → sets context, returns guild_config
  5. Test guild exists + NO RLS context + user authorized → sets context, returns guild_config
  6. Test guild exists + NO RLS context + user NOT authorized → sets context, raises HTTPException(404)
  7. Test custom error messages work correctly
  8. Test idempotent behavior (context already set → doesn't refetch)
  9. Test oauth2.get_user_guilds called only when context missing
  10. Test oauth2.get_user_guilds cache usage
- **Success**:
  - All tests written with clear assertions
  - All tests marked xfail
  - Tests import required mocks (AsyncSession, oauth2, guild_isolation)
  - Test coverage includes happy path and all error cases
  - pytest collection succeeds (tests are syntactically valid)
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 185-240) - Helper function specification with auto-context-setting
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing strategy
- **Dependencies**:
  - pytest-asyncio
  - pytest-mock
  - FastAPI test utilities

### Task 1.2: Implement require_guild_by_id helper function in queries.py

Implement the helper function with automatic RLS context setup and authorization enforcement.

- **Files**:
  - services/api/database/queries.py - Add new function after get_guild_by_id
- **Implementation**:
  ```python
  from fastapi import HTTPException
  from starlette import status
  from shared.data_access.guild_isolation import get_current_guild_ids, set_current_guild_ids

  async def require_guild_by_id(
      db: AsyncSession,
      guild_id: str,
      access_token: str,
      user_discord_id: str,
      not_found_detail: str = "Guild configuration not found"
  ) -> GuildConfiguration:
      """
      Fetch guild configuration by UUID with automatic RLS context setup.

      Sets RLS context if not already set (idempotent). Returns 404 for both
      "not found" and "unauthorized" to prevent information disclosure.
      """
      from services.api.auth import oauth2

      # Ensure RLS context is set (idempotent)
      if get_current_guild_ids() is None:
          user_guilds = await oauth2.get_user_guilds(access_token, user_discord_id)
          guild_ids = [g["id"] for g in user_guilds]
          set_current_guild_ids(guild_ids)

      guild_config = await get_guild_by_id(db, guild_id)
      if not guild_config:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=not_found_detail
          )

      # Defense in depth: Manual authorization check
      authorized_guild_ids = get_current_guild_ids()
      if authorized_guild_ids is None or guild_config.guild_id not in authorized_guild_ids:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=not_found_detail
          )

      return guild_config
  ```
- **Success**:
  - Function added to queries.py
  - All imports added correctly
  - Function signature matches specification
  - Idempotent RLS context setup implemented
  - Manual authorization check implemented
  - Returns 404 (not 403) to prevent information disclosure
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 185-240) - Complete implementation specification
- **Dependencies**:
  - services.api.auth.oauth2 module
  - shared.data_access.guild_isolation module

### Task 1.3: Remove xfail markers and verify all tests pass

Remove xfail markers from tests and verify implementation is correct.

- **Files**:
  - tests/services/api/database/test_queries_require_guild.py
- **Success**:
  - All xfail markers removed
  - All tests pass
  - 100% code coverage for require_guild_by_id
  - No regressions in existing tests
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing validation
- **Dependencies**:
  - Task 1.2 completion

## Phase 2: Migrate guilds.py Routes (6 locations)

### Task 2.1: Add integration tests for guilds.py routes (verify no behavior change)

Add integration tests that will verify behavior doesn't change during migration.

- **Files**:
  - tests/integration/test_guilds_routes_migration.py (CREATE NEW)
- **Test Cases**:
  1. GET /guilds/{guild_id} - authorized user → 200
  2. GET /guilds/{guild_id} - unauthorized user → 404
  3. GET /guilds/{guild_id}/config - authorized user → 200
  4. PUT /guilds/{guild_id}/config - authorized user → 200
  5. GET /guilds/{guild_id}/channels - authorized user → 200
  6. GET /guilds/{guild_id}/roles - authorized user → 200
  7. POST /guilds/{guild_id}/validate-mention - authorized user → 200
  8. All routes with invalid guild_id → 404
- **Success**:
  - Integration tests pass with current implementation
  - Tests will verify no behavior change after migration
  - Error messages verified
  - Authorization verified
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 86-100) - Current guilds.py locations
- **Dependencies**:
  - Integration test infrastructure
  - Test OAuth tokens

### Task 2.2: Migrate get_guild_basic_info (line 89)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 89)
- **Before**:
  ```python
  guild_config = await queries.get_guild_by_id(db, guild_id)
  if not guild_config:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Guild configuration not found",
      )
  ```
- **After**:
  ```python
  guild_config = await queries.require_guild_by_id(
      db, guild_id, current_user.access_token, current_user.user.discord_id
  )
  ```
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Phase 1 completion

### Task 2.3: Migrate get_guild_config (line 121)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 121)
- **Before/After**: Same pattern as Task 2.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 2.2 completion

### Task 2.4: Migrate update_guild_config (line 192)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 192)
- **Before/After**: Same pattern as Task 2.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 2.3 completion

### Task 2.5: Migrate list_guild_channels (line 228)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 228)
- **Before/After**: Same pattern as Task 2.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 2.4 completion

### Task 2.6: Migrate get_guild_roles (line 272)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 272)
- **Before/After**: Same pattern as Task 2.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 2.5 completion

### Task 2.7: Migrate validate_mention (line 344)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/guilds.py (line 344)
- **Before/After**: Same pattern as Task 2.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 2.6 completion

### Task 2.8: Run integration tests to verify no behavior changes

Run full integration test suite for guilds.py routes.

- **Files**:
  - tests/integration/test_guilds_routes_migration.py
- **Success**:
  - All integration tests pass
  - Error responses unchanged
  - Authorization behavior unchanged
  - Performance acceptable
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing strategy
- **Dependencies**:
  - All Phase 2 migration tasks complete

## Phase 3: Migrate templates.py Routes (2 locations)

### Task 3.1: Add integration tests for templates.py routes

Add integration tests that will verify behavior doesn't change during migration.

- **Files**:
  - tests/integration/test_templates_routes_migration.py (CREATE NEW)
- **Test Cases**:
  1. GET /templates?guild_id={guild_id} - authorized user → 200
  2. GET /templates?guild_id={guild_id} - unauthorized user → 404
  3. POST /templates - authorized user → 201
  4. POST /templates - unauthorized guild_id → 404
- **Success**:
  - Integration tests pass with current implementation
  - Tests will verify no behavior change after migration
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 76-85) - Current templates.py locations
- **Dependencies**:
  - Phase 2 completion

### Task 3.2: Migrate list_templates (line 55)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/templates.py (line 55)
- **Before**:
  ```python
  guild_config = await queries.get_guild_by_id(db, guild_id)
  if not guild_config:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Guild configuration not found",
      )
  ```
- **After**:
  ```python
  guild_config = await queries.require_guild_by_id(
      db, guild_id, current_user.access_token, current_user.user.discord_id
  )
  ```
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Migrate create_template (line 181)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/routes/templates.py (line 181)
- **Before/After**: Same pattern as Task 3.2
- **Success**:
  - Code replaced successfully
  - Integration tests still pass
  - Service remains operational
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 242-265) - Migration pattern
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Run integration tests to verify no behavior changes

Run full integration test suite for templates.py routes.

- **Files**:
  - tests/integration/test_templates_routes_migration.py
- **Success**:
  - All integration tests pass
  - Error responses unchanged
  - Authorization behavior unchanged
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing strategy
- **Dependencies**:
  - All Phase 3 migration tasks complete

## Phase 4: Migrate permissions.py Functions (3 locations)

### Task 4.1: Add unit tests for permissions.py functions

Add unit tests that will verify behavior doesn't change during migration.

- **Files**:
  - tests/services/api/dependencies/test_permissions_migration.py (CREATE NEW)
- **Test Cases**:
  1. verify_template_access - authorized user → success
  2. verify_template_access - unauthorized user → raises HTTPException(404, "Template not found")
  3. verify_game_access - authorized user → success
  4. verify_game_access - unauthorized user → raises HTTPException(404, "Game not found")
  5. resolve_guild_discord_id - authorized user → returns Discord guild ID
  6. resolve_guild_discord_id - unauthorized user → raises HTTPException(404)
- **Success**:
  - Unit tests pass with current implementation
  - Tests will verify no behavior change after migration
  - Custom error messages verified
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 102-120) - Current permissions.py locations
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Migrate verify_template_access (line 135) with custom message

Replace get_guild_by_id + error handling with require_guild_by_id call using custom error message.

- **Files**:
  - services/api/dependencies/permissions.py (line 135)
- **Before**:
  ```python
  guild_config = await queries.get_guild_by_id(db, template.guild_id)
  if not guild_config:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Template not found"
      )
  ```
- **After**:
  ```python
  guild_config = await queries.require_guild_by_id(
      db, template.guild_id, access_token, user_discord_id,
      not_found_detail="Template not found"
  )
  ```
- **Success**:
  - Code replaced successfully with custom message
  - Unit tests still pass
  - Error message "Template not found" preserved
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 267-275) - Custom message pattern
- **Dependencies**:
  - Task 4.1 completion

### Task 4.3: Migrate verify_game_access (line 181) with custom message

Replace get_guild_by_id + error handling with require_guild_by_id call using custom error message.

- **Files**:
  - services/api/dependencies/permissions.py (line 181)
- **Before**:
  ```python
  guild_config = await queries.get_guild_by_id(db, game.guild_id)
  if not guild_config:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Game not found"
      )
  ```
- **After**:
  ```python
  guild_config = await queries.require_guild_by_id(
      db, game.guild_id, access_token, user_discord_id,
      not_found_detail="Game not found"
  )
  ```
- **Success**:
  - Code replaced successfully with custom message
  - Unit tests still pass
  - Error message "Game not found" preserved
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 267-275) - Custom message pattern
- **Dependencies**:
  - Task 4.2 completion

### Task 4.4: Migrate resolve_guild_discord_id (line 242)

Replace get_guild_by_id + error handling with require_guild_by_id call.

- **Files**:
  - services/api/dependencies/permissions.py (line 242)
- **Before**:
  ```python
  guild_config = await queries.get_guild_by_id(db, guild_id)
  if not guild_config:
      raise HTTPException(
          status_code=status.HTTP_404_NOT_FOUND,
          detail="Guild configuration not found"
      )
  ```
- **After**:
  ```python
  # Note: This function is called from require_manage_guild which has current_user
  guild_config = await queries.require_guild_by_id(
      db, guild_id, access_token, user_discord_id
  )
  ```
- **Success**:
  - Code replaced successfully
  - Unit tests still pass
  - Function called from require_manage_guild has access to credentials
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 122-140) - RLS context availability
- **Dependencies**:
  - Task 4.3 completion

### Task 4.5: Run unit tests to verify no behavior changes

Run full unit test suite for permissions.py functions.

- **Files**:
  - tests/services/api/dependencies/test_permissions_migration.py
- **Success**:
  - All unit tests pass
  - Error responses unchanged (including custom messages)
  - Authorization behavior unchanged
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing strategy
- **Dependencies**:
  - All Phase 4 migration tasks complete

## Phase 5: Final Verification and Security Validation

### Task 5.1: Run full test suite (unit + integration + e2e)

Run complete test suite to ensure no regressions.

- **Files**:
  - All test files
- **Commands**:
  ```bash
  uv run pytest tests/services/api/database/test_queries_require_guild.py -v
  uv run pytest tests/integration/test_guilds_routes_migration.py -v
  uv run pytest tests/integration/test_templates_routes_migration.py -v
  uv run pytest tests/services/api/dependencies/test_permissions_migration.py -v
  uv run pytest tests/ -v
  ```
- **Success**:
  - All unit tests pass
  - All integration tests pass
  - All e2e tests pass
  - No test failures or regressions
  - Code coverage maintained or improved
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 320-330) - Testing strategy
- **Dependencies**:
  - All migration phases complete

### Task 5.2: Perform security validation testing

Manually verify authorization enforcement and information disclosure prevention.

- **Files**:
  - Manual testing against running API
- **Test Scenarios**:
  1. Attempt to access guild_config for guild user is NOT member of
     - Expected: 404 (not 403, to prevent info disclosure)
  2. Attempt with valid guild_id but invalid OAuth token
     - Expected: 401 or 404
  3. Verify RLS context is set correctly in all routes
  4. Verify oauth2.get_user_guilds cache is used (no repeated calls)
  5. Test with missing RLS context → verify context is set
  6. Test with existing RLS context → verify not refetched
- **Success**:
  - All security scenarios pass
  - 404 returned for unauthorized access (not 403)
  - RLS context set automatically when missing
  - oauth2.get_user_guilds cache working (5-min cache)
  - No information disclosure vulnerabilities
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 331-356) - Security validation
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Verify all 11 locations migrated

Verify no old pattern remains in codebase.

- **Files**:
  - Search across all Python files
- **Verification**:
  ```bash
  # Should find NO matches of old pattern
  grep -r "await queries.get_guild_by_id" services/api/routes/
  grep -r "await queries.get_guild_by_id" services/api/dependencies/

  # Should find 11 matches of new pattern
  grep -r "await queries.require_guild_by_id" services/api/routes/
  grep -r "await queries.require_guild_by_id" services/api/dependencies/
  ```
- **Success**:
  - Old pattern found 0 times in routes and dependencies
  - New pattern found exactly 11 times (6 guilds.py + 2 templates.py + 3 permissions.py)
  - All locations accounted for
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md (Lines 76-120) - All 11 locations documented
- **Dependencies**:
  - All migration phases complete

### Task 5.4: Document changes and close security gap

Update documentation to reflect consolidation and security improvements.

- **Files**:
  - .copilot-tracking/changes/20260103-get-guild-by-id-consolidation-changes.md
  - docs/PRODUCTION_READINESS_GUILD_ISOLATION.md (update security section)
- **Documentation**:
  - Summarize all changes made
  - Document security gap that was closed
  - Document RLS context setup automation
  - Note code reduction (44-55 lines → 11 lines)
  - Document testing performed
  - Add notes about future RLS enablement on guild_configurations
- **Success**:
  - Changes file updated with complete summary
  - Security documentation updated
  - Clear record of what was done and why
- **Research References**:
  - #file:../research/20260103-get-guild-by-id-consolidation-research.md - Complete research for documentation
- **Dependencies**:
  - Task 5.3 completion

## Dependencies

- pytest with async support
- FastAPI testing client
- Mock OAuth2 tokens for testing
- Access to development database
- Integration test infrastructure

## Success Criteria

- All 11 locations migrated to use require_guild_by_id
- 100% test coverage for new helper function
- All existing tests pass without modification
- Security validation confirms authorization enforcement
- No service interruptions during migration
- Code reduction: 44-55 lines to 11 lines achieved
- Documentation updated

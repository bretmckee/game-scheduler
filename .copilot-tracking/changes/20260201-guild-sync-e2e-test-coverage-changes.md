<!-- markdownlint-disable-file -->

# Release Changes: Guild Sync E2E Test Coverage

**Related Plan**: 20260201-guild-sync-e2e-test-coverage-plan.instructions.md
**Implementation Date**: 2026-02-01

## Summary

Comprehensive e2e test suite for guild sync functionality including database verification, idempotency testing, cross-guild isolation, and error scenarios.

**IMPORTANT NOTE**: This implementation is INCOMPLETE due to non-hermetic test infrastructure.

### Current Status

The new guild sync tests in `test_guild_sync_e2e.py` are complete and work correctly, but they revealed a fundamental issue: **all e2e tests are non-hermetic**. Tests depend on the init service pre-creating guilds rather than creating them in fixtures. This causes:

1. **Test execution order dependencies**: Tests pass in isolation but fail when run after guild sync tests that clean up guilds
2. **Fixture scope issues**: `synced_guild` fixture doesn't actually create guilds - it finds them already present from init service
3. **Cascading failures**: When `fresh_guild_sync` fixture properly cleans up (hermetic behavior), 11 other tests fail because they expect guilds to exist

### What Was Attempted

- Modified `synced_guild` and `synced_guild_b` fixtures to delete guilds before syncing (hermeticity)
- Removed guild creation from `seed_e2e.py` init service
- Result: Tests became hermetic but broke other non-hermetic tests

### What Needs To Happen

**BEFORE these guild sync tests can be merged**, the entire e2e test suite must be made hermetic:

1. **Update all e2e test fixtures** to ensure each test creates its own guilds via `synced_guild`
2. **Remove init service guild creation** - only create users (authentication) not guilds
3. **Fix the 11 failing tests**:
   - `test_join_notification.py` (2 tests)
   - `test_player_removal.py` (1 test)
   - `test_signup_methods.py` (4 tests)
   - `test_user_join.py` (1 test)
   - `test_waitlist_promotion.py` (2 tests)
4. **Verify full suite passes** with hermetic fixtures before merging guild sync tests

### Files Currently in Limbo

- `tests/e2e/test_guild_sync_e2e.py` - **KEEP** (complete and correct)
- `tests/e2e/test_guild_sync_e2e.py.backup` - **KEEP** (backup of first iteration)
- Hermeticity changes - **REVERTED** (will be done in separate effort)

### Resuming This Work

1. Wait for separate hermeticity effort to make all e2e tests hermetic
2. Once that's complete, merge `test_guild_sync_e2e.py` without changes
3. The `fresh_guild_sync` fixture in that file is already hermetic and won't break other hermetic tests
4. Full test suite should pass with all tests being hermetic

## Changes

### Added

- tests/e2e/test_guild_sync_e2e.py - New e2e test file with guild sync test infrastructure including database verification helper fixtures
  - `test_complete_guild_creation()` - Verifies full sync workflow (guild → channels → templates) with database state validation
  - `test_sync_idempotency()` - Verifies repeated syncs don't create duplicate records
  - `test_multi_guild_sync()` - Verifies User A and User B each sync only their admin guilds with proper isolation
  - `test_rls_enforcement_after_sync()` - Verifies RLS properly isolates guild template access after sync
  - `test_channel_filtering()` - Verifies only text channels (type=0) are synced, not voice channels
  - `test_template_creation_with_channels()` - Verifies default template creation for guilds with text channels
  - `test_sync_respects_user_permissions()` - Verifies sync respects MANAGE_GUILD permissions and bot guild membership

### Modified

- tests/e2e/test_01_authentication.py - Enhanced `test_synced_guild_creates_configs()` docstring to reference comprehensive guild sync tests in test_guild_sync_e2e.py

### Removed

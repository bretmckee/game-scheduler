<!-- markdownlint-disable-file -->

# Release Changes: Service Layer Transaction Management and Atomicity

**Related Plan**: 20260130-service-layer-transaction-management-plan.instructions.md
**Implementation Date**: 2026-01-30

## Summary

Restore transaction atomicity by removing premature commits from service layer functions and enforcing route-level transaction boundaries.

## Changes

### Added

### Modified

- services/api/routes/auth.py - Removed manual commit from OAuth callback, user creation now atomic with token storage, improved error handling (Redis failure rolls back user creation)

- services/api/services/guild_service.py - Removed commits from create_guild_config() and update_guild_config(), replaced with flush for ID generation, added transaction docstring notes, removed unused db parameter from update_guild_config()
- services/api/services/channel_service.py - Removed commits from create_channel_config() and update_channel_config(), replaced with flush for ID generation, added transaction docstring notes, removed unused db parameter from update_channel_config()
- services/api/routes/guilds.py - Updated update_guild_config() call to remove db argument
- services/api/routes/channels.py - Updated update_channel_config() call to remove db argument
- services/bot/events/handlers.py - Refactored _handle_game_created() to reduce cognitive complexity from 18 to 14 by extracting validation helpers (_validate_game_created_event, _validate_discord_channel, _get_bot_channel)
- tests/services/api/services/test_guild_service.py - Updated tests to verify no commits in service layer, expect flush for ID generation, removed db parameter from update tests
- tests/services/api/services/test_channel_service.py - Updated tests to verify no commits in service layer, expect flush for ID generation, removed db parameter from update tests
- tests/services/api/routes/test_channels.py - Added test_update_channel_config_success to verify route-level transaction handling
- tests/services/bot/events/test_handlers.py - Added 8 tests for new validation helper methods with comprehensive coverage of success and error paths
- services/api/services/template_service.py - Removed all 6 commits from CRUD operations (create_template, create_default_template, update_template, set_default, delete_template, reorder_templates), replaced with flush for ID generation where needed, added transaction docstring notes
- tests/services/api/services/test_template_service.py - Updated all 6 test functions (test_create_template, test_create_default_template, test_update_template, test_set_default, test_delete_template, test_reorder_templates) to expect flush instead of commit, removed refresh assertions, verified all tests pass
- services/api/services/games.py - Removed all 6 commits from game operations (create_game, update_game, delete_game, join_game, leave_game), replaced with flush in join_game for ID generation, added transaction docstring notes to all public methods
- tests/services/api/services/test_games.py - Removed commit assertions from 6 test functions (test_update_game_fields, test_update_game_where_field, test_delete_game_success, test_leave_game_success, test_join_game_success, test_join_game_already_joined), updated to expect flush instead of commit where appropriate, verified all tests pass

## Phase 4: Route Handler Verification - COMPLETE

### Task 4.1: Audit Results

**All mutation endpoints verified:**

- **services/api/routes/guilds.py**: 6 mutation endpoints use `Depends(database.get_db)` or `Depends(database.get_db_with_user_guilds())` - ✅ CORRECT
- **services/api/routes/channels.py**: 3 mutation endpoints use `Depends(database.get_db)` - ✅ CORRECT
- **services/api/routes/templates.py**: 7 mutation endpoints use `Depends(database.get_db_with_user_guilds())` - ✅ CORRECT
- **services/api/routes/games.py**: Game service injected via `_get_game_service()` which internally uses `Depends(database.get_db_with_user_guilds())` - ✅ CORRECT
- **services/api/routes/export.py**: 1 endpoint uses `Depends(database.get_db_with_user_guilds())` - ✅ CORRECT

**Issue Found:**

- **services/api/routes/auth.py**: Line 117 had manual `await db.commit()` within callback endpoint that uses `Depends(get_db)`. **FIXED** - Removed manual commit; user creation now participates in route-level transaction. Token storage in Redis happens before commit, and if Redis fails, user creation rolls back (improved atomicity).

**Manual commit/rollback audit:**
- Manual commit in services/api/routes/auth.py removed (was at line 117)
- Zero manual rollback calls found in route handlers
- All routes properly delegate transaction management to get_db() dependency

### Task 4.2: Transaction Boundary Verification

**Orchestrator functions verified atomic:**

1. **guild_service.sync_user_guilds()**:
   - Calls `_create_guild_with_channels_and_template()` for each new guild
   - Creates guild config, multiple channel configs, and default template
   - No commits in orchestrator or helper functions - ✅ ATOMIC
   - Transaction boundary at route level (routes/guilds.py sync_guilds endpoint)

2. **games.GameService.create_game()**:
   - Creates game session
   - Resolves and creates participant records
   - Sets up notification schedules
   - Sets up status transition schedules
   - No commits in service method - ✅ ATOMIC
   - Transaction boundary at route level (routes/games.py create_game endpoint)

3. **games.GameService.update_game()**:
   - Updates game fields
   - Removes participants
   - Updates prefilled participants
   - Updates notification and status schedules
   - Detects and notifies promotions
   - No commits in service method - ✅ ATOMIC
   - Transaction boundary at route level (routes/games.py update_game endpoint)

4. **games.GameService.delete_game()** (cancel):
   - Deletes status schedules
   - Updates game status to CANCELLED
   - No commits in service method - ✅ ATOMIC
   - Transaction boundary at route level (routes/games.py delete_game endpoint)

5. **games.GameService.join_game()**:
   - Adds participant record
   - Creates join notification schedule
   - No commits in service method (flush only for ID generation) - ✅ ATOMIC
   - Transaction boundary at route level (routes/games.py join_game endpoint)

6. **games.GameService.leave_game()**:
   - Removes participant record
   - No commits in service method - ✅ ATOMIC
   - Transaction boundary at route level (routes/games.py leave_game endpoint)

**Verification Summary:**
- All orchestrator functions maintain atomicity
- Multi-step operations complete fully or rollback completely
- No commits within service layer break transaction boundaries
- Production incident scenario (guild without channels) cannot reoccur with current implementation

### Removed

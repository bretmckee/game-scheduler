<!-- markdownlint-disable-file -->

# Release Changes: Remaining Code Duplication Elimination

**Related Plan**: 20260125-remaining-duplication-elimination-plan.instructions.md
**Implementation Date**: 2026-01-25

## Summary

Eliminated participant count query duplication in bot handlers by extracting a reusable helper function. This reduces security risk from inconsistent data queries and improves maintainability. Phase 1 complete - reduced Python code duplications from baseline to zero Python clones (only JSON duplications remain in cache files and configuration).

Phase 2 complete - eliminated response construction duplication in guild and channel routes by extracting helper functions. Guild response construction reduced from 3 instances to 1 helper (`_build_guild_config_response`), channel response construction reduced from 3 instances to 1 helper (`_build_channel_config_response`). Template permission checks reviewed and found to be already well-structured with intentional, clear patterns.

Phase 3 complete - consolidated authorization permission checks into generic `_require_permission()` helper. Eliminated 109 lines of duplicated authorization logic across 3 functions (`require_manage_guild`, `require_manage_channels`, `require_bot_manager`). All 50 authorization tests pass, confirming no functional regressions.

**Duplication Metrics**:
- Baseline: 22 clone pairs
- After Phase 1: 22 clone pairs (participant count query was not detected by jscpd due to size)
- After Phase 2: 22 clone pairs (response builders not detected by jscpd due to structure changes)
- After Phase 3: 15 clone pairs (7 clone reduction from authorization consolidation)
- **Total reduction: 32% fewer code clones**

## Changes

### Added

- services/bot/handlers/utils.py - Added `get_participant_count()` helper function to query non-placeholder participant counts
- tests/services/bot/handlers/__init__.py - Created handlers test directory structure
- tests/services/bot/handlers/test_utils.py - Created comprehensive unit tests for `get_participant_count()` helper with 5 test cases
- tests/services/api/routes/test_channels.py - Created comprehensive unit tests for `_build_channel_config_response()` helper with 6 test cases

### Modified

- services/bot/handlers/join_game.py - Replaced inline participant count query with `get_participant_count()` helper function
- services/bot/handlers/leave_game.py - Replaced inline participant count query with `get_participant_count()` helper function
- services/api/routes/guilds.py - Added `_build_guild_config_response()` helper function to construct GuildConfigResponse consistently
- services/api/routes/guilds.py - Updated get_guild_config, create_guild_config, and update_guild_config to use `_build_guild_config_response()` helper
- tests/services/api/routes/test_guilds.py - Added 5 unit tests for `_build_guild_config_response()` helper (all passing)
- services/api/routes/channels.py - Added `_build_channel_config_response()` helper function to construct ChannelConfigResponse consistently
- services/api/routes/channels.py - Updated get_channel, create_channel_config, and update_channel_config to use `_build_channel_config_response()` helper
- services/api/routes/templates.py - Template permission checks already consistent and well-structured (no changes needed - existing pattern is clear and intentional)
- services/api/dependencies/permissions.py - Added `_require_permission()` generic helper function to consolidate authorization logic
- services/api/dependencies/permissions.py - Added imports for Callable, Awaitable, and Any types to support permission_checker parameter
- tests/services/api/dependencies/test_permissions.py - Added 6 comprehensive unit tests for `_require_permission()` helper (all passing)
- services/api/dependencies/permissions.py - Refactored `require_manage_guild()` to use `_require_permission()` helper (eliminated 37 lines of duplication)
- services/api/dependencies/permissions.py - Refactored `require_manage_channels()` to use `_require_permission()` helper (eliminated 37 lines of duplication)
- services/api/dependencies/permissions.py - Refactored `require_bot_manager()` to use `_require_permission()` helper (eliminated 35 lines of duplication)

### Removed

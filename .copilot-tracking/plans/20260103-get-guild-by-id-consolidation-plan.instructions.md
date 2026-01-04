---
applyTo: ".copilot-tracking/changes/20260103-get-guild-by-id-consolidation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: get_guild_by_id Consolidation

## Overview

Consolidate 11 duplicated `get_guild_by_id()` + error handling patterns into single helper function with automatic RLS context setup and authorization enforcement.

## Objectives

- Reduce 44-55 lines of duplicated code to 11 lines (~75% reduction)
- Add authorization enforcement to close security gap
- Enable automatic RLS context setup for future RLS on guild_configurations
- Maintain system availability throughout implementation
- Write tests before implementation (marked xfail until code complete)

## Research Summary

### Project Files

- services/api/database/queries.py - Base function definition, target for new helper
- services/api/routes/templates.py (2 locations) - Template operations
- services/api/routes/guilds.py (6 locations) - Guild configuration operations
- services/api/dependencies/permissions.py (3 locations) - Permission checks

### External References

- #file:../research/20260103-get-guild-by-id-consolidation-research.md - Comprehensive duplication analysis
- #file:../../.github/instructions/api-authorization.instructions.md - Authorization patterns
- #file:../../.github/instructions/python.instructions.md - Python coding standards

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment guidelines
- #file:../../.github/instructions/integration-tests.instructions.md - Testing standards

## Implementation Checklist

### [x] Phase 1: Test-First Implementation of Helper Function

- [x] Task 1.1: Write comprehensive unit tests for require_guild_by_id (marked xfail)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 25-85)

- [x] Task 1.2: Implement require_guild_by_id helper function in queries.py
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 87-125)

- [x] Task 1.3: Remove xfail markers and verify all tests pass
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 127-140)

### [x] Phase 2: Migrate guilds.py Routes (6 locations)

- [x] Task 2.1: Add e2e tests for guilds.py routes (verify no behavior change)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 142-175)

- [x] Task 2.2: Migrate get_guild_basic_info (line 89)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 177-195)

- [x] Task 2.3: Migrate get_guild_config (line 121)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 197-215)

- [x] Task 2.4: Migrate update_guild_config (line 192)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 217-235)

- [x] Task 2.5: Migrate list_guild_channels (line 228)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 237-255)

- [x] Task 2.6: Migrate get_guild_roles (line 272)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 257-275)

- [x] Task 2.7: Migrate validate_mention (line 344)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 277-295)

- [x] Task 2.8: Run integration tests to verify no behavior changes
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 297-310)

### [x] Phase 3: Migrate templates.py Routes (2 locations)

- [x] Task 3.1: Add integration tests for templates.py routes
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 312-335)

- [x] Task 3.2: Migrate list_templates (line 55)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 337-355)

- [x] Task 3.3: Migrate create_template (line 181)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 357-375)

- [x] Task 3.4: Run integration tests to verify no behavior changes
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 377-390)

### [x] Phase 4: Migrate permissions.py Functions (3 locations)

- [x] Task 4.1: Add unit tests for permissions.py functions
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 392-425)

- [x] Task 4.2: Migrate verify_template_access (line 135) with custom message
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 427-450)

- [x] Task 4.3: Migrate verify_game_access (line 181) with custom message
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 452-475)

- [x] Task 4.4: Migrate resolve_guild_discord_id (line 242)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 477-495)

- [x] Task 4.5: Run unit tests to verify no behavior changes
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 497-510)

### [x] Phase 5: Final Verification and Security Validation

- [x] Task 5.1: Run full test suite (unit + integration + e2e)
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 512-530)

- [x] Task 5.2: Perform security validation testing
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 532-560)

- [x] Task 5.3: Verify all 11 locations migrated
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 562-580)

- [x] Task 5.4: Document changes and close security gap
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 582-600)

### [x] Phase 6: Enable RLS on guild_configurations Table

- [x] Task 6.1: Create Alembic migration to add RLS policy
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 602-635)

- [x] Task 6.2: Test RLS enforcement in development environment
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 637-665)

- [x] Task 6.3: Run full test suite to verify RLS doesn't break existing functionality
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 667-685)

- [x] Task 6.4: Optional - Simplify helper to remove manual authorization check
  - Details: .copilot-tracking/details/20260103-get-guild-by-id-consolidation-details.md (Lines 687-710)

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
- (Optional) RLS policy enabled on guild_configurations for defense in depth

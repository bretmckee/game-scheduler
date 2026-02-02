---
applyTo: ".copilot-tracking/changes/20260201-e2e-test-hermetic-isolation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: E2E Test Hermetic Isolation

## Overview

Replace shared E2E test state seeded at container startup with function-scoped fixtures that create guilds via /api/v1/guilds/sync and clean up after each test.

## Objectives

- Eliminate shared database state from E2E tests
- Enable tests to create guilds from scratch
- Make every test hermetic with automatic cleanup
- Preserve test logic while updating fixture dependencies
- Support concurrent test execution without interference

## Research Summary

### Project Files

- services/init/seed_e2e.py - Seeds Guild A + Guild B at container startup
- services/init/main.py - Calls seed_e2e_data() in Phase 6
- tests/e2e/conftest.py - Session-scoped fixtures providing Discord IDs
- tests/e2e/test_00_environment.py - Validates init service seeded data
- tests/e2e/test_01_authentication.py - Uses synced_guild fixture
- 21 test files total requiring fixture updates

### External References

- #file:../research/20260201-e2e-test-hermetic-isolation-research.md - Complete analysis of current state, fixture design, and migration patterns

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting standards

## Implementation Checklist

### [ ] Phase 1: Environment Variable Management

- [ ] Task 1.1: Create DiscordTestEnvironment dataclass
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 15-45)

- [ ] Task 1.2: Create discord_ids session-scoped fixture
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 47-70)

### [ ] Phase 2: Guild Creation Fixtures

- [ ] Task 2.1: Create GuildContext dataclass
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 72-95)

- [ ] Task 2.2: Create fresh_guild fixture with cleanup
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 97-160)

- [ ] Task 2.3: Create fresh_guild_b fixture with cleanup
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 162-220)

### [ ] Phase 3: Remove Init Service Seeding

- [ ] Task 3.1: Remove seed_e2e_data() call from init service
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 222-240)

- [ ] Task 3.2: Mark seed_e2e.py as deprecated
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 242-260)

### [ ] Phase 4: Update test_00_environment.py

- [ ] Task 4.1: Keep database/migration validation tests
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 262-285)

- [ ] Task 4.2: Remove seeded data validation tests
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 287-310)

- [ ] Task 4.3: Add discord_ids fixture validation test
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 312-330)

### [ ] Phase 5: Update Guild-Dependent Fixtures

- [ ] Task 5.1: Remove individual ID fixtures
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 332-355)

- [ ] Task 5.2: Replace guild_a_db_id and guild_b_db_id fixtures
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 357-380)

- [ ] Task 5.3: Replace guild_a_template_id and guild_b_template_id fixtures
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 382-405)

- [ ] Task 5.4: Update synced_guild and synced_guild_b fixtures
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 407-430)

### [ ] Phase 6: Migrate Test Files

- [ ] Task 6.1: Update test_01_authentication.py
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 432-460)

- [ ] Task 6.2: Update test_guild_routes_e2e.py
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 462-490)

- [ ] Task 6.3: Update test_guild_isolation_e2e.py
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 492-520)

- [ ] Task 6.4: Migrate 16 game-related test files
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 522-600)

### [ ] Phase 7: Update Documentation

- [ ] Task 7.1: Update TESTING.md with new fixture patterns
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 602-630)

- [ ] Task 7.2: Document environment variable validation
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 632-655)

- [ ] Task 7.3: Add troubleshooting section
  - Details: .copilot-tracking/details/20260201-e2e-test-hermetic-isolation-details.md (Lines 657-680)

## Dependencies

- Pytest fixtures framework
- AsyncSession for database operations
- httpx.AsyncClient for API calls
- Discord bot with guild membership
- Database CASCADE constraints for cleanup

## Success Criteria

- All E2E tests pass with no shared state
- Each test creates and cleans up own guilds
- Can write tests that create guilds from scratch
- test_00_environment.py validates database/migrations only
- No orphaned database records after test suite
- Test logic unchanged - only fixture dependencies modified
- Guild creation/sync tests work without pre-seeded data

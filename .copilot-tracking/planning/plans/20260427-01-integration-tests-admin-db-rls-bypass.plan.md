---
applyTo: '.copilot-tracking/changes/20260427-01-integration-tests-admin-db-rls-bypass-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Integration Tests Using admin_db Bypass RLS

## Overview

Convert the 12 defective `GameService(db=admin_db, ...)` calls in
`test_game_image_integration.py` to use `app_db` with an RLS guild context,
so the integration tests exercise the same row-level security policies that
production HTTP routes enforce.

## Objectives

- Replace all `GameService(db=admin_db, ...)` operation calls with `GameService(db=app_db, ...)`
  preceded by `set_config('app.current_guild_ids', ...)` in `test_game_image_integration.py`
- Keep `admin_db` for fixture setup (INSERT) and post-operation verification (SELECT)
- Ensure all 13 tests in the file pass after conversion

## Research Summary

### Project Files

- `tests/integration/services/api/services/test_game_image_integration.py` - file with 13 defective GameService calls
- `tests/conftest.py` (lines 163-315) - `admin_db`, `app_db`, `bot_db` fixture definitions
- `shared/database.py` (lines 122-170) - production `get_db_with_user_guilds` showing RLS enforcement

### External References

- #file:../research/20260427-01-integration-tests-admin-db-rls-bypass-research.md - complete defect analysis and correct split pattern

### Standards References

- #file:../../.github/instructions/test-driven-development.instructions.md - "retrofitting tests for correct code" scenario: no stubs or xfail
- #file:../../.github/instructions/unit-tests.instructions.md - behavioral assertions required
- #file:../../.github/instructions/integration-tests.instructions.md - integration test conventions
- #file:../../.github/instructions/test-execution.instructions.md - use tee when capturing output

## Implementation Checklist

### [ ] Phase 1: Convert GameService Instances to Use app_db with RLS Context

- [ ] Task 1.1: Convert all 12 `GameService(db=admin_db, ...)` operation calls to use `app_db` with guild RLS context in `test_game_image_integration.py`
  - Details: .copilot-tracking/planning/details/20260427-01-integration-tests-admin-db-rls-bypass-details.md (Lines 11-78)

## Dependencies

- Integration test environment with PostgreSQL and RLS enabled (`scripts/run-integration-tests.sh`)
- `app_db` fixture already present in `tests/conftest.py`

## Success Criteria

- All `GameService` calls in `test_game_image_integration.py` that perform the operation under test use `app_db` with `set_config('app.current_guild_ids', ...)` set before the call
- All 13 tests in `test_game_image_integration.py` pass under `scripts/run-integration-tests.sh`

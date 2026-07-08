<!-- markdownlint-disable-file -->

# Task Details: Integration Tests Using admin_db Bypass RLS

## Research Reference

**Source Research**: #file:../research/20260427-01-integration-tests-admin-db-rls-bypass-research.md

## Phase 1: Convert GameService Instances to Use app_db with RLS Context

### Task 1.1: Convert all GameService(db=admin_db) calls in test_game_image_integration.py

In `tests/integration/services/api/services/test_game_image_integration.py`, every
`GameService(db=admin_db, ...)` call that exercises the operation under test must be split:
fixture data is inserted via `admin_db` (BYPASSRLS), the operation is performed via `app_db`
(RLS enforced) with the guild RLS context configured, and verification reads after the
operation continue to use `admin_db`.

The correct pattern (from the research):

```python
# Setup: use admin_db (BYPASSRLS) to insert fixture data
setup_service = GameService(db=admin_db, ...)
game = await setup_service.create_game(...)
await admin_db.commit()

# Exercise: use app_db (RLS enforced) with guild context set
await app_db.execute(
    text("SELECT set_config('app.current_guild_ids', :guild_ids, false)"),
    {"guild_ids": guild["id"]},
)
app_service = GameService(db=app_db, ...)
await app_service.delete_game(...)
await app_db.commit()

# Verify: use admin_db to read back results (bypasses RLS so assertions aren't blocked)
result = await admin_db.execute(select(GameSession).where(GameSession.id == game_id))
assert result.scalar_one_or_none() is None
```

The 13 `GameService(db=admin_db, ...)` instances, and the action required for each:

| Line | Test name                                                | Action needed                            |
| ---- | -------------------------------------------------------- | ---------------------------------------- |
| 136  | test_create_game_with_thumbnail_stores_image             | use app_db for create                    |
| 198  | test_create_game_with_both_images_stores_both            | use app_db for create                    |
| 266  | test_create_two_games_same_image_deduplicates            | use app_db for both creates              |
| 346  | test_update_game_replaces_thumbnail                      | use app_db for create + update           |
| 438  | test_delete_game_releases_images                         | use app_db for create + delete           |
| 516  | test_delete_shared_image_keeps_image_until_all_refs_gone | use app_db for all creates + deletes     |
| 623  | test_clone_game_increments_image_refcounts               | use app_db for create + clone            |
| 746  | test_delete_game_removes_row_from_db                     | use app_db for create + delete           |
| 814  | test_delete_game_cascades_participants_gone              | use app_db for create + delete           |
| 890  | test_delete_game_with_participant_succeeds               | setup via admin_db already correct; skip |
| 985  | test_delete_game_no_images_succeeds                      | use app_db for create + delete           |
| 1057 | test_delete_game_shared_image_persists                   | use app_db for both creates + delete     |
| 1141 | test_delete_game_status_schedules_removed                | use app_db for create + delete           |

Each test that is converted needs `app_db` added to its parameter list if not already present.
The `guild_id` for the RLS context (`set_config('app.current_guild_ids', ...)`) is already
available in every test via `create_guild()["id"]`.

This is a "retrofitting tests for correct code" scenario per the TDD instructions: no stubs
and no xfail markers are needed; the tests should pass immediately after conversion because
the production code is correct — it was just never exercised under RLS.

- **Files**:
  - `tests/integration/services/api/services/test_game_image_integration.py` - all 12 defective tests
- **Success**:
  - All 12 affected tests use `app_db` (with RLS context set) for the operation under test
  - `test_delete_game_with_participant_succeeds` is verified correct (no change needed)
  - Running `scripts/run-integration-tests.sh tests/integration/services/api/services/test_game_image_integration.py` passes all 13 tests
- **Research References**:
  - #file:../research/20260427-01-integration-tests-admin-db-rls-bypass-research.md (Lines 64-128) - Affected test table and defect details
  - #file:../research/20260427-01-integration-tests-admin-db-rls-bypass-research.md (Lines 144-166) - Correct split pattern for setup vs exercise vs verify
- **Dependencies**:
  - `app_db` fixture already exists in `tests/conftest.py` (lines 163-315); no new fixtures required

## Dependencies

- Integration test environment (PostgreSQL with RLS enabled) via `scripts/run-integration-tests.sh`
- `app_db` fixture in `tests/conftest.py`

## Success Criteria

- All `GameService` calls in `test_game_image_integration.py` that perform the operation under
  test use `app_db` with `set_config('app.current_guild_ids', ...)` called before the service call
- All 13 tests in `test_game_image_integration.py` pass under the integration test suite

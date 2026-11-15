<!-- markdownlint-disable-file -->

# Changes: Integration Tests Using admin_db Bypass RLS

## Status: Complete

## Phase 1: Convert GameService Instances to Use app_db with RLS Context

### Task 1.1 — Complete

#### Modified

- `tests/integration/services/api/services/test_game_image_integration.py` — converted 12 `GameService(db=admin_db, ...)` operation calls to `GameService(db=app_db, ...)` with `set_config('app.current_guild_ids', ...)` set before each test's service operations; added `app_db: AsyncSession` parameter to all 12 affected test function signatures; changed all post-service `await admin_db.commit()` calls to `await app_db.commit()`; verification reads retained on `admin_db`; `test_delete_game_with_participant_succeeds` left unchanged (already correctly split)

#### Verified

- All 13 tests in `test_game_image_integration.py` pass under `scripts/run-integration-tests.sh` (exit 0, 13 passed in 1.51s)

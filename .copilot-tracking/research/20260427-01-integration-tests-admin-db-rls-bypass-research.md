<!-- markdownlint-disable-file -->

# Task Research Notes: Integration Tests Using admin_db Bypass RLS

## Research Executed

### File Analysis

- `tests/conftest.py` (lines 154–310)
  - `admin_db` fixture uses `ADMIN_DATABASE_URL` — the PostgreSQL superuser, which has `BYPASSRLS`
  - `app_db` fixture uses `DATABASE_URL` — the app user, which is subject to all RLS policies
  - `bot_db` fixture uses `BOT_DATABASE_URL` — the bot user, which has `BYPASSRLS`

- `shared/database.py` (`get_db_with_user_guilds`, lines 124–175)
  - Production HTTP routes use this dependency, which yields an `app_db`-equivalent session
  - It calls `setup_rls_and_convert_guild_ids()` to set `app.current_guild_ids` before yielding
  - The session is subject to full RLS enforcement

- `services/api/routes/games.py` (`_get_game_service`, lines 101–122)
  - `GameService` in production is always constructed with `db=get_db_with_user_guilds()` — the RLS-enforced session

- `services/api/services/embed_deletion_consumer.py`
  - Uses `get_bypass_db_session()` — the bot user (BYPASSRLS), not the app user
  - This is intentional: the embed consumer is an internal daemon, not a user-initiated request

### Code Search Results

- `db=admin_db` in `tests/integration/**/*.py`
  - 18 matches across two files:
    - `tests/integration/services/api/services/test_game_image_integration.py`: 13 `GameService` instances (lines 137, 201, 271, 353, 447, 527, 636, 761, 831, 909, 1007, 1081, 1167)
    - `tests/integration/test_games_route_guild_isolation.py`: 5 `GameService` instances (lines 136, 169, 208, 255, 291) — all in list/get operations

- `db=app_db` in `tests/integration/**/*.py`
  - 1 match: `test_delete_game_with_participant_succeeds` line 954 — the test fixed in commit 761e1756

### RLS Tables

```sql
-- Tables with ENABLE ROW LEVEL SECURITY:
guild_configurations   -- policy: guild_isolation_configurations
game_sessions          -- policy: guild_isolation_games
game_templates         -- policy: guild_isolation_templates
game_participants      -- policy: guild_isolation_participants
```

All four policies are `FOR ALL` with only a `USING` clause (no explicit `WITH CHECK`).
PostgreSQL applies `USING` as `WITH CHECK` automatically, meaning both reads and writes
are restricted.

### Policy Details

```sql
-- game_sessions and game_templates: direct guild_id check
USING (
    guild_id::text = ANY(
        string_to_array(current_setting('app.current_guild_ids', true), ',')
    )
)

-- game_participants: indirect via join to game_sessions
USING (
    game_session_id IN (
        SELECT id FROM game_sessions
        WHERE guild_id::text = ANY(
            string_to_array(current_setting('app.current_guild_ids', true), ',')
        )
    )
)
```

### Project Conventions

- `admin_db` is the correct fixture for test data setup (INSERT/DELETE raw fixtures)
- `app_db` is the correct fixture for any `GameService` call that mirrors a production HTTP route
- `bot_db` is the correct fixture for any code that runs as a background daemon (embed consumer, scheduler)

## Key Discoveries

### The Defect

Every `GameService` integration test in `test_game_image_integration.py` constructs the service with
`db=admin_db`. Because `admin_db` is the superuser with `BYPASSRLS`, all RLS policies are silently
skipped. The tests cannot detect:

1. Operations that would be blocked by the `USING` clause (e.g. accessing a game from a different guild)
2. Operations that would be blocked by the implicit `WITH CHECK` (e.g. writing a row that doesn't satisfy the guild filter)
3. SQLAlchemy ORM flush behavior that emits SQL blocked by `WITH CHECK` (the exact failure seen in production)

The production bug (`passive_deletes` + RLS) was only caught because an e2e test ran through the
real HTTP route — not because the integration test caught it. The integration test passed falsely.

### Affected Tests

All 13 `GameService(db=admin_db, ...)` instances in `test_game_image_integration.py`:

| Line | Test name                                                  | Operation                               | Risk                              |
| ---- | ---------------------------------------------------------- | --------------------------------------- | --------------------------------- |
| 137  | `test_create_game_stores_image`                            | create + delete                         | Both bypass RLS                   |
| 201  | `test_update_game_replaces_image`                          | create + update + delete                | All bypass RLS                    |
| 271  | `test_update_game_with_same_image`                         | create + update + delete                | All bypass RLS                    |
| 353  | `test_update_game_clears_thumbnail`                        | create + update + delete                | All bypass RLS                    |
| 447  | `test_delete_game_releases_images`                         | create + delete                         | Both bypass RLS                   |
| 527  | `test_delete_shared_image_keeps_image_until_all_refs_gone` | create × 2 + delete × 2                 | All bypass RLS                    |
| 636  | `test_clone_game_increments_image_refcounts`               | create + clone + delete                 | All bypass RLS                    |
| 761  | `test_delete_game_removes_row_from_db`                     | create + delete                         | Both bypass RLS                   |
| 831  | `test_delete_game_cascades_participants_gone`              | create + delete (no participants added) | Vacuous test                      |
| 909  | `test_delete_game_with_participant_succeeds` (setup only)  | create (setup via admin_db)             | Setup only — delete uses app_db ✓ |
| 1007 | `test_delete_game_no_images_succeeds`                      | create + delete                         | Both bypass RLS                   |
| 1081 | `test_delete_game_with_status_schedule_succeeds`           | create + delete                         | Both bypass RLS                   |
| 1167 | `test_delete_game_with_thumbnail_succeeds`                 | create + delete                         | Both bypass RLS                   |

The 5 `db=admin_db` usages in `test_games_route_guild_isolation.py` are list/get operations
that are already parametrized with explicit `app_db` variants — those tests are intentionally
comparing admin vs. app behaviour and are not defective.

### What Failures the Defect Can Mask

Any future bug in `GameService` that:

- Violates the guild_id RLS constraint on `game_sessions` or `game_templates`
- Violates the `game_session_id IN (...)` RLS constraint on `game_participants`
- Produces an ORM flush that emits a SQL statement blocked by `WITH CHECK`

would pass these integration tests and only surface in e2e tests or production.

### Correct Pattern (Established in This Session)

```python
# Setup: use admin_db (BYPASSRLS) to insert fixture data
setup_service = GameService(db=admin_db, ...)
game = await setup_service.create_game(...)
await admin_db.commit()

# Exercise: use app_db (RLS enforced) with guild context set, matching production
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

## Recommended Approach

Convert all `GameService(db=admin_db, ...)` instances in `test_game_image_integration.py` to use
`app_db` for the actual service call, following the split pattern above.

The `guild_id` for the RLS context is already available in all tests from `create_guild()["id"]`.

A shared fixture (e.g. `app_db_with_guild_context(guild_id)`) could reduce boilerplate if many
tests need conversion.

## Implementation Guidance

- **Objectives**: Make `GameService` integration tests exercise the same RLS constraints that production does
- **Key Tasks**:
  1. Add a helper fixture or inline the two-line `set_config` call in each test
  2. Replace `GameService(db=admin_db, ...)` with `GameService(db=app_db, ...)` for the operation under test
  3. Keep `admin_db` for fixture setup (INSERT) and verification (SELECT after)
  4. Verify tests still pass after conversion (they should — the code is correct, just untested under RLS)
  5. Consider whether `test_delete_game_cascades_participants_gone` should actually add a participant before deleting
- **Dependencies**: `app_db` fixture already exists in `tests/conftest.py`; no new fixtures required unless a helper is desired
- **Success Criteria**: Every `GameService` call in `test_game_image_integration.py` uses `app_db`, and all tests pass

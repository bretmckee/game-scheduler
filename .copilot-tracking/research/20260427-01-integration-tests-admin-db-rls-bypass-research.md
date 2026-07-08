<!-- markdownlint-disable-file -->

# Task Research Notes: Integration Tests Using admin_db Bypass RLS

## Research Executed

### File Analysis

- `tests/conftest.py` (lines 163–315)
  - `admin_db` fixture uses `ADMIN_DATABASE_URL` — the PostgreSQL superuser, which has `BYPASSRLS`
  - `app_db` fixture uses `DATABASE_URL` — the app user, which is subject to all RLS policies
  - `bot_db` fixture uses `BOT_DATABASE_URL` — the bot user, which has `BYPASSRLS`

- `shared/database.py` (`get_db_with_user_guilds`, lines 122–170)
  - Production HTTP routes use this dependency, which yields an `app_db`-equivalent session
  - It calls `setup_rls_and_convert_guild_ids()` in a temp session to seed the RLS context, then yields a second session where an event listener enforces RLS on every transaction begin
  - The session is subject to full RLS enforcement

- `services/api/routes/games.py` (`_get_game_service`, lines 105–122)
  - `GameService` in production is always constructed with `db=get_db_with_user_guilds()` — the RLS-enforced session

- `services/bot/bot.py` and `services/bot/handlers/participant_drop.py`
  - Both use `get_bypass_db_session()` — the bot user (BYPASSRLS), not the app user
  - This is intentional: bot event handlers and participant-drop logic are internal daemons, not user-initiated HTTP requests

### Code Search Results

- `db=admin_db` in `tests/integration/**/*.py`
  - 18 matches across two files:
    - `tests/integration/services/api/services/test_game_image_integration.py`: 13 `GameService` instances (lines 136, 198, 266, 346, 438, 516, 623, 746, 814, 890, 985, 1057, 1141)
    - `tests/integration/test_games_route_guild_isolation.py`: 5 `GameService` instances (lines 134, 166, 204, 250, 285) — all in list/get operations

- `db=app_db` in `tests/integration/**/*.py`
  - 1 match: `test_delete_game_with_participant_succeeds` line 934 — the test fixed in commit 761e1756

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
- `bot_db` is the correct fixture for any code that runs as a background daemon (bot event handlers, SSE bridge, participant-drop handler)

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
| 136  | `test_create_game_with_thumbnail_stores_image`             | create                                  | Bypasses RLS                      |
| 198  | `test_create_game_with_both_images_stores_both`            | create                                  | Bypasses RLS                      |
| 266  | `test_create_two_games_same_image_deduplicates`            | create × 2                              | Both bypass RLS                   |
| 346  | `test_update_game_replaces_thumbnail`                      | create + update                         | Both bypass RLS                   |
| 438  | `test_delete_game_releases_images`                         | create + delete                         | Both bypass RLS                   |
| 516  | `test_delete_shared_image_keeps_image_until_all_refs_gone` | create × 2 + delete × 2                 | All bypass RLS                    |
| 623  | `test_clone_game_increments_image_refcounts`               | create + clone                          | Both bypass RLS                   |
| 746  | `test_delete_game_removes_row_from_db`                     | create + delete                         | Both bypass RLS                   |
| 814  | `test_delete_game_cascades_participants_gone`              | create + delete (no participants added) | Vacuous test                      |
| 890  | `test_delete_game_with_participant_succeeds` (setup only)  | create (setup via admin_db)             | Setup only — delete uses app_db ✓ |
| 985  | `test_delete_game_no_images_succeeds`                      | create + delete                         | Both bypass RLS                   |
| 1057 | `test_delete_game_shared_image_persists`                   | create × 2 + delete                     | All bypass RLS                    |
| 1141 | `test_delete_game_status_schedules_removed`                | create + delete                         | Both bypass RLS                   |

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

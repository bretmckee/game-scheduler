<!-- markdownlint-disable-file -->

# Task Details: Notify participants when a game's details change

## Research Reference

**Source Research**: #file:../../research/20261108-01-game-time-change-notification-research.md

## Phase 1: Change-notification helper and DM format (TDD)

### Task 1.1: Create stubs for the snapshot, the helper and the DM format

Create `shared/services/game_change_notifications.py` (copyright header per `.github/instructions/copyright-headers.instructions.md`) next to `waitlist_transitions.py`, with stubs that `raise NotImplementedError`:

| Symbol                           | Signature                                                                                                                                         | Purpose                                    |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| `GameNotifySnapshot`             | frozen `@dataclass`: `scheduled_at: datetime`, `expected_duration_minutes: int \| None`, `where: str \| None`, `signup_instructions: str \| None` | Pre-edit values of the four notify fields  |
| `capture_notify_snapshot`        | `(game: GameSession) -> GameNotifySnapshot`                                                                                                       | Called before `_update_game_fields`        |
| `notify_participants_of_changes` | `async (db: AsyncSession, game: GameSession, old: GameNotifySnapshot) -> set[str]`                                                                | Enqueues DMs; returns notified discord IDs |

Add stub `DMFormats.game_updated(game_title: str, changes: list[tuple[str, str, str]], jump_url: str \| None = None) -> str` to `shared/message_formats.py` (`changes` = `(label, old_text, new_text)`).

- **Files**:
  - shared/services/game_change_notifications.py - new module (stubs)
  - shared/message_formats.py - add `DMFormats.game_updated` stub
- **Success**:
  - `uv run mypy shared/ services/` passes; module imports cleanly
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 44, 48-53) - pattern to reuse and notify-field list
- **Dependencies**:
  - None

### Task 1.2: Write xfail unit tests with real assertions

Create `tests/unit/shared/services/test_game_change_notifications.py`, modelled on `tests/unit/shared/services/test_waitlist_transitions.py` (`_make_participant`, `_make_game`, `mock_db` helpers). Mark each test `@pytest.mark.xfail(reason="Function not yet implemented", strict=True)`. Cases:

| #   | Scenario                                                                                        | Expected                                                                                                                       |
| --- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1   | `scheduled_at` changed, 2 confirmed + 1 waitlisted user                                         | 3 `db.add` calls, one `BotActionQueue(action_type="send_dm")` per discord_id, `payload["notification_type"] == "game_updated"` |
| 2   | Each of `expected_duration_minutes`, `where`, `signup_instructions` changed alone (parametrize) | one DM per participant; message lists only that field                                                                          |
| 3   | Two fields changed in one edit                                                                  | still exactly one DM per participant; message lists both                                                                       |
| 4   | No field changed (no-op save)                                                                   | `db.add` not called; returns empty set                                                                                         |
| 5   | Placeholder participant (`user=None`, `display_name` set)                                       | skipped, no DM                                                                                                                 |
| 6   | Only excluded fields differ (e.g. title)                                                        | no DM (title is not in the snapshot)                                                                                           |
| 7   | `capture_notify_snapshot`                                                                       | returns the game's current four values                                                                                         |
| 8   | `DMFormats.game_updated`                                                                        | time rendered as `<t:{unix}:F>` old -> new; includes jump URL when given, omits link when `None`                               |

Time comparison uses the normalized naive-UTC values the model stores; payload carries `game_title` and `game_time_unix` like the waitlist DMs.

- **Files**:
  - tests/unit/shared/services/test_game_change_notifications.py - new tests
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_game_change_notifications.py -v` shows all xfailed
  - Assertions follow `.github/instructions/unit-tests.instructions.md` (call-verification, no coverage theater)
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 49-53) - one DM per participant per edit, confirmed and waitlisted, no-op saves excluded
- **Dependencies**:
  - Task 1.1

### Task 1.3: Implement helper and format; remove xfail markers

- `capture_notify_snapshot`: copy the four fields.
- `notify_participants_of_changes`: build `changes` for each differing field. Labels: reuse `_FREE_TEXT_FIELD_LABELS` style ("Time", "Duration", "Location", "Signup Instructions"). Render time as Discord `<t:{int(dt.replace(tzinfo=UTC).timestamp())}:F>`, duration as minutes (`"90 min"`, `"not set"` for `None`), text `None`/empty as `"(none)"`. Return early with `set()` when nothing changed. One `BotActionQueue` per participant with a `user` (both confirmed and waitlisted), `payload` keys `notification_type`, `game_title`, `game_time_unix`, `message`. Log each enqueue like `waitlist_transitions`.
- Jump URL: move `_build_jump_url` from `waitlist_transitions.py` to a shared spot (or import it) rather than duplicating; if moved, update `waitlist_transitions.py` and its tests in this same task.
- `DMFormats.game_updated`: header `"📝 The host updated **{title}**:"`, one line per change `"• **{label}**: {old} → {new}"`, then `[View game in Discord]({jump_url})` when present.
- Remove only the xfail decorators.

- **Files**:
  - shared/services/game_change_notifications.py - implementation
  - shared/message_formats.py - implementation
  - shared/services/waitlist_transitions.py - only if `_build_jump_url` is moved
- **Success**:
  - All Task 1.2 tests pass unchanged except for decorator removal
  - Phase gate: `uv run pytest tests/unit`, `uv run mypy shared/ services/`
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 44, 49) - send_dm pattern, `<t:...>` timestamps, game-message link
- **Dependencies**:
  - Task 1.2

## Phase 2: Wire the helper into `update_game` (TDD bug fix)

### Task 2.1: Write xfail regression tests for `GameService.update_game`

Add tests to `tests/unit/services/api/services/test_games_service.py` (follow existing `update_game` fixtures there and in `test_games_promotion.py`), marked `@pytest.mark.xfail(reason="Bug: participants not notified when game details change", strict=True)`:

| Scenario                                                            | Expected                                                                                                 |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Announced game (`message_id` set), `scheduled_at` changed           | `notify_participants_of_changes` awaited once with the reloaded game and a snapshot holding the OLD time |
| Unannounced game (`message_id is None`) with `scheduled_at` changed | not called                                                                                               |
| `clear_post_at` announce-now path                                   | not called                                                                                               |

Patch `shared.services.game_change_notifications.notify_participants_of_changes` at its import site in `services.api.services.games`.

- **Files**:
  - tests/unit/services/api/services/test_games_service.py - new xfail tests
- **Success**:
  - New tests show as xfailed; existing tests unaffected
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 9-12, 48-49) - update_game ordering, old value not captured today
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Call the helper from `update_game`; remove xfail markers

In `services/api/services/games.py` `update_game` (L2122):

1. Call `old_notify = game_change_notifications.capture_notify_snapshot(game)` next to `_capture_old_state` (L2180-2184), before `_update_game_fields`. Do NOT change `_capture_old_state`'s return type (keeps callers untouched).
2. Compare after the reload (L2219-2225) so values reflect channel/mention/emoji resolution of `where` and `signup_instructions`.
3. Inside the existing `if game.message_id is not None:` block (L2249), await `notify_participants_of_changes(self.db, game, old_notify)` before `_publish_game_updated`. Same transaction; no commit (see `.github/instructions/fastapi-transaction-patterns.instructions.md`).
4. Remove only the xfail decorators from Task 2.1 tests.

- **Files**:
  - services/api/services/games.py - capture snapshot and call helper
  - tests/unit/services/api/services/test_games_service.py - remove xfail markers
- **Success**:
  - Phase gate: `uv run pytest tests/unit`, `uv run mypy shared/ services/`
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 48-53) - capture point, announced-only, exclusions
- **Dependencies**:
  - Task 2.1

## Phase 3: Integration test through the API and bot queue

### Task 3.1: Add integration test (retrofit; no xfail)

Create `tests/integration/test_game_change_notification.py`, modelled on `tests/integration/test_leave_game_promotion.py` (`_make_context`, `_insert_participant`, `seed_redis_cache` before `create_authenticated_client`). Mark the game announced with `UPDATE game_sessions SET message_id = '...' WHERE id = :id` via `admin_db_sync`. Cases:

- `PUT /api/v1/games/{id}` with a new `scheduled_at` -> one `send_dm` row with `notification_type = 'game_updated'` per participant (confirmed and waitlisted); message contains new `<t:...>` value.
- `PUT` resubmitting the same `scheduled_at` -> zero `game_updated` rows.
- `PUT` changing only `title` -> zero `game_updated` rows.

- **Files**:
  - tests/integration/test_game_change_notification.py - new tests
- **Success**:
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` green (see `.github/instructions/test-execution.instructions.md`)
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 63, 65) - integration test with bot queue; success criteria
- **Dependencies**:
  - Phase 2 complete

## Phase 4: E2E test of DM delivery through the bot

### Task 4.1: Add the `game_updated` DM predicate and e2e `DMType`

- `shared/message_formats.py`: add `DMPredicates.game_updated(game_title)` next to the existing predicates; match on the `DMFormats.game_updated` header text AND the title, so it cannot match join/promotion DMs for the same game.
- `tests/e2e/helpers/discord.py`: add `DMType.GAME_UPDATED = "game_updated"` to `DMType` (L39) and register it in the `predicates` map in `wait_for_recent_dm` (L792).
- Add a unit test for the predicate in `tests/unit/shared/test_message_formats.py` (retrofit; no xfail): matches a `game_updated` message, rejects a `promotion` message for the same title.

- **Files**:
  - shared/message_formats.py - `DMPredicates.game_updated`
  - tests/e2e/helpers/discord.py - `DMType.GAME_UPDATED` and mapping
  - tests/unit/shared/test_message_formats.py - predicate tests
- **Success**:
  - `uv run pytest tests/unit`, `uv run mypy shared/ services/` pass
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 17-18, 44) - existing send_dm bot path; DM pattern
- **Dependencies**:
  - Phase 3 complete

### Task 4.2: Add e2e test for the change DM (retrofit; no xfail)

Add `test_game_time_change_sends_dm` to `tests/e2e/test_game_update.py`, following `test_leave_promotes_waitlisted_participant_sends_dm` in `tests/e2e/test_waitlist_promotion.py` (L393):

1. Look up guild and default template via `admin_db`; create the game with `authenticated_admin_client`, `initial_participants` = `[<@{discord_user_id}>]`, unique title `f"E2E Time Change {uuid4().hex[:8]}"`.
2. `wait_for_game_message_id`, then `main_bot_helper.wait_for_message` so the game is announced.
3. `PUT /api/v1/games/{id}` with `scheduled_at` moved by one hour; assert 200.
4. `main_bot_helper.wait_for_recent_dm(user_id=discord_user_id, game_title=..., dm_type=DMType.GAME_UPDATED, timeout=test_timeouts[TimeoutType.DM_IMMEDIATE])`.
5. Assert the DM contains the new `<t:{unix}:F>`, the old one, and the jump URL `https://discord.com/channels/{guild}/{channel}/{message_id}`.

Negative cases (no-op save, title-only edit) stay in the Phase 3 integration test; proving absence in e2e needs a timeout wait and is flaky.

- **Files**:
  - tests/e2e/test_game_update.py - new test
- **Success**:
  - `scripts/run-e2e-tests.sh |& tee output-e2e.txt` green (see `.github/instructions/test-execution.instructions.md`)
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 49, 65) - DM content; success criteria
- **Dependencies**:
  - Task 4.1

## Phase 5: Update the player guide

### Task 5.1: Describe the shipped behavior in docs/PLAYER-GUIDE.md

- "Game Updates" (L161-166): replace the "may receive" / "major changes always" bullets with the exact rule: one DM per edit when time, expected duration, location or signup instructions change, listing old -> new; title, description and rewards edits send no DM; max-players/signup-method changes still send existing promotion/demotion DMs.
- "What if the game time changes?" (L219-223): keep existing bullets; add that waitlisted players are notified too.
- Must land in the same PR as Phases 1-4; never merge ahead of the code.

- **Files**:
  - docs/PLAYER-GUIDE.md - two sections
- **Success**:
  - Wording matches implemented behavior; markdown per `.github/instructions/markdown.instructions.md`
- **Research References**:
  - #file:../../research/20261108-01-game-time-change-notification-research.md (Lines 67-73) - documentation requirements
- **Dependencies**:
  - Phase 4 complete

## Dependencies

- Existing `BotActionQueue` `send_dm` handler in services/bot/bot_action_listener.py (no bot changes)
- pytest, mypy, integration and e2e test harnesses (e2e needs the Discord test guild and users)

## Success Criteria

- Changing any notify field on an announced game yields exactly one DM per participant (confirmed and waitlisted)
- No-op saves, unannounced games and excluded-field edits yield no DM
- docs/PLAYER-GUIDE.md matches shipped behavior

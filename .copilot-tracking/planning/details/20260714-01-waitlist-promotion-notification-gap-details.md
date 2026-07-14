<!-- markdownlint-disable-file -->

# Task Details: Waitlist Promotion DM on Leave

## Research Reference

**Source Research**: #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md

## Phase 1: Extract shared waitlist transition detection

### Task 1.1: Create `detect_and_notify_transitions` stub in `shared/services/waitlist_transitions.py`

Create a new module-level async function that will hold the diff-and-notify logic currently
duplicated inside `GameService` (`_detect_and_notify_transitions`, `_notify_promoted_users`,
`_notify_demoted_users`, `_publish_promotion_notification`). Model the module on the existing
plain-function style of `shared/services/game_cancellation.py` (module-level `async def`, no
class, takes `db: AsyncSession` plus domain objects, does not commit).

Signature:

```python
async def detect_and_notify_transitions(
    db: AsyncSession,
    game: GameSession,
    old_partitioned: PartitionedParticipants,
) -> tuple[set[str], set[str]]:
    """Detect waitlist promotions/demotions and enqueue send_dm notifications.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError("detect_and_notify_transitions not yet implemented")
```

- **Files**:
  - `shared/services/waitlist_transitions.py` - new file, stub function with full type hints and docstring
- **Success**:
  - Module imports cleanly; `mypy shared/` passes on the new stub
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 58-74) - Implementation Patterns: the 4-step capture/mutate/reload/detect pattern being extracted
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 77-95) - Current (correct) promotion trigger code to base the extraction on
- **Dependencies**:
  - None (first task)

### Task 1.2: Write unit tests with real assertions marked `xfail`

Create `tests/unit/shared/services/test_waitlist_transitions.py` following the mock-`AsyncSession`
style used in `tests/unit/api/services/test_games.py` (see `mock_db` fixture pattern). Build
`GameSession`/`GameParticipant` test doubles (or real lightweight instances) and a
`PartitionedParticipants` old-state fixture directly via `partition_participants`.

Required test cases (all `@pytest.mark.xfail(reason="Function not yet implemented", strict=True)`):

- `test_promotion_enqueues_send_dm_and_returns_promoted_id` - a participant in `game.participants`
  moves from the old-state overflow set into the new confirmed set (e.g. `max_players=1`, old
  partitioned has a confirmed + an overflow participant, `game.participants` now only has the
  formerly-overflow one). Assert `db.add` was called once with a `BotActionQueue` whose
  `action_type == "send_dm"`, `payload["notification_type"] == "waitlist_promotion"`, and
  `discord_id` matches the promoted user; assert the returned `promoted_discord_ids` set contains
  that discord ID.
- `test_demotion_enqueues_send_dm_and_returns_demoted_id` - mirrors the above for a
  confirmed-to-overflow transition, asserting `notification_type == "waitlist_demotion"`.
- `test_no_transitions_enqueues_nothing` - old and new partitioned state identical; assert
  `db.add` was not called and both returned sets are empty.
- `test_promotion_without_jump_url_when_message_id_missing` - `game.message_id is None`; assert
  the enqueued DM payload's `message` does not contain a jump URL (matches existing
  `_publish_promotion_notification` behavior at research lines 100-116).

- **Files**:
  - `tests/unit/shared/services/test_waitlist_transitions.py` - new file
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_waitlist_transitions.py -v` shows all 4 tests as `xfailed`
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 96-131) - exact current behavior being preserved (`_publish_promotion_notification`, `_notify_demoted_users` bodies)
- **Dependencies**:
  - Task 1.1 completion

### Task 1.3: Implement and remove `xfail` markers

Move the bodies of `GameService._detect_and_notify_transitions`, `_notify_promoted_users`,
`_notify_demoted_users`, and `_publish_promotion_notification` (`services/api/services/games.py`,
current lines ~1838-1863 and ~2525-2600) into `detect_and_notify_transitions`, adapted to:
compute `new_partitioned` via `partition_participants`, diff via `old_partitioned.cleared_waitlist`
/`entered_waitlist` called on the new state (matches existing call convention
`new_partitioned.cleared_waitlist(old_partitioned)`), build DMs via `DMFormats.promotion`/
`waitlist_demotion`, `db.add(BotActionQueue(...))` for each affected discord ID, and return
`(promoted_discord_ids, demoted_discord_ids)`.

- **Files**:
  - `shared/services/waitlist_transitions.py` - full implementation
  - `tests/unit/shared/services/test_waitlist_transitions.py` - remove `xfail` markers only, no assertion changes
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_waitlist_transitions.py -v` shows all tests passing
  - `uv run mypy shared/` passes
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 77-131) - source logic being moved
- **Dependencies**:
  - Task 1.2 completion

### Task 1.4: Refactor and add edge-case tests

Add a test for multiple simultaneous promotions (`max_players` increased by 2 with 2 waitlisted
users) asserting both discord IDs appear in the returned set and two separate `BotActionQueue`
rows were added. Run the full unit suite for the module.

- **Files**:
  - `tests/unit/shared/services/test_waitlist_transitions.py` - add edge-case test
- **Success**:
  - `uv run pytest tests/unit` passes with no regressions
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 58-74)
- **Dependencies**:
  - Task 1.3 completion

## Phase 2: Refactor `update_game` to use the shared transition function

### Task 2.1: Delegate `GameService` promotion/demotion methods to the shared function and delete the now-dead private methods

Replace the body of `GameService._detect_and_notify_transitions` with a call to
`waitlist_transitions.detect_and_notify_transitions(self.db, game, old_partitioned)`. Delete
`GameService._notify_promoted_users`, `_notify_demoted_users`, and `_publish_promotion_notification`
entirely (dead code after delegation) — per the code-removal ordering rule, this deletion happens
in the same task as wiring the new call, not a later phase.

- **Files**:
  - `services/api/services/games.py` - replace `_detect_and_notify_transitions` body; delete `_notify_promoted_users`, `_notify_demoted_users`, `_publish_promotion_notification`; add `from shared.services import waitlist_transitions` import
- **Success**:
  - `grep -n "_notify_promoted_users\|_notify_demoted_users\|_publish_promotion_notification" services/api/services/games.py` returns no matches
  - No behavior change: `update_game`'s public contract is unchanged
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 173-174) - "also refactor `_detect_and_notify_transitions`... to call the promotion/demotion half of the same shared module"
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Verify no regression in existing promotion/demotion tests

This is a behavior-preserving refactor of already-correct, already-tested code — no new `xfail`
cycle applies. Run the existing test suites that exercise `update_game`'s promotion/demotion path
and fix any test that referenced the deleted private methods directly (e.g. via `patch(...)` on
`GameService._notify_promoted_users`).

- **Files**:
  - `tests/unit/api/services/test_games.py` - update any test patching the removed private methods
  - `tests/integration/test_player_removed_queue.py` - must continue to pass unmodified (`test_removing_confirmed_player_enqueues_waitlist_promotion_dm`)
- **Success**:
  - `uv run pytest tests/unit` passes
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows `test_player_removed_queue.py` passing (follow #file:../../.github/instructions/test-execution.instructions.md for capture)
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 33-34) - existing integration test this must not break
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Create shared leave-game core

### Task 3.1: Create `leave_game_and_notify` stub in `shared/services/leave_game.py`

Signature:

```python
async def leave_game_and_notify(
    db: AsyncSession,
    game: GameSession,
    participant: GameParticipant,
) -> GameSession:
    """Remove a participant, detect waitlist transitions, and notify affected users.

    Precondition: `game` must have `participants` (with `.user`), `host`, `guild`, and
    `channel` relationships already loaded (e.g. via GameService.get_game()'s selectinload
    chain). Does not commit; caller must commit.

    Returns:
        The game with its `participants` relationship refreshed after the delete.

    Raises:
        NotImplementedError: Not yet implemented.
    """
    raise NotImplementedError("leave_game_and_notify not yet implemented")
```

- **Files**:
  - `shared/services/leave_game.py` - new file, stub function
- **Success**:
  - Module imports cleanly from both a `services/api/` and a `services/bot/` context (no
    `services.api.*` imports); `mypy shared/` passes
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 164-172) - deployment constraint and shared-module contract
- **Dependencies**:
  - Phase 1 completion (imports `waitlist_transitions.detect_and_notify_transitions`)

### Task 3.2: Write unit tests with real assertions marked `xfail`

Create `tests/unit/shared/services/test_leave_game.py`, same mock-`AsyncSession` style as Task 1.2.

Required test cases (all `@pytest.mark.xfail(reason="Function not yet implemented", strict=True)`):

- `test_leave_deletes_the_participant` - assert `db.delete` called once with the passed
  `participant`.
- `test_confirmed_leave_promotes_waitlisted_participant` - `max_players=1`,
  `HOST_SELECTED_WITH_WAITLIST`, old state has a confirmed leaver + a waitlisted user; after
  delete the waitlisted user becomes confirmed. Assert a `BotActionQueue` with
  `notification_type == "waitlist_promotion"` and the waitlisted user's `discord_id` was added.
- `test_host_added_leave_enqueues_dropout_dm_to_host` - `participant.position_type ==
ParticipantType.HOST_ADDED`, `game.host.discord_id` set. Assert a `BotActionQueue` row with
  `notification_type == "host_added_dropout"` and `discord_id == game.host.discord_id` was added.
- `test_self_added_leave_with_empty_waitlist_enqueues_nothing` - no waitlisted users, not
  `HOST_ADDED`. Assert `db.add` was not called at all.
- `test_no_host_dropout_dm_when_host_missing` - `HOST_ADDED` leaver but `game.host is None`.
  Assert no `host_added_dropout` `BotActionQueue` row was added (existing guard from
  `services/api/services/games.py::leave_game`'s `if position_type == HOST_ADDED and
host_discord_id:` check).

- **Files**:
  - `tests/unit/shared/services/test_leave_game.py` - new file
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_leave_game.py -v` shows all 5 tests as `xfailed`
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 97-131) - current buggy `leave_game` and bot-handler bodies whose correct replacement behavior these tests assert
- **Dependencies**:
  - Task 3.1 completion

### Task 3.3: Implement and remove `xfail` markers

Implement `leave_game_and_notify`:

1. Capture `position_type = participant.position_type`,
   `host_discord_id = game.host.discord_id if game.host else None`,
   `old_partitioned = partition_participants(game.participants, resolve_max_players(game.max_players), signup_method=game.signup_method)`
   — all before the delete.
2. `await db.delete(participant)`; `await db.flush()`;
   `await db.refresh(game, ["participants"])` to pick up the post-delete collection (matches the
   `await self.db.refresh(game, ["participants"])` call already used in `update_game`; verify via
   the unit tests whether a full reselect is also needed for `.user` on surviving participants —
   it should not be, since no new participants are added by a leave).
3. `promoted_ids, demoted_ids = await waitlist_transitions.detect_and_notify_transitions(db, game, old_partitioned)`.
4. If `position_type == ParticipantType.HOST_ADDED and host_discord_id`: build the DM via
   `DMFormats.host_added_dropout(...)` (same fields as the current
   `services/api/services/games.py::leave_game` block) and `db.add(BotActionQueue(action_type="send_dm", ..., payload={"notification_type": "host_added_dropout", ...}))`.
5. `return game`.

- **Files**:
  - `shared/services/leave_game.py` - full implementation
  - `tests/unit/shared/services/test_leave_game.py` - remove `xfail` markers only, no assertion changes
- **Success**:
  - `uv run pytest tests/unit/shared/services/test_leave_game.py -v` shows all tests passing
  - `uv run mypy shared/` passes
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 108-117) - the host_added_dropout DM fields to reuse verbatim
- **Dependencies**:
  - Task 3.2 completion

### Task 3.4: Refactor and add edge-case tests

Add a test where the leaver is both the only confirmed HOST_SELECTED participant and there are 2
waitlisted users but `max_players` only frees 1 slot — assert exactly one promotion DM is enqueued
(not both). Run the full unit suite.

- **Files**:
  - `tests/unit/shared/services/test_leave_game.py` - add edge-case test
- **Success**:
  - `uv run pytest tests/unit` passes with no regressions
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 148-158) - Technical Requirements
- **Dependencies**:
  - Task 3.3 completion

## Phase 4: Wire the API leave path (bug fix)

### Task 4.1: Write `xfail` regression test proving the gap

Create `tests/integration/test_leave_game_promotion.py`, mirroring the proven pattern in
`tests/integration/test_player_removed_queue.py::test_removing_confirmed_player_enqueues_waitlist_promotion_dm`
(same `_make_context`/`_insert_participant`-style helpers, `create_authenticated_client`,
`admin_db_sync`), but driving the **leave** route instead of the update route:

- `test_confirmed_leave_via_api_promotes_waitlisted_participant` - create a
  `HOST_SELECTED_WITH_WAITLIST` game with `max_players=1`, insert a confirmed participant and a
  waitlisted participant, call `client.post(f"/api/v1/games/{game_id}/leave")` authenticated as
  the confirmed participant, then query `bot_action_queue` for a `waitlist_promotion` row
  targeting the waitlisted user's `discord_id`.

Mark with `@pytest.mark.xfail(reason="leave_game never calls promotion detection", strict=True)`.
Run it to confirm it shows as `xfailed` (proves the test actually detects the bug).

- **Files**:
  - `tests/integration/test_leave_game_promotion.py` - new file
- **Success**:
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows the new test as `xfailed` (follow #file:../../.github/instructions/test-execution.instructions.md for output capture)
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 156, 176-177) - HTTP leave route reachability and the exact assertion pattern to mirror
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Fix `GameService.leave_game` and remove the `xfail` marker

In `services/api/services/games.py::leave_game`, replace the inline
`await self.db.delete(participant)` + `HOST_ADDED` block (current lines ~2440-2453) with:

```python
game = await leave_game_and_notify(self.db, game, participant)
```

(placed where the current delete+reload+HOST_ADDED block sits; `game` at this point is already
fully loaded via `self.get_game(game_id)` at function entry, so no extra query is needed before
the call). Keep the existing validation (game found, not completed, user found, participant
found) and the `await self._publish_game_updated(game)` call using the returned `game`. Remove
the `xfail` marker from the Task 4.1 test — no assertion changes.

- **Files**:
  - `services/api/services/games.py` - `leave_game` method; add `from shared.services.leave_game import leave_game_and_notify` import
  - `tests/integration/test_leave_game_promotion.py` - remove `xfail` marker only
- **Success**:
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows the test passing
  - `uv run pytest tests/unit tests/unit/api/services/test_games.py -v` — existing `TestLeaveGame` tests (not-found, completed, user-not-found, reload-failure, host-added-dropout) all still pass unmodified
  - `uv run mypy shared/ services/` passes
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 97-117) - exact current buggy code being replaced
- **Dependencies**:
  - Task 4.1 completion (xfailed regression test must exist first)

## Phase 5: Wire the bot leave path (bug fix + delivery unification)

### Task 5.1: Write `xfail` regression tests and update the host-added-dropout tests that change delivery mechanism

**New regression tests** (both `xfail(strict=True)`, proving the promotion gap on this transport):

- Integration: add `test_confirmed_leave_via_handler_promotes_waitlisted_participant` to
  `tests/integration/test_leave_game.py`, following the existing real-DB pattern in that file
  (`_insert_participant`, `handle_leave_game(interaction, game_id)` via `_patch_db()`/
  `BotAsyncSessionLocal`), asserting a `waitlist_promotion` row appears in `bot_action_queue`.
- Unit: add a promotion-on-leave case to `tests/unit/bot/handlers/test_leave_game_handler.py`
  using the `_make_mock_db` side_effect pattern, extended with the additional mocked `execute`
  calls the new `leave_game_and_notify` call will require (determine the exact count by running
  the test and adjusting the `side_effect` list to match actual call order — do not guess ahead).

**Required same-phase updates** (delivery mechanism changes from direct `discord.Client.send()` to
`BotActionQueue`, so these existing tests' assertions must change — this is not a new xfail cycle,
it is updating already-passing tests to match the new, intentionally different behavior):

- `tests/unit/bot/handlers/test_leave_game_handler.py::test_host_added_leave_sends_dm_to_host` -
  change assertion from `interaction.client.get_user(...).send.assert_called_once_with(...)` to
  asserting a `BotActionQueue(action_type="send_dm", ...)` was added to the mock db session with
  `payload["notification_type"] == "host_added_dropout"`.
- `tests/unit/bot/handlers/test_leave_game_handler.py::test_host_added_leave_no_dm_when_host_not_in_cache` -
  this test's premise (`bot.get_user(id) is None` suppresses the DM) no longer applies once
  delivery goes through `BotActionQueue` instead of a live gateway lookup; rewrite it to assert
  the DM is enqueued regardless of gateway cache state, or delete it if no longer meaningful —
  confirm which by checking whether `leave_game_and_notify` needs `game.host` (DB relationship)
  rather than `interaction.client.get_user` (gateway cache) to build the notification.
- `tests/integration/test_leave_game.py::test_host_added_leave_sends_dm_to_host` - same
  BotActionQueue-based assertion change as the unit test above.

- **Files**:
  - `tests/integration/test_leave_game.py` - new promotion test; update `test_host_added_leave_sends_dm_to_host`
  - `tests/unit/bot/handlers/test_leave_game_handler.py` - new promotion test; update/rewrite the two host-added-dropout tests listed above
- **Success**:
  - `uv run pytest tests/unit/bot/handlers/test_leave_game_handler.py -v` shows the new promotion test as `xfailed` and the rewritten host-added-dropout tests reflecting the target (post-fix) behavior
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows the new integration promotion test as `xfailed`
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 154) - the existing host_added_dropout delivery-mechanism divergence being removed
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 119-131) - current bot-handler buggy/divergent code
- **Dependencies**:
  - Phase 3 completion

### Task 5.2: Fix `handle_leave_game` and remove the `xfail` markers

In `services/bot/handlers/leave_game.py`:

1. Add `selectinload(GameSession.participants).selectinload(GameParticipant.user)` to the query in
   `_validate_leave_game` (alongside the existing `guild`/`host`/`channel` selectinloads) so
   `game.participants` is populated before the delete.
2. Replace `await db.delete(participant)` plus the later
   `await _notify_host_if_host_added(interaction, game, position_type)` call with:
   `game = await leave_game_and_notify(db, game, participant)` (placed where the delete currently
   happens, before `upsert_message_refresh_and_notify`/`db.commit()`).
3. Delete the now-unused `_notify_host_if_host_added` function entirely.
4. Remove the `xfail` markers from the Task 5.1 tests — no assertion changes beyond what Task 5.1
   already updated for the delivery-mechanism change.

- **Files**:
  - `services/bot/handlers/leave_game.py` - `_validate_leave_game`, `handle_leave_game`; delete `_notify_host_if_host_added`; add `from shared.services.leave_game import leave_game_and_notify` import; remove now-unused `DMFormats` import if nothing else in the file uses it
  - `tests/integration/test_leave_game.py` - remove `xfail` marker only
  - `tests/unit/bot/handlers/test_leave_game_handler.py` - remove `xfail` marker only
- **Success**:
  - `uv run pytest tests/unit/bot/handlers/test_leave_game_handler.py -v` all passing
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` shows `tests/integration/test_leave_game.py` fully passing
  - `uv run mypy shared/ services/` passes
  - `grep -n "_notify_host_if_host_added" services/bot/handlers/leave_game.py` returns no matches
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 151, 175) - bot handler already has a DB session in scope; this is the actual convergence point between the two transports
- **Dependencies**:
  - Task 5.1 completion (xfailed regression tests must exist first)

## Phase 6: E2E coverage for leave-triggers-promotion DM delivery

### Task 6.1: Add e2e test combining the leave path with promotion-DM verification

TDD does not apply — this is e2e coverage added after the implementation exists (per
#file:../../.github/instructions/test-driven-development.instructions.md, "E2E Tests (TDD NOT
Required)"). No `xfail` marker; write the assertion and run it immediately.

Add `test_leave_promotes_waitlisted_participant_sends_dm` to `tests/e2e/test_waitlist_promotion.py`
(or a new file, matching whichever the existing file's fixture/parametrization style makes
cleaner), combining:

- Game setup: `max_players=1`, Player A (a second bot account) confirmed, the real test user
  (`discord_user_id`) waitlisted — same setup as
  `test_waitlist_promotion.py::test_promotion_drag_delivers_promotion_dm`.
- Trigger: `authenticated_player_a_client.post(f"/api/v1/games/{game_id}/leave")` — same call
  pattern as `tests/e2e/test_host_added_dropout_notification.py::test_host_added_dropout_sends_dm_to_host`.
- Verification: `main_bot_helper.wait_for_recent_dm(user_id=discord_user_id, dm_type=DMType.PROMOTION, ...)`.

- **Files**:
  - `tests/e2e/test_waitlist_promotion.py` (or new file) - new e2e test
- **Success**:
  - `scripts/run-e2e-tests.sh |& tee output-e2e.txt` shows the new test passing (follow #file:../../.github/instructions/test-execution.instructions.md for output capture)
- **Research References**:
  - #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md (Lines 180-191) - full E2E feasibility analysis and the exact fixtures/helpers to combine
- **Dependencies**:
  - Phase 4 completion (this test only covers the API leave path, per research's caveat that the
    Discord-button path cannot be driven e2e at all — line 191)

## Dependencies

- `shared/utils/participant_sorting.py` (existing, unchanged)
- `shared/message_formats.py::DMFormats` (existing, unchanged)
- `shared/models/bot_action_queue.py::BotActionQueue` (existing, unchanged)
- `uv run pytest`, `uv run mypy`, `scripts/run-integration-tests.sh`, `scripts/run-e2e-tests.sh`

## Success Criteria

- All 6 phases complete with all phase-completion gates green.
- `waitlist_promotion` DMs fire on both leave transports, proven by unit, integration, and e2e tests.
- Zero duplicated partition/diff/notify logic between `update_game`, the API leave path, and the bot leave path.
- `host_added_dropout` delivery is unified on `BotActionQueue` for both transports.

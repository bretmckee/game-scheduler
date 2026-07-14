# Changes: Waitlist Promotion DM on Leave

## Plan Reference

[Plan](../planning/plans/20260714-01-waitlist-promotion-notification-gap.plan.md)

---

## Phase 1: Extract shared waitlist transition detection

### Added

- `shared/services/waitlist_transitions.py` — New module holding `detect_and_notify_transitions(db, game, old_partitioned)`, extracted from `GameService`'s promotion/demotion notification logic. Partitions the current participant state, diffs against a previously captured `old_partitioned` state via `cleared_waitlist`/`entered_waitlist`, and enqueues `BotActionQueue(action_type="send_dm")` rows for `waitlist_promotion`/`waitlist_demotion` notifications. Returns `(promoted_discord_ids, demoted_discord_ids)`.
- `tests/unit/shared/services/test_waitlist_transitions.py` — New unit test suite (5 tests): promotion enqueues send_dm and returns promoted id, demotion enqueues send_dm and returns demoted id, no transitions enqueues nothing, promotion omits jump URL when `message_id` is missing, multiple simultaneous promotions enqueue one row per promoted user.

### Notes

- `GameService._detect_and_notify_transitions`/`_notify_promoted_users`/`_notify_demoted_users`/`_publish_promotion_notification` in `services/api/services/games.py` still contain the original (now duplicated) implementation — Phase 2 will delegate them to this new shared module and delete the dead private methods.

---

## Phase 2: Refactor `update_game` to use the shared transition function

### Modified

- `services/api/services/games.py` — `_detect_and_notify_transitions` body replaced with a single delegating call to `waitlist_transitions.detect_and_notify_transitions(self.db, game, old_partitioned)`; deleted the now-dead `_notify_promoted_users`, `_notify_demoted_users`, and `_publish_promotion_notification` methods; added `from shared.services import waitlist_transitions` import. No behavior change — `update_game`'s public contract is unchanged.
- `tests/unit/services/api/services/test_games_promotion.py` — `test_promotion_when_participant_removed` no longer patches the deleted `_notify_promoted_users` method; removed `test_detect_transitions_notifies_demoted_users` (duplicated coverage of the still-passing `test_detect_transitions_sends_demotion_dm`, which exercises the same path via real `BotActionQueue` assertions instead of mocking a now-deleted method).
- `tests/unit/services/api/services/test_games_service.py` — `test_detect_and_notify_promotions_with_promotions`/`test_detect_and_notify_promotions_no_promotions` rewritten to assert on real `mock_db.add` calls instead of patching the deleted `_notify_promoted_users` method; added `scheduled_at` to the test `GameSession` fixture since the notification path is now actually exercised.
- `tests/unit/api/services/test_games.py` — removed `TestNotifyDemotedUsers` (tested the now-deleted `_notify_demoted_users` method directly; equivalent coverage lives in `tests/unit/shared/services/test_waitlist_transitions.py`).

### Verified

- `uv run pytest tests/unit` — 2345 passed (net -2 vs. Phase 1's 2347: two tests removed for testing now-deleted private methods, no coverage lost)
- `uv run mypy shared/ services/` — no issues
- `scripts/run-integration-tests.sh tests/integration/test_player_removed_queue.py tests/integration/test_leave_game.py` — 9 passed, confirming `test_removing_confirmed_player_enqueues_waitlist_promotion_dm` still passes unmodified

---

## Phase 3: Create shared leave-game core

### Added

- `shared/services/leave_game.py` — New module holding `leave_game_and_notify(db, game, participant)`: captures `position_type`/`host_discord_id`/`old_partitioned` before delete, deletes the participant, flushes, refreshes `game.participants`, delegates promotion/demotion detection to `waitlist_transitions.detect_and_notify_transitions`, and (for a `HOST_ADDED` leaver with a host) enqueues a `host_added_dropout` `BotActionQueue` row — same DM fields as the current `services/api/services/games.py::leave_game` block. Depends only on `shared/` (no `services.api.*` import), so it's importable from both Docker images. Does not commit; caller commits.
- `tests/unit/shared/services/test_leave_game_shared.py` — New unit test suite (6 tests): deletes the passed participant, confirmed HOST_ADDED leave promotes a waitlisted HOST_ADDED user, HOST_ADDED leave enqueues a host_added_dropout DM to the host, SELF_ADDED leave with empty waitlist enqueues nothing, no dropout DM when `game.host` is `None`, freeing 1 slot promotes only the next-in-line of 2 waitlisted users. Named `test_leave_game_shared.py` (not `test_leave_game.py`) to avoid a pytest basename collision with the existing `tests/unit/services/bot/handlers/test_leave_game.py` (neither `tests/unit/shared/` nor `tests/unit/services/` has `__init__.py`, so pytest requires unique basenames).

### Verified

- `uv run pytest tests/unit/shared/services/test_leave_game_shared.py -v` — all 6 xfailed before implementation, all 6 passed after
- `uv run pytest tests/unit` — 2351 passed (net +6 vs. Phase 2's 2345)
- `uv run mypy shared/ services/` — no issues

---

## Phase 4: Wire the API leave path (bug fix)

### Added

- `tests/integration/test_leave_game_promotion.py` — New regression test `test_confirmed_leave_via_api_promotes_waitlisted_participant`: creates a `HOST_SELECTED_WITH_WAITLIST` game (`max_players=1`), inserts a confirmed + a waitlisted participant, has the confirmed participant call `POST /api/v1/games/{id}/leave` as themselves, and asserts a `waitlist_promotion` `send_dm` row targets the waitlisted user. Written `xfail(strict=True)` first, confirmed `xfailed` (proving the gap), then the marker removed after the fix landed.

### Modified

- `services/api/services/games.py` — `leave_game` now delegates the delete + promotion/demotion-detect-and-notify + host-added-dropout core to `leave_game_and_notify(self.db, game, participant)` instead of its previous inline `db.delete` + `HOST_ADDED` block; added `from shared.services.leave_game import leave_game_and_notify` import; removed the now-unused `DMFormats` import. This is the actual bug fix — `leave_game` now calls promotion detection, which it never did before.
- `tests/unit/api/services/test_games.py` — removed `TestLeaveGame::test_reload_failure_after_leave_raises_error`. That test asserted a `"Failed to reload game after leave"` `ValueError` raised when a second `self.get_game(game_id)` call returned `None`; that reload mechanism no longer exists — `leave_game_and_notify` reloads via `db.refresh(game, ["participants"])` per Task 3.3's design, not a second `get_game` call, so this failure path is now unreachable dead-code testing (same category as Phase 2's removed tests). The plan's Task 4.2 detail asserted this test would "still pass unmodified," which turned out to be inconsistent with Task 3.3's own already-implemented reload strategy.

### Verified

- `scripts/run-integration-tests.sh tests/integration/test_leave_game_promotion.py tests/integration/test_leave_game.py tests/integration/test_player_removed_queue.py tests/integration/test_games_crud.py` — 28 passed
- `uv run pytest tests/unit` — 2350 passed (net -1 vs. Phase 3's 2351: one obsolete test removed, see above)
- `uv run mypy shared/ services/` — no issues

### Notes

- The new integration test needed `seed_redis_cache(...)` for the _leaving_ participant (not just the bot-manager account already seeded by `_make_context`) — RLS (`get_db_with_user_guilds()`) resolves the acting user's guild membership from the Redis member-projection cache, and an unseeded user resolves to an empty guild list, making the game invisible ("Game not found" 404) even though it exists. That `seed_redis_cache` call must also come _before_ any `create_authenticated_client(...)` call in the test: that factory creates and closes its own asyncio event loop, and `seed_redis_cache`'s sync wrapper reuses `asyncio.get_event_loop()` — calling it afterward hits a closed loop (`RuntimeError: Event loop is closed`).

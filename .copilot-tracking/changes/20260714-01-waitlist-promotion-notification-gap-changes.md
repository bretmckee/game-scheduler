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

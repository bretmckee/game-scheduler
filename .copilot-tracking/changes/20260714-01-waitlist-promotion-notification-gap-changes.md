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

<!-- markdownlint-disable-file -->

# Changes: HOST_SELECTED_WITH_WAITLIST signup mode

## Summary

Adds `HOST_SELECTED_WITH_WAITLIST` signup mode where players self-join a waitlist and the
host promotes them to confirmed slots by dragging in the edit form, with full DM notifications.

---

## Phase 1: Enum Additions

### Added

- `shared/models/signup_method.py` — added `HOST_SELECTED_WITH_WAITLIST` enum value with `display_name` and `description` properties
- `frontend/src/types/index.ts` — mirrored `HOST_SELECTED_WITH_WAITLIST` in TypeScript `SignupMethod` enum and added `SIGNUP_METHOD_INFO` entry

---

## Phase 2: Core Partition Logic + Demotion Detection

### Modified

- `shared/utils/participant_sorting.py` — added `signup_method` parameter to `partition_participants` with `HOST_SELECTED_WITH_WAITLIST` branch (HOST_ADDED-only in confirmed); added `entered_waitlist()` method to `PartitionedParticipants` for symmetric demotion detection

### Added

- `tests/unit/shared/utils/test_participant_sorting.py` — 5 new tests for HOST_SELECTED_WITH_WAITLIST partition logic and `entered_waitlist()` detection

---

## Phase 3: New DM Formats

### Modified

- `shared/message_formats.py` — added `DMFormats.join_waitlist()` and `DMFormats.waitlist_demotion()` static methods

### Added

- `tests/unit/shared/test_message_formats.py` — 6 new tests for `join_waitlist` and `waitlist_demotion` format methods

---

## Phase 4: Backend Services — Callers + Upsert + Transitions

### Modified

- `shared/services/game_schedules.py` — updated `partition_participants` caller to pass `signup_method=game.signup_method`
- `services/api/services/games.py` — updated 4 `partition_participants` callers; added SELF_ADDED→HOST_ADDED upsert in `_update_prefilled_participants`; renamed `_detect_and_notify_promotions` → `_detect_and_notify_transitions`; added `_notify_demoted_users`
- `services/api/routes/games.py` — updated 1 `partition_participants` caller to pass `signup_method`
- `services/bot/events/handlers.py` — updated 4 `partition_participants` callers to pass `signup_method`

### Added

- `tests/unit/services/api/services/test_games.py` — tests for SELF_ADDED upsert and demotion notification transitions

---

## Phase 5: Bot Changes — Join Button, Waitlist DM Dispatch

### Modified

- `services/bot/views/game_view.py` — changed join button disabled guard from `== SignupMethod.HOST_SELECTED.value` to `in (SignupMethod.HOST_SELECTED.value,)` so `HOST_SELECTED_WITH_WAITLIST` keeps the Join button enabled
- `services/bot/events/handlers.py` — added `HOST_SELECTED_WITH_WAITLIST` guard in `_format_join_notification_message` to dispatch `DMFormats.join_waitlist()`; updated `_is_participant_confirmed` to return `True` for SELF_ADDED players in `HOST_SELECTED_WITH_WAITLIST` mode so they receive join notifications
- `tests/unit/services/bot/views/test_game_view.py` — added 2 tests: `test_join_button_enabled_for_host_selected_with_waitlist` and `test_update_button_states_host_selected_with_waitlist_keeps_join_enabled`
- `tests/unit/services/bot/events/test_handlers_join_notification.py` — added `test_format_join_notification_dispatches_waitlist_dm` (TDD RED→GREEN)
- `tests/e2e/test_signup_methods.py` — added `test_join_button_enabled_for_host_selected_with_waitlist`
- `tests/e2e/test_join_notification.py` — added `test_join_dm_says_waitlist_for_host_selected_with_waitlist`; added `SignupMethod` import
- `tests/e2e/test_waitlist_promotion.py` — added `test_promotion_drag_delivers_promotion_dm` for HOST_SELECTED_WITH_WAITLIST host-selects-waitlisted-player flow; added `SignupMethod` and `uuid4` imports

### Deviations from Plan

- `_is_participant_confirmed` extended to allow SELF_ADDED overflow players to receive join notifications in `HOST_SELECTED_WITH_WAITLIST` mode (not specified in plan, required to avoid silent DM drops)

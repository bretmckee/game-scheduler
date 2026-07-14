---
applyTo: '.copilot-tracking/changes/20260714-01-waitlist-promotion-notification-gap-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Waitlist Promotion DM on Leave

## Overview

Fix the bug where a confirmed participant voluntarily leaving a game (via the API `POST /{game_id}/leave` route or the bot's Discord "Leave" button) never triggers the `waitlist_promotion` DM for a waitlisted participant who clears a slot, by centralizing the diff-and-notify logic in `shared/` and wiring both leave transports to it.

## Objectives

- Extract the existing, correct "diff participants and notify promotions/demotions" logic out of `GameService` into a shared, transport-independent module so it has exactly one implementation.
- Create a shared "delete participant + detect/notify promotion+demotion + notify host-added-dropout" core in `shared/services/leave_game.py`, importable from both the `services/api/` and `services/bot/` Docker images.
- Wire `services/api/services/games.py::leave_game` and `services/bot/handlers/leave_game.py::handle_leave_game` to call the same shared core, replacing their independent inline delete/notify logic.
- Unify `host_added_dropout` DM delivery on the bot-service leave path onto the same `BotActionQueue` mechanism the API service already uses (removing the current direct-`discord.Client.send()` divergence).
- Prove the fix with a new API-level integration test, a new bot-handler integration test, and a new e2e test that verifies real DM delivery.

## Research Summary

### Project Files

- `services/api/services/games.py` - `leave_game` (bug: never calls promotion detection), `update_game`/`_detect_and_notify_transitions`/`_notify_promoted_users`/`_notify_demoted_users`/`_publish_promotion_notification` (correct pattern to extract), `get_game` (selectinload reference pattern), `_capture_old_state`.
- `services/bot/handlers/leave_game.py` - `handle_leave_game` (bug: never calls promotion detection; also sends `host_added_dropout` via direct `discord.Client.send()` instead of `BotActionQueue`), `_validate_leave_game`, `_notify_host_if_host_added` (to be deleted).
- `shared/utils/participant_sorting.py` - `partition_participants`, `PartitionedParticipants.cleared_waitlist`/`entered_waitlist` (existing centralized partitioning, reused as-is).
- `shared/message_formats.py` - `DMFormats.promotion`, `DMFormats.waitlist_demotion`, `DMFormats.host_added_dropout` (existing formatters, reused as-is).
- `shared/models/bot_action_queue.py` - `BotActionQueue` ORM model (existing, reused as-is).
- `shared/services/game_cancellation.py` - style/pattern reference for a plain-function shared service module (`async def cancel_game(db, game, ...)`).
- `docker/bot.Dockerfile` (lines 83-86) - confirms `services/bot/` image never contains `services/api/`, which is why the shared code MUST live under `shared/`.

### External References

- #file:../research/20260714-01-waitlist-promotion-notification-gap-research.md - Full research: reproduction evidence, code paths, recommended approach, and e2e feasibility analysis.

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python style, type hints, Ruff.
- #file:../../.github/instructions/test-driven-development.instructions.md - RED-GREEN-REFACTOR for new functions; xfail-regression workflow for bug fixes; no-xfail rule for integration/e2e tests written against already-implemented code.
- #file:../../.github/instructions/unit-tests.instructions.md - Falsifiable assertions, `assert_called_once_with`, no coverage theater.
- #file:../../.github/instructions/integration-tests.instructions.md - Real-DB integration test conventions.
- #file:../../.github/instructions/test-execution.instructions.md - Output-capture rules for `scripts/run-integration-tests.sh` / `scripts/run-e2e-tests.sh`.
- #file:../../.github/instructions/fastapi-transaction-patterns.instructions.md - Service methods do not commit; caller commits.

## Implementation Checklist

### [x] Phase 1: Extract shared waitlist transition detection

- [x] Task 1.1: Create `detect_and_notify_transitions` stub in `shared/services/waitlist_transitions.py`
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 15-40)

- [x] Task 1.2: Write unit tests with real assertions marked `xfail`
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 42-70)

- [x] Task 1.3: Implement and remove `xfail` markers
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 72-90)

- [x] Task 1.4: Refactor and add edge-case tests
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 92-104)

### [ ] Phase 2: Refactor `update_game` to use the shared transition function

- [ ] Task 2.1: Delegate `GameService` promotion/demotion methods to the shared function and delete the now-dead private methods
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 108-130)

- [ ] Task 2.2: Verify no regression in existing promotion/demotion tests
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 132-144)

### [ ] Phase 3: Create shared leave-game core

- [ ] Task 3.1: Create `leave_game_and_notify` stub in `shared/services/leave_game.py`
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 148-172)

- [ ] Task 3.2: Write unit tests with real assertions marked `xfail`
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 174-202)

- [ ] Task 3.3: Implement and remove `xfail` markers
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 204-222)

- [ ] Task 3.4: Refactor and add edge-case tests
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 224-236)

### [ ] Phase 4: Wire the API leave path (bug fix)

- [ ] Task 4.1: Write `xfail` regression test proving the gap
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 240-266)

- [ ] Task 4.2: Fix `GameService.leave_game` and remove the `xfail` marker
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 268-292)

### [ ] Phase 5: Wire the bot leave path (bug fix + delivery unification)

- [ ] Task 5.1: Write `xfail` regression tests and update the host-added-dropout tests that change delivery mechanism
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 296-330)

- [ ] Task 5.2: Fix `handle_leave_game` and remove the `xfail` markers
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 332-360)

### [ ] Phase 6: E2E coverage for leave-triggers-promotion DM delivery

- [ ] Task 6.1: Add e2e test combining the leave path with promotion-DM verification
  - Details: .copilot-tracking/planning/details/20260714-01-waitlist-promotion-notification-gap-details.md (Lines 364-390)

## Dependencies

- Existing `shared/utils/participant_sorting.py::partition_participants`/`PartitionedParticipants` (no changes needed).
- Existing `shared/message_formats.py::DMFormats.promotion`/`waitlist_demotion`/`host_added_dropout` (no changes needed).
- Existing `shared/models/bot_action_queue.py::BotActionQueue` (no changes needed).
- `uv run pytest`, `uv run mypy`, `scripts/run-integration-tests.sh`, `scripts/run-e2e-tests.sh` (e2e stack via `compose.e2e.yaml`, requires `DISCORD_USER_ID`/bot tokens configured per `docs/developer/TESTING.md`).

## Success Criteria

- A confirmed participant leaving a game with a non-empty waitlist and an open slot afterward results in a `waitlist_promotion` `bot_action_queue` row for the promoted user, via **both** the API leave route and the bot Discord "Leave" button.
- Exactly one implementation of "diff participants and notify" exists in the codebase (`shared/services/waitlist_transitions.py`), used by `update_game`, the API leave path, and the bot leave path.
- Exactly one implementation of "delete participant + notify" exists for leave flows (`shared/services/leave_game.py`), used by both transports.
- `host_added_dropout` DM delivery is unified on `BotActionQueue` for both transports (no direct `discord.Client.send()` remaining in `handle_leave_game`).
- New tests: one unit suite for each shared module, an API-level integration test, a bot-handler-level integration test, and an e2e test — all passing without `xfail`.
- No regression: existing `leave_game`, `update_game`, `handle_leave_game`, host-added-dropout, message-refresh/pg_notify, and join-notification-suppression tests all continue to pass.
- All phase-completion gates green: `uv run pytest tests/unit`, `uv run mypy shared/ services/`, and (for phases touching integration/e2e tests) `scripts/run-integration-tests.sh` / `scripts/run-e2e-tests.sh`.

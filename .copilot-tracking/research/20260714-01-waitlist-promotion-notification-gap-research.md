<!-- markdownlint-disable-file -->

# Task Research Notes: Waitlist promotion DM never sent when a confirmed participant leaves

## Research Executed

### File Analysis

- `services/api/services/games.py` (HEAD, `leave_game` at line 2355; `update_game` at ~line 2055; `_detect_and_notify_transitions` at line 1838; `_notify_promoted_users` at line 2525; `_publish_promotion_notification` at line 2554)
  - `_detect_and_notify_transitions` (partitions old vs new participants, computes `cleared_waitlist`/`entered_waitlist`, and fires promotion/demotion notifications) is called from exactly **one** place in the whole file: inside `update_game`, at line ~2147, after a host-initiated edit (including host-driven `removed_participant_ids`).
  - `leave_game` (the voluntary "user leaves their own game" path) deletes the `GameParticipant` row, publishes a `game.updated`/message-refresh notification, and — only if the leaving participant's `position_type == ParticipantType.HOST_ADDED` — enqueues a `host_added_dropout` DM to the host. It never calls `_detect_and_notify_transitions` or `_notify_promoted_users`. Confirmed by reading the full function body (no partial reads).
  - `_publish_promotion_notification` (current HEAD implementation) builds the DM via `DMFormats.promotion(...)` and inserts a `BotActionQueue(action_type="send_dm", ...)` row (line 2579) — this is the **current** (post RabbitMQ-removal) delivery mechanism.
- `services/bot/handlers/leave_game.py` (HEAD, `handle_leave_game` line 49, `_notify_host_if_host_added` line 110)
  - Discord "Leave" button handler. Deletes the participant, calls `upsert_message_refresh_and_notify(...)` (pg_notify-based SSE/refresh path), and only sends a DM via `_notify_host_if_host_added` when `position_type == HOST_ADDED`. No promotion-detection call exists here either.
- `services/bot/handlers/join_game.py` (HEAD, `handle_join_game` line 53)
  - On join, creates the `GameParticipant` row and a `NotificationSchedule` row with `notification_type="join_notification"`, `notification_time = utc_now() + 60s`. No immediate DM is sent at join time — only the delayed one.
- `services/api/services/notification_schedule.py`
  - `schedule_join_notification`/`populate_schedule`: docstring states the delayed join-notification schedule row is "automatically cancelled via CASCADE delete" if the participant leaves before the notification fires. Confirmed this is real behavior, not aspirational: the first participant to join the incident game left ~9s after joining (well inside the 60s window) and never received a `join_notification`, with no corresponding warning/error logged — consistent with cascade-delete cancellation, not a failure.
- `services/bot/events/handlers.py`
  - `_handle_notification_due` (line 397): routes `game.notification_due` events by `notification_type` — only `reminder`, `join_notification`, `clone_confirmation` are handled; anything else logs `logger.error("Unknown notification type...")`. `waitlist_promotion` is never dispatched through this path — promotion DMs bypass this router entirely and are inserted straight into `BotActionQueue` from the API service.
  - `_send_join_notification_dm` (line ~717) / `_send_dm` (line 810): DM send path. Catches `discord.Forbidden` → logs `"Cannot send DM to user %s: DMs disabled or bot blocked"` (WARN). Catches `bot.get_user(id) is None` → logs `"User %s not found in gateway cache; skipping DM"` (WARN). Both are the only two ways a DM can silently fail to reach a user; both are logged at WARN with `detected_level=warn` in the OTel structured metadata.
- `shared/message_formats.py`
  - `DMFormats` class: `promotion`, `removal`, `join_with_instructions`, `join_simple`, `reminder_host`, `reminder_participant`, `clone_confirmation`, `rewards_reminder`, `join_waitlist`, `waitlist_demotion`, `host_added_dropout`. **No method exists that notifies a host that a new participant joined/signed up** — confirmed by reading the full class and grepping every call site of every method plus every `notification_type=` string literal in the codebase.

### Code Search Results

- `grep -rn "notification_type=" --include=*.py services/`
  - Only 8 distinct notification types exist in the codebase: `clone_confirmation`, `waitlist_demotion`, `host_added_dropout`, `waitlist_promotion`, `join_notification`, `reminder`. There is no "host notified on signup" type.
- `grep -rn "_detect_and_notify_transitions\|cleared_waitlist\|_notify_promoted_users" services/ shared/` (excluding tests)
  - Single call site confirmed on HEAD, identical in count/location to `v1.1.0-RC.15`.
- `grep -rln "handle_leave_game\|\.leave_game(" tests/`
  - Leave-game test files found: `tests/integration/test_leave_game.py`, `tests/unit/bot/handlers/test_leave_game_handler.py`, `tests/unit/api/services/test_games.py`. None of these three files contain the strings "promot" or "waitlist" anywhere — the leave path has zero test coverage for promotion behavior.
- `grep -in "promot" tests/integration/test_player_removed_queue.py` (added in commit `98dd7ea0`)
  - The only integration test asserting a `waitlist_promotion` `send_dm` row is enqueued (`test_removing_confirmed_player_enqueues_waitlist_promotion_dm`) drives `PUT /api/v1/games/{id}` with `removed_participant_ids` — the **host-edit** path (`update_game`), not the voluntary leave path. Reinforces rather than contradicts the gap.
- `git log --oneline --all -i --grep="promot"` and follow-up `git merge-base --is-ancestor` checks
  - Found an older, unrelated "promotion detection bug" fix chain (`e21a8087`, `4d5e2c4e`, `f85b9454`, `f204f158`, all dated 2025-12-24) that fixed incorrect participant partitioning inside `update_game`'s promotion logic (placeholders were mis-counted). All four commits are confirmed ancestors of the `v1.1.0-RC.15` tag (`git merge-base --is-ancestor <sha> v1.1.0-RC.15` → true for all) — i.e. **already shipped in production**, months before the tag was cut, and not related to the `leave_game` gap.
- `git diff v1.1.0-RC.15..HEAD -- services/bot/handlers/leave_game.py`
  - Only transport-layer changes (RabbitMQ publish → `upsert_message_refresh_and_notify` pg_notify call). No promotion-detection logic added.
- `git diff v1.1.0-RC.15..HEAD -- services/api/services/games.py | grep -n "_detect_and_notify_transitions\|_notify_promoted_users"`
  - Confirms call site count/location unchanged across the rewrite.

### Production Log Analysis (Grafana Loki, `grafanacloud-gameschedulerprod-logs`, verified via `basicAuthUser=1570477` matching the documented prod Loki instance ID)

- Identified the only game created in the last 48h: `game_id=7b249018-d97c-402c-a62b-18cdf6c040e2`, created 2026-07-14 00:23:31 UTC (`_publish_game_created`, `services/api/services/games.py:2480` in the RC.15 build), host's game had `max_players=6`.
- Confirmed via `count_over_time` aggregation that `retry-daemon`'s constant ~204 lines/hour of "error/warn/fail"-matching text were false positives (INFO-level RabbitMQ/pika connection-cycling messages containing the word "fail" in normal operational text) — not real errors.
- Game saw heavy join/leave churn immediately after creation: participant count oscillated as high as 13 against a capacity of 6 within ~90 seconds, driven by many distinct Discord users repeatedly joining and leaving within single-digit seconds.
- Confirmed via `| detected_level=~"warn|error"` (structured-metadata filter, not text matching) that **zero** WARN/ERROR log lines exist for this game across the full 24h window — ruling out any logged DM failure, permission error, or exception for this game.
- Confirmed via a 30-day global search on `bot-service` for `"Cannot send DM"`, `"gateway cache"`, `"Forbidden"` — **zero** hits anywhere in the deployment's observed history. Rules out a systemic DM-permission/blocking problem.
- Enumerated all 6 successful `join_notification` DMs for this game (`_send_join_notification_dm`, `services/bot/events/handlers.py:734`): Discord IDs `865846903320608777`, `1210423940586016819`, `289046676935671819`, `814634582460203008`, `82978854381031424`, `271103507199688714`, all sent 00:24:41–00:24:59 UTC. User asked `271103507199688714` directly whether the DM was received, corroborating log evidence that the join-notification pathway itself works correctly.
- Zero `waitlist_promotion` log lines exist anywhere for this game, despite confirmed-participant departures that dropped the confirmed count below 6 while other participants sat on the waitlist (e.g. user `253723899076935691` leaving brought the count to `(5 remaining)` — a slot that should have triggered a promotion check).
- The first participant to join, `430140510825611265`, joined at 00:23:39.929 UTC and left at 00:23:49.137 UTC (~9s later) — inside the 60s `join_notification` delay window, so their notification was correctly cancelled via cascade delete, not lost to a bug.

### Project Conventions

- Standards referenced: `.github/instructions/grafana-observability-debugging.instructions.md` (three separate Grafana Cloud stacks; verify stack via `basicAuthUser`/instance ID before trusting query results; `bot-service` OTLP logs carry no `environment`/`container` label).
- Instructions followed: verified the connected Grafana stack was `gameschedulerprod` (instance ID `1570477`) before drawing any conclusion from log contents, per the "don't assume checked-out code == deployed code" guidance in that file.

## Key Discoveries

### Project Structure

Promotion/demotion notification dispatch is centralized in `GameService` (`services/api/services/games.py`) but is only wired into the host-edit flow (`update_game` → `_detect_and_notify_transitions`). The two participant-self-service flows that can also free up a waitlist slot — the API's `leave_game` and the bot's `handle_leave_game` button handler — are structurally independent code paths that never call into the shared promotion-detection utility (`shared/utils/participant_sorting.py::PartitionedParticipants.cleared_waitlist`). This is a design gap that predates `v1.1.0-RC.15` and survived the subsequent RabbitMQ-removal rewrite (`services/api/services/games.py`: 9 commits / 301 lines changed since RC.15; `services/bot/events/handlers.py`: 4 commits / 222 lines changed; `services/bot/handlers/leave_game.py`: 1 commit / 20 lines changed) because that rewrite only touched _transport_ (RabbitMQ → `BotActionQueue` + `pg_notify`), not the _triggering_ logic.

### Implementation Patterns

The correct pattern already exists and is exercised/tested for the host-edit path:

1. Capture old partitioned state before mutating participants: `_capture_old_state(game)` → `old_partitioned`.
2. Mutate participants (removal, capacity change, etc.).
3. Reload the game with fresh participant relationships.
4. Call `await self._detect_and_notify_transitions(game, old_partitioned)`, which internally partitions the new state, diffs against the old one via `cleared_waitlist`/`entered_waitlist`, and dispatches `_notify_promoted_users` / `_notify_demoted_users`.

This same 4-step pattern needs to be applied around the participant deletion in both `leave_game` implementations.

### Complete Examples

Current (correct, but only reachable from `update_game`) promotion trigger, `services/api/services/games.py`:

```python
# Capture current participant state for promotion detection
(
    _old_max_players,
    _old_participants_snapshot,
    old_partitioned,
) = self._capture_old_state(game)

# ... mutate game / participants ...

# Refresh game object to get updated relationships from database
await self.db.refresh(game, ["participants"])
game = await self.get_game(game.id)

# Detect promotions/demotions and notify affected users
await self._detect_and_notify_transitions(game, old_partitioned)
```

Current `leave_game` (API service) — gap is the absence of any partition/notify step after the delete, `services/api/services/games.py:2355-2453`:

```python
async def leave_game(self, game_id: str, user_discord_id: str) -> None:
    ...
    participant = participant_result.scalar_one_or_none()
    if participant is None:
        ...
        return

    position_type = participant.position_type
    host_discord_id = game.host.discord_id if game.host else None

    await self.db.delete(participant)          # <-- slot freed here
    game = await self.get_game(game_id)         # reload
    await self._publish_game_updated(game)       # SSE/refresh only

    if position_type == ParticipantType.HOST_ADDED and host_discord_id:
        ...                                      # host_added_dropout only
    # NOTHING ELSE — no promotion detection, ever
```

Bot-service equivalent gap, `services/bot/handlers/leave_game.py:49-107`:

```python
async def handle_leave_game(interaction: discord.Interaction, game_id: str) -> None:
    ...
    position_type = participant.position_type
    await db.delete(participant)
    await upsert_message_refresh_and_notify(db, game_id, game.channel.channel_id, game.guild_id)
    await db.commit()
    ...
    await _notify_host_if_host_added(interaction, game, position_type)
    # No promotion detection here either
```

### API and Schema Documentation

Full `notification_type` inventory (all locations grepped, none missed):

| `notification_type`  | Trigger                                 | Recipient                | Currently reachable from `leave_game`?     |
| -------------------- | --------------------------------------- | ------------------------ | ------------------------------------------ |
| `join_notification`  | 60s after joining, if still confirmed   | joining participant      | N/A (own path, works)                      |
| `reminder`           | scheduled pre-game reminder             | host + participants      | N/A                                        |
| `clone_confirmation` | recurring-game clone carryover          | carried-over participant | N/A                                        |
| `waitlist_demotion`  | confirmed → waitlisted (host edit only) | demoted user             | **No**                                     |
| `waitlist_promotion` | waitlisted → confirmed (host edit only) | promoted user            | **No — the bug**                           |
| `host_added_dropout` | a host-added player leaves              | host                     | Yes (only case leave_game notifies anyone) |

`DMFormats.promotion(game_title, scheduled_at_unix, jump_url=...)` is the exact formatter already used by the working host-edit path; reusing it requires no new message-format work.

### Technical Requirements

- Any fix must target **HEAD's current architecture**: promotion notifications are delivered via a `BotActionQueue` row insert (`action_type="send_dm"`), not the RabbitMQ `event_publisher.publish_deferred(...)` calls used in `v1.1.0-RC.15`. The two versions are not cross-compatible/cherry-pickable.
- `services/bot/handlers/leave_game.py`'s `handle_leave_game` operates directly against the DB (no `GameService` reuse) but already has a DB session in scope, so it can insert `BotActionQueue` rows itself — it does not need a live `discord.Client` at write time, only at consume time (handled elsewhere by the existing `BotActionListener`).
- `services/api/services/games.py::leave_game` already has `_capture_old_state` / `_detect_and_notify_transitions` / `_notify_promoted_users` on the same class (used by `update_game`), but per project convention (confirmed centralization precedent below) the diff+notify step itself should move out of `GameService` and into a shared module so it isn't reachable from only one of the two leave transports.
- **`services/bot/` cannot import `GameService` at all** — verified via `docker/bot.Dockerfile`, which only copies `shared/` and `services/bot/` into the bot-service image, never `services/api/`. This rules out "bot handler delegates to `GameService.leave_game`" as an option and fixes the convergence point at `shared/`: both transports must call the same `shared/` function, not one calling into the other's service layer.
- Today the two leave paths already diverge on `host_added_dropout` delivery, not just on promotion: the API service enqueues it via `BotActionQueue` (async, delivered whenever the bot's queue listener next runs), while the bot-service handler sends it immediately via a direct `discord.Client.send()` call (`services/bot/handlers/leave_game.py:129`). Centralizing the whole delete+notify core (not just promotion) in `shared/` removes this second divergence too, on the same pass.
- **Existing centralization precedent**: the Dec 2025 fix chain (`4d5e2c4e feat: add centralized participant partitioning utility`) already extracted participant partitioning into `shared/utils/participant_sorting.py::partition_participants`/`PartitionedParticipants` specifically to stop the sort+slice logic from being duplicated across 6 call sites. The current gap is the same shape of problem one layer up: the _diff-and-notify_ step (`_detect_and_notify_transitions` → `_notify_promoted_users`/`_notify_demoted_users` → `BotActionQueue` insert) still lives only inside `GameService`, so it's invisible to the bot-service leave handler. User direction: **centralize, do not duplicate.**
- Verified the API leave path is reachable purely over HTTP: `POST /api/v1/games/{game_id}/leave` (`services/api/routes/games.py:901`) → `GameService.leave_game`. This route is already exercised the same way `test_player_removed_queue.py` exercises `PUT /api/v1/games/{id}`, via `create_authenticated_client` + `admin_db_sync` assertions against `bot_action_queue` — no mocking of DB or service internals needed.
- The bot-service Discord-button leave path is **not** reachable over HTTP at all — `handle_leave_game` is a Discord gateway interaction handler with its own direct DB access (`tests/integration/test_leave_game.py` already establishes the pattern: call `handle_leave_game(interaction, game_id)` directly against a real DB via `_patch_db()`/`BotAsyncSessionLocal`, with a `MagicMock` `discord.Interaction`). This path must stay a handler-level integration test; it cannot be "simulated with API calls" the way the API-service path can, because it is a different transport entirely.
- No existing test (unit, integration, or e2e) exercises promotion-on-leave in either path today.

## Recommended Approach

**Centralize the diff-and-notify step, then wire both leave transports to call it — no duplicated partition/diff/notify logic in either caller.**

**Deployment constraint that decides where the shared code must live** (verified, not assumed): `docker/bot.Dockerfile` (lines 83-86) copies only `pyproject.toml`, `shared/`, `services/__init__.py`, and `services/bot/` into the bot-service runtime image — `services/api/` is never copied in. Confirmed via `grep` that `services/bot/` currently has zero imports from `services.api.*` anywhere. This means `services/bot/handlers/leave_game.py` **cannot** import `GameService` or anything else under `services/api/` — the module would not exist in that container at runtime (`ModuleNotFoundError`), regardless of whether it "looks fine" in the monorepo source tree. (For contrast, `docker/api.Dockerfile` copies both `services/api/` and `services/bot/`, so the reverse direction is technically possible, but nothing in the codebase does that today and there's no reason to start.) **Conclusion: the two leave entry points can only converge inside `shared/`**, which is the one package both Docker images actually ship.

1. **New shared module**, e.g. `shared/services/leave_game.py`, holding the full "delete participant → detect + notify promotion/demotion → detect + notify host-added-dropout" core as one function (not just the diff/notify slice), taking a `db: AsyncSession`, the loaded `game`, and the `participant` to remove:
   - Captures `old_partitioned` via `partition_participants` before delete.
   - Deletes the participant.
   - Reloads participants, computes `cleared_waitlist`/`entered_waitlist` via the same `shared/utils/participant_sorting.py` helpers already centralized there.
   - For promotions/demotions, builds the DM via `DMFormats.promotion(...)`/`DMFormats.waitlist_demotion(...)` and inserts `BotActionQueue(action_type="send_dm", ...)` rows.
   - For `position_type == ParticipantType.HOST_ADDED`, builds and enqueues the `host_added_dropout` DM the same way (via `BotActionQueue`, not a direct `discord.Client.send()` call) — this also **removes** the existing divergence where the bot-service currently sends that DM immediately/directly while the API service enqueues it, unifying on one delivery mechanism end to end.
   - Depends only on `shared/` + SQLAlchemy — no dependency on `GameService`, FastAPI, or a live `discord.Client`, so it's importable from both `services/api/` and `services/bot/` images.
2. **`services/api/services/games.py::leave_game`**: keep its existing validation/lookup (game found, not completed, user found, participant found — this part is API-service-specific request handling, e.g. HTTP error mapping) and its `_publish_game_updated` SSE call, but delegate the delete+promotion+dropout core to the new shared function instead of the current inline `db.delete(participant)` + ad-hoc `HOST_ADDED` block.
3. **`services/api/services/games.py::update_game`**: also refactor `_detect_and_notify_transitions`/`_notify_promoted_users`/`_notify_demoted_users` to call the promotion/demotion half of the same shared module, so there is exactly one implementation of "diff participants and notify" in the whole codebase, not two (leave-path core vs. update-path core).
4. **`services/bot/handlers/leave_game.py::handle_leave_game`**: keep its Discord-specific bits (interaction deferral, `_validate_leave_game`, success/error messages, `upsert_message_refresh_and_notify` for SSE) but delegate the delete+promotion+dropout core to the identical shared function call used by the API service — this is the actual point of convergence the user flagged: both transports call the _same function_ immediately after their transport-specific validation, rather than each maintaining a parallel reimplementation that merely shares a smaller sub-helper.
5. **Tests** (both real-DB integration tests, no unit-level mocking of the DB, matching repo convention):
   - **API path**: new test in `tests/integration/test_leave_game.py` (or a new `test_leave_game_promotion.py`) driving `client.post(f"/api/v1/games/{game_id}/leave")` via `create_authenticated_client`, asserting a `waitlist_promotion` row appears in `bot_action_queue` — directly mirroring `test_player_removed_queue.py::test_removing_confirmed_player_enqueues_waitlist_promotion_dm`, confirming the user's instinct that this half is API-call-testable.
   - **Bot path**: new test in `tests/integration/test_leave_game.py` (bot-handler suite), calling `handle_leave_game(interaction, game_id)` directly against a real DB per the existing pattern in that file, asserting the same `bot_action_queue` row appears. This half is **not** an API-call test — it has to invoke the handler directly, since there is no HTTP route for the Discord button flow.

### E2E feasibility (resolves open concern about bot-to-bot DM delivery)

User raised a concern that e2e coverage might not be possible because "bot users can't send each other messages." Investigated the e2e harness directly rather than assuming either way:

- `docs/developer/TESTING.md:277-281`: the account DMs are verified against, `TEST_DISCORD_USER_ID`, is documented as a **real human developer's Discord account** ("Right-click your username → Copy User ID"), which must join the test guild "(required for DM verification)". It is not a bot account.
- `tests/e2e/helpers/discord.py::DiscordTestHelper.get_user_recent_dms` (line 223) verifies delivery by having the **main bot's own test client** (`main_bot_helper`, authenticated with the same production bot token via `discord_main_bot_token`) open/fetch its DM channel with the recipient and read back messages where `msg.author.id == self.client.user.id` — i.e. it re-reads its own sent history. This works regardless of whether the recipient is a bot or human; it does not require logging in as the recipient.
- **A directly combinable precedent already exists and passes today**:
  - `tests/e2e/test_waitlist_promotion.py::test_waitlist_promotion_sends_dm`/`test_promotion_drag_delivers_promotion_dm` already prove `main_bot_helper.wait_for_recent_dm(user_id=discord_user_id, dm_type=DMType.PROMOTION, ...)` correctly detects a delivered promotion DM to the real test-user account, triggered via `PUT /api/v1/games/{id}` (participant removal / max_players increase / host drag-promote).
  - `tests/e2e/test_host_added_dropout_notification.py::test_host_added_dropout_sends_dm_to_host` (line 123) already proves the **leave path itself** is e2e-drivable: `authenticated_player_a_client.post(f"/api/v1/games/{game_id}/leave")` (Player A, a second bot account, leaving) triggers a DM, verified the same way.
  - These two patterns combine directly: create a game with `max_players=1`, Player A confirmed, the real test user (`discord_user_id`) waitlisted (as in `test_promotion_drag_delivers_promotion_dm`), have Player A call `POST /{game_id}/leave`, then assert `main_bot_helper.wait_for_recent_dm(user_id=discord_user_id, dm_type=DMType.PROMOTION, ...)` fires. No new e2e infrastructure is needed — this is a straightforward new test (or a third `trigger_promotion_via_*` parametrization in `test_waitlist_promotion.py`) built entirely from existing fixtures/helpers.
- Conclusion: the "bots can't DM each other" constraint does not block this — the DM recipient in every promotion scenario is the real human test-user account, never a bot account, and that delivery path is already proven reliable in CI today. **E2E coverage for the API leave→promotion flow is both feasible and low-effort.**
- Caveat: this only covers the **API leave path** (`POST /{game_id}/leave`). No e2e test in the suite simulates an actual Discord button click/gateway interaction for _any_ handler, and this is a **platform constraint, not a suite gap**: a component (button) interaction is only ever originated by a real Discord client UI session — a bot token cannot fabricate the `INTERACTION_CREATE` gateway event or the session-bound interaction token a button click produces, so bots structurally cannot "click" buttons the way `discord.js`/`discord.py` handlers expect to receive them. This is consistent across the whole suite: every button-driven handler (`join_game`, `leave_game`, etc.) is verified only via direct handler invocation with a mocked `discord.Interaction` against a real DB (`tests/integration/test_leave_game.py`'s existing pattern), never via a simulated real click. The bot-service `handle_leave_game` Discord-button path stays at that same integration level for this fix too — there is no way to get true e2e (real Discord round-trip) coverage of it, on this platform, at all.

## Implementation Guidance

- **Objectives**: Ensure `waitlist_promotion` DMs are sent whenever a confirmed participant leaves a game (via either the API `leave_game` service method or the bot's Discord "Leave" button) and their departure clears a slot for a waitlisted participant — matching the behavior already correct for host-initiated edits/removals, and doing so through one shared implementation rather than two parallel ones.
- **Key Tasks**:
  - Create `shared/services/leave_game.py` (or similar) with the full delete + promotion/demotion-detect-and-notify + host-added-dropout-notify core, using `shared/utils/participant_sorting.py` and inserting `BotActionQueue` rows for every notification type it triggers (including `host_added_dropout`, unifying its delivery mechanism across both transports).
  - Refactor `GameService.update_game`'s existing `_detect_and_notify_transitions`/`_notify_promoted_users`/`_notify_demoted_users` call site to use the promotion/demotion half of the same shared module (no behavior change, but removes the duplication risk for future callers).
  - Wire `services/api/services/games.py::leave_game` to delegate to the shared module immediately after its existing validation, replacing its inline delete + `HOST_ADDED` block.
  - Wire `services/bot/handlers/leave_game.py::handle_leave_game` to delegate to the _same_ shared module call immediately after its existing validation, replacing its inline delete + `_notify_host_if_host_added` call — this is the actual convergence point between the two transports.
  - Add an HTTP-level integration test for the API leave path (`POST /{game_id}/leave`) asserting the `waitlist_promotion` `bot_action_queue` row.
  - Add a handler-level integration test for the bot leave path (direct `handle_leave_game` invocation) asserting the same.
  - Add an e2e test combining `authenticated_player_a_client.post(f"/api/v1/games/{id}/leave")` (from `test_host_added_dropout_notification.py`'s pattern) with `main_bot_helper.wait_for_recent_dm(dm_type=DMType.PROMOTION)` (from `test_waitlist_promotion.py`'s pattern) to prove real end-to-end DM delivery on the leave-triggers-promotion flow.
- **Dependencies**: `shared/utils/participant_sorting.py` (`partition_participants`, `PartitionedParticipants.cleared_waitlist`/`entered_waitlist`), `shared/message_formats.py::DMFormats.promotion`/`waitlist_demotion`, `shared/models/bot_action_queue.py` (`BotActionQueue`).
- **Success Criteria**: A confirmed participant leaving a game with a non-empty waitlist and an open slot afterward results in a `waitlist_promotion` `bot_action_queue` row for the promoted user, verified by a new HTTP-level API integration test, a new bot-handler integration test, and a new e2e test proving real DM delivery — with zero duplicated partition/diff/notify logic between the two call sites; no regression to existing `leave_game` or `update_game` tests (host-added dropout DM, message-refresh/pg_notify behavior, join-notification suppression logic, and existing promotion/demotion unit tests all continue to pass).

<!-- markdownlint-disable-file -->

# Task Research Notes: Participants not notified when a game's time changes

## Research Executed

### File Analysis

- services/api/services/games.py (`update_game`, ~L2170-2250)
  - Order: `_capture_old_state` -> `_update_game_fields` -> reschedule notification/status schedules -> `_detect_and_notify_transitions` -> `_publish_game_updated` (only if `message_id` is set).
  - `_capture_old_state` (L1891) snapshots participants/max_players only. It does NOT capture the old `scheduled_at`, so no code can currently tell the time changed.
  - `_update_game_fields` (L1403) knows `scheduled_at_updated` but uses it only to flag schedule rebuilds; the result is not used for notification.
- shared/services/waitlist_transitions.py (L61, L85)
  - The only update-path DMs: `BotActionQueue(action_type="send_dm")` for waitlist promotion/demotion.
- services/bot/events/handlers.py (`_handle_game_updated`, L174)
  - Only inserts a `message_refresh_queue` row, which silently edits the Discord announcement. No DM, no ping.
- services/bot/bot_action_listener.py (L47-190)
  - Dispatch has `send_dm` / `send_notification` handlers already, so a DM path needs no new bot plumbing.
- docs/PLAYER-GUIDE.md (L161-166, L219-223)
  - Promises "Major changes (time/date) always trigger notifications" and "You'll receive an update notification in your DMs". The code does not do this.

### Code Search Results

- `resched|time.?chang|schedule.?chang` in services/ and shared/ (py)
  - No notification logic for time changes.
- `BotActionQueue(` / `action_type=`
  - Producers: game_created, player_removed, game_cancelled, send_dm (waitlist, leave), notification_due, participant_drop_due, status_transition_due. None for a schedule change.

### Project Conventions

- Standards referenced: AGENTS.md / CLAUDE.md, TDD applies (Python).
- Instructions followed: researcher-enhancements (no version recommendations needed).

## Key Discoveries

### Root cause (verified in code, not reproduced)

Host edits `scheduled_at` -> reminders are rebuilt for the new time -> the Discord embed is silently edited in place -> nobody who signed up is told. This is a gap between documented behavior and implementation, not a user error. The reporter's account is consistent with it.

Not established: that this is what happened to this user (see Technical Requirements).

### Implementation Patterns

Existing pattern to reuse: queue a `BotActionQueue(action_type="send_dm", ...)` in the same transaction as the update, as `waitlist_transitions` and `leave_game` do (shared/services/leave_game.py L56).

### Technical Requirements

- Capture old `scheduled_at` before `_update_game_fields` (extend `_capture_old_state`, or return it from `_update_scheduled_at_field`).
- After the update, if any notify-field changed and the game is announced, enqueue ONE DM per participant (confirmed AND waitlisted) per edit, listing each changed field as old -> new. Time uses Discord `<t:...>` timestamps (render in each viewer's timezone); include a link to the game message.
- Notify fields (decided with user): `scheduled_at`, `expected_duration_minutes`, `where`, `signup_instructions`.
- Excluded (decided): `title`, `description`, `rewards`, host-only settings (`reminder_minutes`, `remind_host_rewards`, `reminders_as_dms`, `archive_delay_seconds`, `notify_role_ids`), pre-announcement fields (`post_at`, `clear_post_at`), `recur_rule`.
- Already covered, no new work: `max_players` and `signup_method` changes. `_capture_old_state` partitions with the old values and `detect_and_notify_transitions` (shared/services/waitlist_transitions.py L120-141) re-partitions with the new ones, so anyone pushed to or released from the waitlist gets the existing promotion/demotion DM. Participant removal has `player_removed`; cancellation has `game_cancelled`.
- Do not DM on no-op saves (compare the normalized UTC naive values).
- Out of scope: a recurrence clone with a different date is a new game, not an edit. The DB has `updated_at` but no edit history, so a past edit cannot be proven after the fact (reporter's case resolved, see Outstanding).

## Recommended Approach

Implement the documented behavior: DM all participants (confirmed and waitlisted) when any notify field changes, using the existing `send_dm` queue action. Smallest change, matches the player guide, no new tables, no bot changes.

## Implementation Guidance

- **Objectives**: Participants are told, in one DM per edit, whenever a host changes a notify field of an announced game.
- **Key Tasks**: (1) capture old notify-field values; (2) new helper in shared/services (next to waitlist_transitions) building the DMs; (3) call it from `update_game`; (4) unit tests for changed / unchanged / unannounced / waitlisted; (5) integration test with the bot queue; (6) update docs/PLAYER-GUIDE.md (see Documentation below).
- **Dependencies**: `BotActionQueue` `send_dm` handler (exists).
- **Success Criteria**: Changing any notify field on an announced game yields exactly one DM per participant; unchanged saves yield none.

## Documentation

docs/PLAYER-GUIDE.md must describe the shipped behavior, in the same change as the code:

- "Game Updates" (L161-166): replace "may receive" / "major changes always" with the exact rule. You get one DM per edit when the time, expected duration, location or signup instructions change, listing old -> new. Title, description and rewards edits send no DM. Waitlist moves caused by max players or signup method changes still send the existing promotion/demotion DMs.
- "What if the game time changes?" (L219-223): keep the DM and embed-update bullets, and add that waitlisted players are notified too.
- Until the code ships, the guide keeps its current wording (it describes intended behavior); do not merge a guide-only change ahead of the code.

## Outstanding:

- Reporter's game confirmed as a host edit of the time; root cause is the missing DM, not a recurrence clone or timezone display.

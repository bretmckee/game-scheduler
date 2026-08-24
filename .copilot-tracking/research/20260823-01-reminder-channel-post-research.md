<!-- markdownlint-disable-file -->

# Task Research Notes: Move Game Reminders from DMs to Location Channel/Thread Posts

## Research Executed

### File Analysis

- `services/bot/events/handlers.py`
  - `_handle_notification_due` (line ~306) routes `notification_type == "reminder"` to `_handle_game_reminder`.
  - `_handle_game_reminder` (line ~441) loads the game with participants, validates state (`_validate_game_for_reminder`), partitions participants into confirmed/overflow via `_partition_and_filter_participants`, builds a jump URL from `game.guild.guild_id` / `game.channel.channel_id` / `game.message_id`, then fans out DMs: `_send_participant_reminders` (confirmed), `_send_participant_reminders` (waitlist — **only the first waitlisted participant**, via `overflow[:_WAITLIST_REMINDER_COUNT]` since commit `0a9d6041`), `_send_host_reminder`.
  - `_WAITLIST_REMINDER_COUNT = 1` (line ~70) — module constant controlling how many waitlisted participants receive a reminder DM.
  - `_send_participant_reminders` (line ~387) loops participants and calls `_send_reminder_dm` per user.
  - `_send_host_reminder` (line ~421) calls `_send_reminder_dm` with `is_host=True`.
  - `_send_reminder_dm` (line ~868) builds the message via `DMFormats.reminder_host` / `DMFormats.reminder_participant` and calls `_send_dm(user_discord_id, message)`.
  - `_send_dm` (line ~810) resolves the user from the gateway cache (`self.bot.get_user`), logs and returns `False` on `discord.Forbidden` (DMs disabled/blocked) and on `discord.HTTPException`.
  - Existing channel-access helpers: `_get_bot_channel` (line ~104) returns `discord.TextChannel | None` from `self.bot.get_channel(int(channel_id))` with an `isinstance` check; `_validate_channel_for_refresh` (line ~229) does the same for refresh flows. `discord.TextChannel` is a base class of `discord.Thread` in discord.py, so the `isinstance(channel, discord.TextChannel)` check already accepts threads.
- `shared/message_formats.py`
  - `DMFormats.reminder_host(game_title, game_time_unix, jump_url)` (line ~136) and `DMFormats.reminder_participant(game_title, game_time_unix, is_waitlist, jump_url)` (line ~158) produce plain-text DM strings using `<t:{unix}:F>` / `<t:{unix}:R>` timestamps and an optional jump URL.
- `services/bot/formatters/game_message.py`
  - `GameMessageFormatter.create_notification_embed(game_title, scheduled_at, host_id, time_until)` (line ~648) builds a "🔔 Game Reminder" embed (Start Time + Host fields). **Currently unused by any production code path** — only referenced by its own unit tests. It is a ready-made candidate for the channel-post embed.
- `services/api/services/channel_resolver.py`
  - `ChannelResolver.resolve_channel_mentions(location_text, guild_discord_id, field_label)` resolves `#name`, `<#id>`, and `https://discord.com/channels/{guild}/{channel}` mentions in free text to `<#id>` tokens. `_TEXT_LIKE_CHANNEL_TYPES = frozenset({0, 10, 11, 12})` — GUILD_TEXT plus the three thread types (PUBLIC_THREAD=11, PRIVATE_THREAD=12, ANONYMOUS=10). Invalid/ambiguous mentions produce validation errors that block game creation.
- `services/api/services/games.py`
  - `_resolve_free_text_fields_for_create` (line ~590) calls `resolve_channel_mentions` on `where` (always, when non-empty) before persisting. **The `where` column therefore stores the resolved text with `<#channel_id>` tokens** (plus any surrounding prose).
  - `_resolve_template_fields` (line ~367) falls back to `template.where` when the request omits `where`.
- `shared/models/game.py`
  - `GameSession.where: Mapped[str | None] = mapped_column(Text, nullable=True)` (line 62) — free-text location, nullable.
- `services/api/services/notification_schedule.py`
  - `NotificationScheduleService.populate_schedule` / `update_schedule` create `notification_schedule` rows per reminder minute; a Postgres trigger emits `NOTIFY` which becomes a `notification_due` row in the bot action queue. **No changes needed here** — the schedule/trigger/queue pipeline is delivery-agnostic.
- `services/bot/bot_action_listener.py`
  - `case "notification_due": await self._event_handlers._handle_notification_due(data)` (line ~185) — the event entry point. No changes needed.
- `services/bot/announcement_loop.py`
  - `_announce` (line ~163) is the canonical pattern for posting to a channel from the bot: `handlers._get_bot_channel(game.channel.channel_id)` → `channel.send(content=..., embed=..., view=..., allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))`.
- `tests/unit/services/bot/events/test_handlers_game_reminder.py`
  - Four `_send_reminder_dm` unit tests (participant / no-jump-url / waitlist / host) assert on the DM string content.
  - Six `_handle_notification_due` flow tests assert `mock_send_reminder.await_count` (3, 1, 1, 2, 4, 4) and per-call kwargs (`user_discord_id`, `is_host`, `is_waitlist`, `jump_url`). Since commit `0a9d6041`, the waitlist flow tests (`test_handle_game_reminder_due_with_waitlist`, `test_handle_game_reminder_due_only_first_waitlist_reminded`) already encode the first-waitlisted-only behavior (e.g. 4 participants / `max_players=2` → 2 confirmed + 1 waitlist + 1 host = 4 DMs). These will need rework when the fan-out changes.
- `tests/e2e/test_game_reminder.py`
  - `test_game_reminder_dm_delivery` creates a game with `reminder_minutes=[1]`, waits for the `notification_schedule` row, then `main_bot_helper.wait_for_recent_dm(user_id, game_title, dm_type=DMType.REMINDER)` and asserts the DM content contains the title. **This e2e test encodes the DM behavior and must be rewritten** to assert a channel post instead.
- `tests/e2e/helpers/discord.py`
  - `find_game_reminder_dm` (line ~243) matches DMs by `game_title in dm.content and "starts <t:" in dm.content and ":F>" in dm.content` — confirms reminders are plain text, not embeds.
  - `wait_for_message(channel_id, message_id, ...)` (line ~483) polls `channel.fetch_message()` — reusable for verifying a posted reminder message if its ID can be learned; a history-scan helper (like the DM one) would be the natural addition for "new message in channel matching title".
- `tests/integration/test_scheduler_loop.py`, `tests/integration/test_notification_schedule.py`
  - Cover the DB/trigger side of reminders (schedule rows, `notification_due` queue row, `sent` flag). **Unaffected** by a delivery-mechanism change.

### Code Search Results

- `reminder` in `services/**/*.py`
  - Reminder fan-out is entirely in `services/bot/events/handlers.py` (`_handle_game_reminder`, `_send_participant_reminders`, `_send_host_reminder`, `_send_reminder_dm`); scheduling is in `services/api/services/notification_schedule.py` and `shared/services/game_schedules.py`.
- `location` in `services/**/*.py`
  - The location field is `GameSession.where` (free text). `ChannelResolver` is the only component that interprets channel references inside it. `services/api/services/calendar_export.py` also renders `game.where` into calendar exports (unaffected).
- `create_notification_embed`
  - Defined in `services/bot/formatters/game_message.py` line 648; referenced only by `tests/unit/services/bot/formatters/test_game_message.py`. Dead in production — safe to adopt.
- `notification_due`
  - Full pipeline verified: Postgres trigger → `bot_action_queue` row (`shared/services/event_builders.py`) → `bot_action_listener.py` → `handlers._handle_notification_due`. Delivery-agnostic; no schema or queue changes required.

### External Research

- #fetch:https://discord.com/developers/docs/interactions/message-components
  - Not required for this change; no new interactive components are introduced.
- #fetch:https://discordpy.readthedocs.io/en/latest/api.html
  - `discord.TextChannel` is the base class for `discord.Thread` (threads are `TextChannel` subclasses), so existing `isinstance(channel, discord.TextChannel)` guards already accept thread objects. `channel.send()` works identically on threads. `discord.Forbidden` is raised when the bot lacks `SendMessages`/`SendMessagesInThreads` permissions.

### Project Conventions

- Standards referenced: TDD (RED→GREEN→REFACTOR) per `.github/instructions/test-driven-development.instructions.md`; behavioral assertions per `.github/instructions/unit-tests.instructions.md` (assert on real arguments, no coverage theater); self-explanatory code per `.github/instructions/self-explanatory-code-commenting.instructions.md`.
- Instructions followed: `python.instructions.md` (type hints, docstrings), `fastapi-transaction-patterns.instructions.md` (not applicable — change is bot-side only), `test-execution.instructions.md` (e2e runs need `tee` capture and ≥900000ms timeout).

## Key Discoveries

### Project Structure

- Reminder delivery is a single, well-isolated fan-out in the bot: one handler (`_handle_game_reminder`) that currently sends DMs to all confirmed participants, the first waitlisted participant only (since commit `0a9d6041`, `overflow[:_WAITLIST_REMINDER_COUNT]`), and the host. Everything upstream (scheduling, trigger, queue, event routing) is delivery-agnostic.
- The "location" is `GameSession.where`, a nullable free-text field. At create/update time, `ChannelResolver` rewrites valid channel references to `<#channel_id>` tokens and **rejects** games whose location mentions an invalid/ambiguous channel. So a `where` value that is "a single channel or thread" is reliably stored as exactly one `<#id>` token (possibly with surrounding prose).
- The bot already has the exact posting pattern needed: `announcement_loop._announce` posts to `game.channel.channel_id` via `handlers._get_bot_channel(...)` + `channel.send(...)`.
- A purpose-built reminder embed (`create_notification_embed`) already exists but is unused in production.

### Implementation Patterns

- **Channel resolution from `where`**: extract the single `<#(\d+)>` token with a regex (the same token format `ChannelResolver` writes). If `where` is `None`, empty, or contains zero or multiple `<#id>` tokens, the "single channel/thread" assumption does not hold → fall back to the existing DM behavior.
- **Channel object acquisition**: reuse `handlers._get_bot_channel(channel_id)` (gateway cache, `isinstance` TextChannel check — threads pass). Optionally fall back to `self.bot.fetch_channel(int(channel_id))` for cold-cache cases, mirroring patterns already used in `tests/unit/services/bot/events/test_channel_worker.py`-style flows.
- **Posting**: one `channel.send(content=..., embed=..., allowed_mentions=discord.AllowedMentions(everyone=True, roles=True))` per reminder event (not per participant). Mention participants with `<@id>` tokens in the content (or `allowed_mentions`-controlled mentions) so the post still reaches the right people.
- **Error handling**: catch `discord.Forbidden` (missing send permission in that channel/thread) and `discord.NotFound` (channel deleted) → log and fall back to DMs, preserving today's delivery guarantee.

### Complete Examples

```python
# services/bot/events/handlers.py — current DM fan-out (to be replaced)
# Waitlist DMs are limited to the first waitlisted participant (commit 0a9d6041)
await self._send_participant_reminders(confirmed, game.title, game_time_unix, is_waitlist=False, jump_url=jump_url)
await self._send_participant_reminders(overflow[:_WAITLIST_REMINDER_COUNT], game.title, game_time_unix, is_waitlist=True, jump_url=jump_url)
await self._send_host_reminder(game.host, game.title, game_time_unix, jump_url=jump_url)

# Proposed channel-post path (sketch)
location_channel_id = extract_single_channel_id(game.where)  # regex <#(\d+)>, None unless exactly one
channel = await self._get_bot_channel(location_channel_id) if location_channel_id else None
if channel is None:
    # fall back to existing DM fan-out
    ...
else:
    embed = GameMessageFormatter.create_notification_embed(
        game_title=game.title,
        scheduled_at=game.scheduled_at,
        host_id=game.host.discord_id if game.host else "",
        time_until=...,
    )
    # Channel post mentions only confirmed participants + host (not waitlist)
    mention_ids = [p.user.discord_id for p in confirmed]
    if game.host and game.host.discord_id:
        mention_ids.append(game.host.discord_id)
    content = " ".join(f"<@{mid}>" for mid in mention_ids)
    try:
        await channel.send(content=content, embed=embed, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True))
        # After successful channel post, still DM the first waitlisted participant(s)
        await self._send_participant_reminders(
            overflow[:_WAITLIST_REMINDER_COUNT],
            game.title,
            game_time_unix,
            is_waitlist=True,
            jump_url=jump_url,
        )
    except (discord.Forbidden, discord.NotFound):
        # fall back to full DM fan-out (confirmed + first waitlisted + host)
        ...
```

### API and Schema Documentation

- No schema changes. `notification_schedule`, `bot_action_queue`, and `games.where` are all reused as-is.
- `NotificationDueEvent` payload (`shared/schemas/events.py` line ~60) carries `game_id`, `notification_type`, `participant_id` — unchanged.

### Configuration Examples

- No new configuration. Behavior is derived from existing data (`games.where`).

### Technical Requirements

- **TDD applies** (Python). Write/adjust unit tests first for the new resolution + posting + fallback logic, then implement.
- **E2E test rewrite required**: `tests/e2e/test_game_reminder.py::test_game_reminder_dm_delivery` asserts DM delivery; it must create a game whose `where` is a single `<#channel>` mention and assert a new message appears in that channel. If the game has a waitlisted participant, the test should also verify that participant receives a reminder DM (hybrid delivery).
- **Unit test rework**: the six `_handle_notification_due` flow tests in `tests/unit/services/bot/events/test_handlers_game_reminder.py` assert DM fan-out counts/kwargs (including the two waitlist tests added/updated by commit `0a9d6041` that encode first-waitlisted-only behavior); the four `_send_reminder_dm` tests remain valid only if DMs are retained as a fallback path.
- **Permissions**: the bot needs `Send Messages` (and `Send Messages in Threads` for threads) in the location channel. This is an operational/deployment consideration, not a code change.
- **Rate limits**: one post per reminder event per game is far lighter than the current DM fan-out (all confirmed + first waitlisted + host); no rate-limiting work needed.

## Recommended Approach

**Hybrid delivery: post a reminder in the location channel/thread mentioning confirmed participants + host when `where` resolves to exactly one channel; always DM the first waitlisted participant(s); fall back to full DM fan-out when channel posting fails.**

Concretely:

1. Add a small pure helper (e.g. `extract_single_channel_id(where: str | None) -> str | None`) that returns the channel ID only when `where` contains exactly one `<#id>` token; unit-test it against plain text, one mention, multiple mentions, and `None`.
2. In `_handle_game_reminder`, after validation and partitioning:
   - Resolve the location channel via the helper + `_get_bot_channel` (with an optional `fetch_channel` fallback).
   - If a channel is available: build the reminder embed (adopt `create_notification_embed`, extending it with a jump-link field if desired), mention only confirmed participants + host (exclude waitlist from the channel post), `channel.send(...)` once, then DM the first `_WAITLIST_REMINDER_COUNT` waitlisted participants via `_send_participant_reminders(overflow[:_WAITLIST_REMINDER_COUNT], ..., is_waitlist=True)`.
   - On `discord.Forbidden` / `discord.NotFound`, or when no single channel resolves: fall back to the existing full `_send_participant_reminders` (confirmed + first waitlisted) / `_send_host_reminder` DM fan-out unchanged.
3. Keep `_send_reminder_dm` and the DM formats intact (they are used for waitlist DMs in the success path and for the full fallback).
4. Rewrite the e2e reminder test to assert a channel post + waitlist DMs; add a unit test for the fallback path (no/ambiguous location → full DM fan-out).

This is the minimal, low-risk hybrid approach: it reuses the existing channel-posting pattern from `announcement_loop`, the existing (dead) reminder embed, and preserves waitlist DMs (targeted, as in the current behavior) plus the existing full DM path as a safety net. It requires no schema, queue, or API changes.

## Implementation Guidance

- **Objectives**: Deliver game reminders as a channel post (mentioning confirmed participants + host) in the game's location channel/thread when the location is a single channel/thread, plus DMs to the first waitlisted participant(s); preserve full DM delivery as a fallback so no reminder is ever lost.
- **Key Tasks**:
  1. Add `extract_single_channel_id` helper + unit tests (RED).
  2. Add `_post_reminder_to_channel` (or inline in `_handle_game_reminder`) with embed + mentions (confirmed + host only) + waitlist DM fan-out + `Forbidden`/`NotFound` fallback (RED→GREEN).
  3. Wire the branch into `_handle_game_reminder`; keep full DM fan-out (confirmed + first waitlisted + host) as the else/fallback path.
  4. Update the six `_handle_notification_due` flow unit tests (including the two waitlist tests from commit `0a9d6041`) to cover both the channel-post and DM-fallback branches with real arguments.
  5. Rewrite `tests/e2e/test_game_reminder.py` to create a game with a single-channel `where` and assert the channel post (add a history-scan helper to `tests/e2e/helpers/discord.py` if needed).
  6. Optionally extend `create_notification_embed` with a jump-link field and update its unit tests.
- **Dependencies**: None new. Uses existing `discord.py` APIs, `ChannelResolver` output format, and `GameMessageFormatter`.
- **Success Criteria**:
  - When `where` contains exactly one valid `<#id>` and the bot can access that
    channel/thread, exactly one reminder message is posted there mentioning
    confirmed participants + host, and the first `_WAITLIST_REMINDER_COUNT`
    waitlisted participant(s) receive reminder DMs (channel post + targeted
    waitlist DMs).
  - When `where` is empty/ambiguous or the channel is inaccessible, the existing
    full DM fan-out still occurs: confirmed + first waitlisted + host (no regression).
  - All unit tests pass (`uv run pytest tests/unit`); the rewritten e2e reminder
    test passes with `tee`-captured output.

---

## Extension (added 2026-08-23): Host opt-out "Always send reminders as DMs"

Follow-up request after Phases 1–3 landed: give hosts a per-game checkbox
(default off), "Always send reminders as DMs", that short-circuits the
location-channel resolution in `_deliver_game_reminders` so every reminder for
that game takes the full DM fan-out path unconditionally.

### Design decisions (confirmed with user)

- **Game-only flag — no template-level default.** Storing it on templates would
  require extra schema surface; explicitly skipped for now. The column lives on
  `game_sessions` only, defaults to `false`, and create requests omitting it get
  `False`.
- **Short-circuit semantics.** When the flag is true, skip the
  `extract_single_channel_id` / `_get_bot_channel` / `_post_reminder_to_channel`
  path entirely and go straight to the existing full DM fan-out (confirmed +
  first waitlisted + host). Waitlist participants still receive their targeted
  DM because the fallback already sends them one. No new delivery logic exists —
  the guard clause reuses the Phase 2 fallback branch verbatim.

### Verified precedent: `remind_host_rewards` end-to-end pattern

The codebase already ships an identical shape of feature (host-facing boolean,
default false, form-driven). Exact touch points verified:

| Layer                | File / location                                                                                                                 | Pattern                                                                                                                                               |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| Migration            | `alembic/versions/20260321_add_rewards_fields.py`                                                                               | `op.add_column("game_sessions", sa.Column(..., sa.Boolean(), nullable=False, server_default=sa.text("false")))`; symmetric `drop_column` in downgrade |
| Model                | `shared/models/game.py` line ~71                                                                                                | `Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))`                                                  |
| Create schema        | `shared/schemas/game.py` line ~98 (`GameCreateRequest`)                                                                         | `bool \| None` Field with description; `None` means "use default"                                                                                     |
| Update schema        | `shared/schemas/game.py` line ~160 (`GameUpdateRequest`)                                                                        | `bool \| None = None` (absent = no change)                                                                                                            |
| Response schema      | `shared/schemas/game.py` lines 245–249 (`GameResponse`)                                                                         | plain `bool` field with `default=False`                                                                                                               |
| Create route         | `services/api/routes/games.py` line ~390                                                                                        | `Annotated[bool \| None, Form()] = None`, passed through to service                                                                                   |
| Update route         | `services/api/routes/games.py` line ~671                                                                                        | same Form() pattern on the PUT endpoint                                                                                                               |
| Service create       | `services/api/services/games.py` `_build_game_session` lines 545–549                                                            | request value if not None else fallback                                                                                                               |
| Service update       | `services/api/services/games.py` `_update_remaining_fields` lines 1280–1313                                                     | `if update_data.X is not None: game.X = ...`                                                                                                          |
| Clone-for-recurrence | `shared/services/game_schedules.py` line ~231 and `services/api/services/games.py` line ~937                                    | explicit carry-over of host preferences into clones                                                                                                   |
| Frontend type        | `frontend/src/types/index.ts` line ~124 (`GameSession`)                                                                         | optional boolean field                                                                                                                                |
| Frontend form state  | `frontend/src/components/GameForm.tsx` lines 113 (interface), 310 + 343 (initializers)                                          | `remindHostRewards: initialData?.remind_host_rewards ?? false` in both useState init and the `useEffect` re-init                                      |
| Frontend checkbox    | `frontend/src/components/GameForm.tsx` lines 963–975                                                                            | MUI `FormControlLabel` + `Checkbox`, `setFormData((prev) => ({...}))` onChange, `disabled={loading}`                                                  |
| Frontend payloads    | `frontend/src/pages/CreateGame.tsx` line 234; `EditGame.tsx` lines 233 + 368                                                    | `payload.append('field', value ? 'true' : 'false')` — EditGame appends on two code paths (update + archive branch)                                    |
| Frontend tests       | `frontend/src/components/__tests__/GameForm.rewards.test.tsx`; `frontend/src/pages/__tests__/CreateGame.test.tsx` lines 537–600 | checkbox reflects `initialData`; payload sends `'true'`/`'false'` strings                                                                             |

### Bot-side change surface (minimal by design)

- `_deliver_game_reminders` (`services/bot/events/handlers.py`) is the single
  delivery decision point created in Phase 2. The new guard clause goes at its
  top: if `game.reminders_as_dms` is true, log and fall through to the existing
  full DM fan-out block without resolving any channel. Complexity stays well
  under the complexipy limit (the method was just extracted for this reason).
- All six pre-existing flow unit tests set no flag attribute on `sample_game`,
  so they must keep passing unchanged (flag falsy → identical behavior). New
  tests set `sample_game.reminders_as_dms = True` explicitly.

### Migration mechanics

- Current alembic head verified via `uv run alembic heads`: **`bf79aeffb6b0`** —
  the new migration's `down_revision`.
- Column name: `reminders_as_dms` (snake_case, matches the "send reminders as
  DMs" phrasing; camelCase `remindersAsDms` in frontend form state).
- `nullable=False, server_default=sa.text("false")` so existing rows are backfilled
  with the default-off value by Postgres itself.

### Test strategy per phase

- **Phase 4 (backend)**: RED unit tests first — `_build_game_session` uses the
  request override / defaults False when absent (`tests/unit/services/api/services/test_games_service.py`, mirroring `test_build_game_session_remind_host_rewards_request_overrides_template` at line ~1141); `_update_remaining_fields` sets/leaves-alone the field (mirrors `test_update_remaining_fields_updates_remind_host_rewards` at line ~459 of `tests/unit/services/api/services/test_update_game_fields_helpers.py`); clone carry-over (mirrors `tests/unit/services/test_system_clone_for_recurrence.py`). Integration test asserts the column exists and defaults false on a fresh game (pattern: `tests/integration/test_rewards_fields.py`).
- **Phase 5 (bot)**: RED unit tests in `tests/unit/services/bot/events/test_handlers_game_reminder.py` driving `_handle_notification_due` with `sample_game.where="<#...>"` + `sample_game.reminders_as_dms = True`: assert `_get_bot_channel` never awaited, `_post_reminder_to_channel` never awaited, full DM fan-out counts; plus a flag-false control test proving channel-post path still taken.
- **Phase 6 (frontend)**: vitest component/page tests mirroring the rewards-feature tests; gates are `cd frontend && npm run build` and `cd frontend && npm run test`.

### Success criteria (extension)

- Host can check "Always send reminders as DMs" when creating or editing a game;
  unchecked is the default and changes nothing about existing behavior.
- When checked, every reminder for that game delivers via the full DM fan-out
  (confirmed + first waitlisted + host) regardless of what `where` contains —
  no channel post is attempted.
- Recurring clones carry the flag over from the source game.
- All pre-commit gates green per phase (unit, mypy, complexipy, frontend
  build+test where applicable).

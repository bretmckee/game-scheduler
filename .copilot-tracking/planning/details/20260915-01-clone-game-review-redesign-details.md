<!-- markdownlint-disable-file -->

# Task Details: Clone Game Review/Edit-Before-Create Redesign

## Research Reference

**Source Research**:

- .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md — primary. The
  "Backend architecture revision: reuse `create_game`'s pipeline instead of an override-diff schema"
  section (lines 159-176) supersedes this document's own "Central open question" (lines 106-117),
  "Technical Requirements" (lines 177-186), and "Implementation Guidance" (lines 191-203) sections, and
  is the authoritative backend design for every phase below.
- .copilot-tracking/research/20260911-01-game-posting-schedule-cleanup-research.md — sibling doc; cited
  only for historical motivation. Its Part 7 recommendation ("give `clone_game`/`CloneGameRequest` a
  real `post_at`, route finalization through `AnnouncementLoop`") is satisfied entirely as a side effect
  of delegating to `create_game`'s pipeline (verified in this planning session: `create_game`'s existing
  `_persist_and_publish`, `services/api/services/games.py` lines 787-850, already implements the exact
  deferred/immediate-publish branch Part 7 asks for — this was already true when the primary research was
  written, it was `clone_game` alone that lacked it). No dedicated "give clone a working post_at" phase
  exists in this plan; it is a natural consequence of Phase 4.

## Verified Against Current Code In This Planning Session (Supersedes Stale Prior-Plan Assumptions)

These are concrete findings from direct reads of `services/api/services/games.py`,
`services/api/routes/games.py`, and `shared/schemas/game.py` in this session, made necessary because the
architecture revision changes what "reuse `create_game`'s pipeline" actually implies mechanically. Do not
re-derive these; treat them as settled.

1. **`GameCreateRequest` has no `channel_id` field, and never has.** `_build_game_session`
   (`games.py` line 501: `channel_id = template.channel_id`) always takes the channel from the game's
   template, unconditionally — there is no override path anywhere in `create_game`'s pipeline. Since the
   redesigned `clone_game` reuses `source_game.template_id` verbatim (per the research's revision), the
   new game's channel is automatically identical to the source game's channel, with **zero new code**.
   `CloneGameRequest` must **not** gain a `channel_id` field — there is nothing for it to override. This
   also applies identically to `notify_role_ids` and `allowed_player_role_ids`: both are template-derived
   only (`_build_game_session` lines 502-503), so reusing `source_game.template_id` reproduces them
   automatically. (Note, out of scope to fix: `EditGame.tsx` submits a `channel_id` form field that
   `update_game`'s route — `services/api/routes/games.py` lines 743-768 — never reads; this is a
   pre-existing, unrelated dead-field bug, not something this plan touches.)
2. **`GameCreateRequest`/`create_game` has no concept of `rewards` at all** (not just "hardcoded to
   None" as `clone_game` does today) — `rewards` is exclusively an `update_game`/`GameUpdateRequest`
   field. A freshly `create_game`-built `GameSession` simply never sets it (ORM/DB default). Delegating
   to `create_game` reproduces today's "clone never carries over rewards" behavior with **zero extra
   code** — no `resolved_rewards` special-casing needed anywhere in `CloneGameRequest` or `clone_game`.
3. **`create_game`'s single `host_user_id` parameter serves two different roles that must NOT be
   collapsed into one value for clone**: it is both (a) the subject of the internal
   `_verify_bot_manager_permission` check (`_resolve_game_host`, `games.py` lines 258-262) run when
   `game_data.host` is set, and (b) the default new-game host when `game_data.host` is unset
   (`actual_host_user_id = requester_user_id`, line 256). In `create_game`'s own call site these are
   always the same person (the user creating the game), so one parameter suffices. For `clone_game` they
   must be different people: the permission-check subject must always be `current_user` (whoever clicked
   "clone"), but the default host (when the clone request does not override host) must be
   `source_game.host_id` (today's exact, tested behavior — clone always keeps the original host by
   default, regardless of who initiated the clone). A bare, single-parameter call to `create_game()`
   cannot reproduce this; `create_game`/`_resolve_game_host` need one small additive parameter
   (Phase 3) to carry the two identities separately.
4. **A raw `@\w+(?:\.\w+)*` mention-token regex in `resolve_mentions_in_text` will false-positive-match
   inside already-resolved `<@discord_id>` text** (`services/api/services/participant_resolver.py` line
   290: `re.findall(r"@\w+(?:\.\w+)*", text)` — confirmed no lookbehind excluding a preceding `<`).
   `update_game` never calls `_resolve_free_text_fields_for_create` at all (confirmed: the only call site
   is inside `create_game`, `games.py` line 744), so this has never mattered before — edited text is
   simply stored as submitted, never re-resolved. Delegating `clone_game` to `create_game`'s pipeline
   changes this: any inherited (or host-resubmitted-unchanged) `description`/`signup_instructions`
   containing a real `<@1234567890>` mention from a prior create/clone would have its digits
   false-positive-matched as a bogus `@1234567890` username token, raising a spurious validation error
   on a field the host never touched. `channel_resolver.py`'s own `#`-mention regex already solves the
   identical problem with a `(?<!<)` lookbehind (`channel_resolver.py` line 54:
   `re.compile(r"(?<!<)#([^\s<>#]+)")`) — Phase 1 applies the same fix to
   `resolve_mentions_in_text`'s regex. This is a small, general, backward-compatible bug fix to shared
   code (benefits `create_game` too, defensively), not clone-specific special-casing, and is required
   before Phase 4's delegation is safe to ship.
5. **`GameService.clone_game` has exactly one caller** (`services/api/routes/games.py` line 920)
   confirmed via repo-wide grep; no other internal or bot-side code calls it directly. `_system_clone_for_recurrence`
   (`games.py` lines 1016-1022) calls a wholly separate function, `clone_game_for_recurrence`
   (imported from `shared.services.game_schedules` or similar), for the unrelated automatic-recurrence
   feature — it does not call `self.clone_game` and is untouched by every phase below.
6. **`get_game`'s eager-load set already includes everything Phase 5's deadline-carryover computation
   needs** (`games.py` lines 852-875: `participants` with `.user` eager-loaded via `selectinload`).
   `create_game`'s own return value is itself the result of a final `self.get_game(game.id)` call
   (`_persist_and_publish`, `games.py` line 842), so `clone_game` needs no extra reload after delegating.
7. **`_publish_game_created` only enqueues a `BotActionQueue` row referencing `game.id`/`channel_id`**
   (`games.py` lines 2425-2438) — it embeds no snapshot of image/participant data. The bot consumes this
   queue asynchronously, after the whole request's transaction commits. This makes it safe for
   `clone_game` to mutate `new_game.thumbnail_id`/`banner_image_id` (Phase 4) _after_ `create_game()`
   returns (even when `create_game()` already ran its own immediate-publish branch internally, because
   `post_at` was omitted/past) — the announcement the bot eventually builds always reads the game's
   final, fully-committed row.

## Design Notes Carried Into Every Phase Below

1. **Override-field semantics**: every scalar `CloneGameRequest` field that has a `GameCreateRequest`
   counterpart is `Optional[None]`, resolved once, when building the delegated `GameCreateRequest`, as
   `clone_data.<field> if clone_data.<field> is not None else source_game.<field>`. `scheduled_at` has no
   source fallback (a clone always needs an explicit new time, matching today). `participants`,
   `post_at`, and `host` are **not** inherit-from-source fields (see notes 2-3 below).
2. **`participants` is always authoritative, never inherited.** `CloneGameRequest.participants: list[str]
= Field(default_factory=list)` mirrors `GameCreateRequest.initial_participants` exactly. Mapped
   directly to `initial_participants` on the constructed `GameCreateRequest` — `create_game`'s own
   `resolve_initial_participants` → `_create_participant_records` pipeline (already fully tested)
   produces the correct roster and, when read back later via `partition_participants`, the correct
   confirmed/waitlist split purely from submitted order, with no additional clone-side logic. An empty
   list means an empty roster, not "inherit source's roster" — the frontend always populates it from
   whatever the participant editor currently shows (Phase 8).
3. **`post_at` is `Optional[None]` meaning "post now"** (matches `GameCreateRequest.post_at`'s own
   docstring), mapped directly to the constructed `GameCreateRequest.post_at`. `create_game`'s existing
   `_persist_and_publish` deferred/immediate-publish branching (`games.py` lines 826-848) and its
   `post_at >= scheduled_at` guard (line 706-708) apply automatically — no separate phase, no duplicate
   validator on `CloneGameRequest`.
4. **`allowed_player_role_ids`, `notify_role_ids`, `channel_id`, and `rewards` are explicitly out of the
   override set** — see "Verified Against Current Code" items 1-2 above. Do not add UI, schema fields, or
   resolution logic for any of them.
5. **Discovered integration hazard: `GameForm`'s `initialData`-resync `useEffect`**
   (`frontend/src/components/GameForm.tsx`, the effect immediately following the `useState<GameFormData>`
   initializer, ~lines 320-360) rebuilds the entire `formData` object whenever the `initialData` object
   reference changes. If `CloneGame.tsx` naively recomputed a fresh `initialData` object every time the
   host toggled the carryover dropdowns, every other in-progress edit would be silently wiped on the next
   toggle. Phase 8 resolves this with a two-stage screen (carryover/deadline choices first, then a single,
   stable `initialData` object computed once and handed to a `GameForm` instance mounted exactly once) —
   `GameForm.tsx` itself stays untouched.
6. **`GameForm`'s file-upload inputs are unconditionally rendered in every mode**
   (`frontend/src/components/GameForm.tsx` lines 1005, 1038 — confirmed neither `type="file"` input is
   gated by `mode === 'edit'`, unlike the "Remove" buttons at lines 1014/1047 which are). Reusing
   `GameForm` unmodified in `mode="create"` for the clone screen means a host genuinely can attach a new
   thumbnail/banner while cloning. This is why image handling is "copy by reference **when no new file
   is uploaded**" (Phase 6), not an unconditional carry-over — the raw-upload path is a real, reachable
   case, not a hypothetical.
7. **`GameForm` needs no `roles` prop and no `/channels` fetch for the clone screen.** Confirmed via
   `grep` on `GameFormProps` (`GameForm.tsx` lines 118-125): only `channels: Channel[]` and
   `isBotManager?: boolean` are relevant here (no `roles` prop exists on `GameForm` at all — the host
   override field is a plain mention text input, gated only by `isBotManager`). Per "Verified Against
   Current Code" item 1, the clone screen can synthesize a single-item `channels` array directly from
   `sourceGame.channel_id`/`channel_name` (both already present on the fetched `GameResponse`, per
   `shared/schemas/game.py` lines 216-217) — exactly mirroring how `CreateGame.tsx` already synthesizes
   its own single-item `channels` array from the selected template (research lines 38-40), just sourced
   from the game response instead of a template response. **No new `/guilds/{id}/channels` or
   `/guilds/{id}/roles` fetch is needed** — this corrects the prior plan draft's assumption.
8. **Pre-existing, out-of-scope gap, noted so it is not mistaken for a regression introduced here**:
   `clone_game` today never calls `_create_game_status_schedules`; `create_game`'s pipeline (via
   `_persist_and_publish`) always does (`games.py` line 834). Delegating `clone_game` to `create_game`
   therefore **adds** status-transition scheduling (IN_PROGRESS/COMPLETED schedules) to cloned games for
   the first time. This is a natural, intentional, low-risk side effect of full delegation (matching the
   research's "no risk of double-processing" framing at line 175) — call it out in the changes log as a
   incidental fix, not something requiring its own phase.
9. **Newly surfaced, accepted trade-off**: `create_game`'s pipeline requires `template_id` to resolve to
   an existing `GameTemplate` row (`_load_game_dependencies`, `games.py` lines 446-452, raises
   `ValueError` otherwise). `GameSession.template_id` is nullable and templates are deletable
   (`services/api/routes/templates.py` line 287-313). Today's `clone_game` never loads the template at
   all, so cloning a game whose template was since deleted currently "works" (in the sense that it
   doesn't error, though it also can't apply any template default changes). After this redesign, cloning
   such a game will fail with a clear `ValueError` ("Template not found..."), surfaced as a 404 through
   the existing error-handling path. This is an accepted, documented consequence of "reuse `create_game`'s
   real pipeline" (consistent with item 3's host-permission recheck being intentional) — Phase 4 adds a
   regression test locking in this behavior; no attempt is made to special-case it.

## Phase 1: Fix `resolve_mentions_in_text`'s Regex To Skip Already-Resolved `<@id>` Tokens

### Task 1.1: Add a `(?<!<)` lookbehind to the mention-token regex

In `services/api/services/participant_resolver.py::resolve_mentions_in_text` (current line 290), change
`tokens = re.findall(r"@\w+(?:\.\w+)*", text)` to
`tokens = re.findall(r"(?<!<)@\w+(?:\.\w+)*", text)`, mirroring the existing, proven pattern in
`channel_resolver.py` line 54 (`re.compile(r"(?<!<)#([^\s<>#]+)")`) for the identical class of problem.
Update the method's docstring to note the exclusion.

- **Files**:
  - `services/api/services/participant_resolver.py` — one-line regex change plus docstring note.
  - `tests/unit/services/api/services/test_participant_resolver.py` — add regression tests.
- **Success**:
  - `resolve_mentions_in_text("hi <@1234567890>, join us", guild_id)` returns the text **unchanged**, with
    no errors (this is the RED case: today it raises a validation error for the bogus `@1234567890`
    token; confirm the test fails before the fix, passes after).
  - `resolve_mentions_in_text("hi @alice, join us", guild_id)` still resolves `@alice` normally (regression
    guard: the fix must not break real, non-`<`-prefixed mentions).
  - `resolve_mentions_in_text("mixed <@111> and @bob", guild_id)` resolves only `@bob`, leaves `<@111>`
    untouched.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 52-53, 129) —
    original Design Note 6 concern (now resolved generally rather than via override-gating, per the
    "Verified Against Current Code" section above, item 4).
- **Dependencies**: None — pure, isolated, backward-compatible bug fix in shared code.

## Phase 2: Extend `CloneGameRequest` With Override Fields, `post_at`, and `participants`

### Task 2.1: Add the new optional fields

Extend `services/api/schemas/clone_game.py`'s `CloneGameRequest` with:

```python
title: str | None = Field(None, min_length=1, max_length=200)
description: str | None = Field(None, max_length=2000)
signup_instructions: str | None = Field(None, max_length=1000)
where: str | None = Field(None, max_length=500)
max_players: int | None = Field(None, ge=1, le=100)
reminder_minutes: list[int] | None = None
expected_duration_minutes: int | None = Field(None, ge=1)
signup_method: str | None = Field(None, max_length=50)
participants: list[str] = Field(default_factory=list)
host: str | None = Field(None, max_length=200)
remind_host_rewards: bool | None = None
reminders_as_dms: bool | None = None
post_at: dt.datetime | None = None
recur_rule: str | None = None
```

(Field constraints copied verbatim from `GameCreateRequest`, `shared/schemas/game.py` lines 41-112, for
consistency.) Do **not** add `channel_id`, `rewards`, `allowed_player_role_ids`, or `notify_role_ids` (see
Design Note 4). Do **not** add a `signup_method` value validator or a `post_at < scheduled_at` validator
on `CloneGameRequest` itself — both are already enforced, for free, when `clone_game` constructs the
delegated `GameCreateRequest` in Phase 4 (`GameCreateRequest.validate_signup_method`, `shared/schemas/game.py`
lines 114-126; `create_game`'s own `post_at >= scheduled_at` check, `games.py` lines 706-708). Duplicating
either here would only produce a less precise, earlier error for no functional benefit, at the cost of two
more things to keep in sync with `GameCreateRequest`.

- **Files**:
  - `services/api/schemas/clone_game.py` — add the fields above.
  - `tests/unit/schemas/test_clone_game_schema.py` — add tests.
- **Success**:
  - All 13 new fields accept `None`; omitting all of them still produces a valid `CloneGameRequest`
    (backward compatibility with every existing test/caller).
  - `participants` defaults to `[]` when omitted.
  - No existing test in the file changes or breaks.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 159-176) —
    architecture revision establishing "every field already final by submit time."
- **Dependencies**: None (schema-only, additive; nothing reads these fields until Phase 4).

### Task 2.2: TDD cycle

Write the new schema tests first (fail against today's `CloneGameRequest` with
`ValidationError: extra fields not permitted` / `AttributeError`), then add the fields, confirm green. No
`NotImplementedError` stub applies to a Pydantic field addition.

- **Files**: same as Task 2.1.
- **Success**: `uv run pytest tests/unit/schemas/test_clone_game_schema.py -v` shows new tests failing
  before, passing after.
- **Dependencies**: Task 2.1.

## Phase 3: Add `default_host_user_id` To `create_game`/`_resolve_game_host` (Additive, Backward-Compatible)

### Task 3.1: Thread a separate default-host identity through host resolution

Per "Verified Against Current Code" item 3, `clone_game` needs the bot-manager-permission-check subject
(`current_user`) and the default-when-no-override host (`source_game.host_id`) to be different values —
something `create_game`'s current single `host_user_id` parameter cannot express. Add a new, optional
parameter to both methods, defaulting to `None` so `create_game`'s only existing call site
(`services/api/routes/games.py` line 477-484) is entirely unaffected:

```python
async def _resolve_game_host(
    self,
    game_data: game_schemas.GameCreateRequest,
    guild_config: guild_model.GuildConfiguration,
    requester_user_id: str,
    default_host_user_id: str | None = None,
) -> tuple[str, user_model.User]:
    actual_host_user_id = (
        default_host_user_id if default_host_user_id is not None else requester_user_id
    )
    if game_data.host and game_data.host.strip():
        await self._verify_bot_manager_permission(requester_user_id, guild_config.guild_id)
        ...  # unchanged below this point
```

```python
async def create_game(
    self,
    game_data: game_schemas.GameCreateRequest,
    host_user_id: str,
    default_host_user_id: str | None = None,
    thumbnail_data: bytes | None = None,
    ...
) -> game_model.GameSession:
    ...
    _actual_host_user_id, host_user = await self._resolve_game_host(
        game_data, guild_config, host_user_id, default_host_user_id
    )
    ...
```

This is a pure, additive widening — no existing behavior changes when the new parameter is omitted. It
replaces the prior plan draft's "generalize `_resolve_game_host` via a `Protocol`" phase entirely (that
generalization is unnecessary now that clone constructs a real `GameCreateRequest`, per research lines
175; the only remaining gap is this identity-decoupling, which a Protocol would not have solved anyway).

- **Files**:
  - `services/api/services/games.py` — widen `_resolve_game_host` and `create_game` signatures.
  - `tests/unit/services/api/services/test_games_service.py` (or wherever `_resolve_game_host`'s /
    `create_game`'s existing coverage lives — locate via
    `grep -rn "_resolve_game_host\|async def create_game" tests/unit/`) — add tests.
- **Success**:
  - `uv run mypy shared/ services/` passes.
  - Calling `create_game(game_data, host_user_id=X)` (omitting the new parameter) behaves identically to
    today for every existing test — the RED signal for this task is a new test that calls
    `_resolve_game_host`/`create_game` with `default_host_user_id=Y` (`Y != X`, `game_data.host` unset)
    and asserts the resolved host is `Y`, not `X`; this fails against today's code (no such parameter
    exists) and passes after the change.
  - A second new test: `game_data.host` set (an override) with `default_host_user_id=Y` still runs the
    bot-manager permission check against `requester_user_id` (`X`), not `Y` — confirming the two
    identities stay decoupled correctly.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 171, 175) —
    "delegate ... to `create_game`'s real pipeline" and the elimination of the Protocol-generalization
    phase; the `default_host_user_id` need itself is a finding from this planning session's direct code
    verification (item 3 above), not from either research document.
- **Dependencies**: None (isolated, additive; Phase 2's schema fields are not required for this phase).

## Phase 4: Rewrite `clone_game` To Delegate To `create_game`; Wire Route-Level `ValidationError` Handling

This is the central phase: `clone_game`'s current ~140-line body (verbatim field-copy `GameSession`
construction, its own participant-partition-driven roster build, its own unconditional
`_setup_game_schedules`/`_publish_game_created` calls) is replaced by constructing a `GameCreateRequest`
and delegating to `create_game`. Image handling (Phase 6) and deadline-carryover (Phase 5) are added back
afterward as clearly separated, additive steps — kept out of this phase to keep it reviewable and to avoid
a temporary "images stop carrying over" regression window (see Task 4.1's ordering note).

### Task 4.1: Replace `clone_game`'s body with a `create_game` delegation

```python
async def clone_game(
    self,
    source_game_id: str,
    clone_data: CloneGameRequest,
    current_user: auth_schemas.CurrentUser,
    role_service: roles_module.RoleVerificationService,
) -> game_model.GameSession:
    source_game = await self.get_game(source_game_id)
    if source_game is None:
        msg = f"Game {source_game_id!r} not found"
        raise ValueError(msg)

    from services.api.dependencies import permissions as permissions_deps  # noqa: PLC0415

    can_manage = await permissions_deps.can_manage_game(
        game_host_id=source_game.host.discord_id,
        guild_id=source_game.guild.guild_id,
        current_user=current_user,
        role_service=role_service,
        db=self.db,
    )
    if not can_manage:
        msg = (
            "You don't have permission to clone this game. "
            "Only the host, Bot Managers, or guild admins can clone games."
        )
        raise ValueError(msg)

    game_data = game_schemas.GameCreateRequest(
        template_id=source_game.template_id,
        title=clone_data.title if clone_data.title is not None else source_game.title,
        scheduled_at=clone_data.scheduled_at,
        description=(
            clone_data.description if clone_data.description is not None else source_game.description
        ),
        max_players=(
            clone_data.max_players if clone_data.max_players is not None else source_game.max_players
        ),
        expected_duration_minutes=(
            clone_data.expected_duration_minutes
            if clone_data.expected_duration_minutes is not None
            else source_game.expected_duration_minutes
        ),
        reminder_minutes=(
            clone_data.reminder_minutes
            if clone_data.reminder_minutes is not None
            else source_game.reminder_minutes
        ),
        where=clone_data.where if clone_data.where is not None else source_game.where,
        signup_instructions=(
            clone_data.signup_instructions
            if clone_data.signup_instructions is not None
            else source_game.signup_instructions
        ),
        initial_participants=clone_data.participants,
        host=clone_data.host,
        signup_method=(
            clone_data.signup_method if clone_data.signup_method is not None else source_game.signup_method
        ),
        remind_host_rewards=(
            clone_data.remind_host_rewards
            if clone_data.remind_host_rewards is not None
            else source_game.remind_host_rewards
        ),
        reminders_as_dms=(
            clone_data.reminders_as_dms
            if clone_data.reminders_as_dms is not None
            else source_game.reminders_as_dms
        ),
        post_at=clone_data.post_at,
        recur_rule=clone_data.recur_rule if clone_data.recur_rule is not None else source_game.recur_rule,
    )

    new_game = await self.create_game(
        game_data,
        host_user_id=current_user.user.id,
        default_host_user_id=source_game.host_id,
    )

    # Images carry over by reference unconditionally in this phase; Phase 6 makes
    # this conditional on "no new file uploaded."
    new_game.thumbnail_id = source_game.thumbnail_id
    new_game.banner_image_id = source_game.banner_image_id
    if source_game.thumbnail_id is not None or source_game.banner_image_id is not None:
        await increment_image_ref(self.db, source_game.thumbnail_id)
        await increment_image_ref(self.db, source_game.banner_image_id)
        self.db.add(new_game)
        await self.db.flush()

    return new_game
```

Note: `increment_image_ref` already tolerates `None` (today's `clone_game` calls it unconditionally for
both fields regardless of whether either is set — `games.py` lines 952-953) — the `if` guard above is an
optional micro-optimization to skip a no-op DB write when the source has no images at all; keep or drop
per reviewer preference, it has no behavioral effect either way.

Delete the entire old body: the verbatim `GameSession(...)` construction, the old
`partition_participants`/`players_to_carry`/`waitlist_to_carry`/participant-row-creation loop, the
`_setup_game_schedules` call, and the `_publish_game_created` call. Do **not** delete
`_apply_deadline_carryover`, `_add_participant_carryover_schedules`, or `_process_carryover_group` — Phase
5 reuses all three unchanged.

Also update `services/api/routes/games.py`'s clone route (lines 903-935) to use the shared
`_handle_game_operation_errors` helper instead of its current hand-rolled `except ValueError` block, since
`clone_game` can now raise `resolver_module.ValidationError` (via the delegated `create_game` call) which
today's route does not catch at all (`resolver_module.ValidationError` subclasses `Exception`, not
`ValueError` — confirmed via `participant_resolver.py` line 45 — so it would otherwise surface as an
unhandled 500):

```python
try:
    game = await game_service.clone_game(game_id, clone_data, current_user, role_service)
except (resolver_module.ValidationError, ValueError) as e:
    _handle_game_operation_errors(e, clone_data)
```

Widen `_handle_game_operation_errors`'s `form_data` parameter type union (`games.py` line 306) to include
`services.api.schemas.clone_game.CloneGameRequest`.

- **Files**:
  - `services/api/services/games.py` — replace `clone_game`'s body; widen `_handle_game_operation_errors`
    is in the routes file (see below).
  - `services/api/routes/games.py` — rewrite the clone route's try/except; widen
    `_handle_game_operation_errors`'s type union.
  - `tests/unit/services/test_clone_game.py` — substantially rewritten (see Task 4.2).
  - `tests/integration/test_clone_game_endpoint.py` — add a case: an unresolvable `@mention` in an
    overridden `description` returns 422 with `error: "invalid_mentions"`.
- **Success**:
  - A clone request overriding only `title` produces a new game with the overridden title and every other
    field equal to `source_game`'s resolved value.
  - Omitting `host` preserves today's exact tested behavior: the new game's host is `source_game`'s host,
    not the requester.
  - A bot-manager overriding `host` with a valid mention gets that mentioned user as host; a
    non-bot-manager attempting the same override is rejected exactly as `create_game` rejects it today —
    per "Verified Against Current Code" item 3, this permission check is now intentionally run against
    `current_user`, and (per the research's confirmed decision) `check_game_host_permission` against the
    template's `allowed_host_role_ids` now also runs against the resolved host even when no override was
    supplied, which it never did before — add a regression test for this new, intentional behavior: a
    source game's host who no longer satisfies the template's `allowed_host_role_ids` causes clone to
    fail with the same "does not have permission" error `create_game` raises today.
  - Cloning a game whose `template_id` points to a deleted template raises `ValueError` ("Template not
    found..."), surfaced as 404 (Design Note 9's accepted trade-off) — add a regression test.
  - An unresolvable `@mention` in an overridden free-text field or in `participants` raises
    `resolver_module.ValidationError`, surfaced by the route as 422 with `invalid_mentions`.
  - Images still carry over by reference for every existing carryover/scalar-override test (verified via
    `increment_image_ref` call assertions and `new_game.thumbnail_id == source_game.thumbnail_id`).
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 159-176) — full
    architecture revision this task implements.
- **Dependencies**: Phase 1 (safe free-text delegation), Phase 2 (schema fields to read), Phase 3
  (`default_host_user_id` parameter).

### Task 4.2: TDD cycle and test-file restructuring

`tests/unit/services/test_clone_game.py`'s existing fixtures (a fully mocked `db` returning one generic
`MagicMock` from every `db.execute(...)` call, per the current file's `game_service` fixture) cannot
support `create_game`'s many distinct, differently-shaped DB round-trips (template load, guild load,
channel load, host lookup, participant duplicate checks, final reload) once `clone_game` delegates to it.
Restructure the test file around **mocking `self.create_game` itself** rather than mocking every DB call
`create_game` makes internally — `create_game`'s own internal behavior is already fully covered by its
own existing test suite; `clone_game`'s unit tests only need to verify (a) the permission gate is still
enforced, (b) the `GameCreateRequest` payload is built correctly from `clone_data`/`source_game`, (c) the
`default_host_user_id`/`host_user_id` split is passed correctly, and (d) the additive image/deadline steps
run correctly around the delegated call. Use
`with patch.object(game_service, "create_game", AsyncMock(return_value=<a MagicMock GameSession>)) as mock_create:`
and assert on `mock_create.call_args`.

Write these tests first against the not-yet-rewritten `clone_game` (a genuine RED signal: today's
`clone_game` never calls `self.create_game` at all, so `mock_create.assert_called_once_with(...)`
fails outright), then apply Task 4.1, confirm green.

Full-pipeline behaviors that only make sense with `create_game`'s real internals running (template
loading, real mention resolution, real permission role checks) belong in
`tests/integration/test_clone_game_endpoint.py` (Phase 7), not here — do not attempt to re-mock
`create_game`'s internals to test them at the unit level.

- **Files**: `tests/unit/services/test_clone_game.py` (near-total rewrite of its fixtures and test
  bodies; keep the file, do not rename it).
- **Success**: `uv run pytest tests/unit/services/test_clone_game.py -v` green; every test in the file
  either exercises `clone_game`'s own orchestration logic (permission gate, payload construction, host
  identity split, image/deadline additions) via a mocked `create_game`, or has been moved to the
  integration suite.
- **Dependencies**: Task 4.1.

## Phase 5: Re-Add Deadline-Carryover Scheduling (Additive, Submitted-List-Driven)

### Task 5.1: Compute carryover-eligible groups from the source partition, filtered to the final roster

After `clone_game`'s delegated `create_game()` call returns (Task 4.1), add:

```python
partitioned = partition_participants(
    source_game.participants,
    source_game.max_players,
    signup_method=source_game.signup_method,
)
submitted_discord_ids = {p.user.discord_id for p in new_game.participants if p.user}

carry_options = {CarryoverOption.YES, CarryoverOption.YES_WITH_DEADLINE}
players_to_carry = (
    [sp for sp in partitioned.confirmed if sp.user and sp.user.discord_id in submitted_discord_ids]
    if clone_data.player_carryover in carry_options
    else []
)
waitlist_to_carry = (
    [sp for sp in partitioned.overflow if sp.user and sp.user.discord_id in submitted_discord_ids]
    if clone_data.waitlist_carryover in carry_options
    else []
)

await self._apply_deadline_carryover(
    new_game=new_game,
    players_to_carry=players_to_carry,
    waitlist_to_carry=waitlist_to_carry,
    clone_data=clone_data,
)
```

`partition_participants` is called with `source_game.max_players`/`source_game.signup_method` — the
**source's own** values, not any resolved/overridden value — because this computation answers "who was
confirmed/waitlisted in the game being cloned," a fact about the source game only, independent of what the
new game's capacity ends up being (per research lines 169; this also means the `max_players`-into-partition
"ordering hazard" the original research flagged, lines 119-121, does not apply here at all — it was an
artifact of the old roster-construction model, which no longer exists). `_apply_deadline_carryover`,
`_add_participant_carryover_schedules`, and `_process_carryover_group` need **no changes** — they already
only need two lists of source `GameParticipant` rows and match them into `new_game.participants` by
`user_id` (`games.py` line 1114-1116), which works correctly here since both point to the same canonical
`User` row for a given Discord account.

- **Files**:
  - `services/api/services/games.py` — add this block to `clone_game`, after the image-handling block
    from Task 4.1.
  - `tests/unit/services/test_clone_game.py` — add tests (using the `create_game`-mocking pattern from
    Task 4.2, with the mock returning a `GameSession`-shaped object whose `.participants` list is
    controlled by the test): (a) submitting a list that omits a previously-confirmed source participant
    means they get no deadline schedule even with `YES_WITH_DEADLINE`; (b) a submitted brand-new
    participant (no source match) gets no deadline schedule; (c) `player_carryover = NO` with a
    resubmitted source-confirmed participant's mention results in no deadline schedule for them (group
    excluded entirely, regardless of individual match); (d) a full `YES_WITH_DEADLINE` round-trip with all
    source-confirmed participants resubmitted creates deadline schedules for all of them.
- **Success**: All four tests pass; roster membership (already correct "for free" since Phase 4) and
  deadline-schedule creation are both fully determined by `clone_data.participants`, matched against the
  source's own partition by `discord_id`.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 146-153,
    167-169) — the resolved participant-editing decision and its exact carried-forward implementation.
- **Dependencies**: Phase 4.

## Phase 6: Multipart Route + Raw Image Upload, With Ref-Copy Fallback

### Task 6.1: `clone_game` accepts raw image bytes; ref-copy becomes conditional

Extend `clone_game`'s signature to mirror `create_game`'s media parameters:

```python
async def clone_game(
    self,
    source_game_id: str,
    clone_data: CloneGameRequest,
    current_user: auth_schemas.CurrentUser,
    role_service: roles_module.RoleVerificationService,
    thumbnail_data: bytes | None = None,
    thumbnail_mime_type: str | None = None,
    image_data: bytes | None = None,
    image_mime_type: str | None = None,
) -> game_model.GameSession:
```

Pass `thumbnail_data`/`thumbnail_mime_type`/`image_data`/`image_mime_type` straight through to the
delegated `self.create_game(...)` call (Task 4.1) exactly as `create_game`'s own route already does for
itself. Replace Task 4.1's unconditional image-ref-copy block with a conditional one:

```python
if thumbnail_data is None and source_game.thumbnail_id is not None:
    new_game.thumbnail_id = source_game.thumbnail_id
    await increment_image_ref(self.db, source_game.thumbnail_id)
if image_data is None and source_game.banner_image_id is not None:
    new_game.banner_image_id = source_game.banner_image_id
    await increment_image_ref(self.db, source_game.banner_image_id)
if (thumbnail_data is None and source_game.thumbnail_id) or (
    image_data is None and source_game.banner_image_id
):
    self.db.add(new_game)
    await self.db.flush()
```

When `thumbnail_data`/`image_data` is provided, `create_game`'s own `_build_game_session` already calls
`store_image` and sets `thumbnail_id`/`banner_image_id` on `new_game` before returning — the block above
correctly leaves those alone in that case (the `is None` guards skip the ref-copy).

### Task 6.2: Route becomes multipart, mirroring `create_game`'s route

Rewrite `services/api/routes/games.py::clone_game` (lines 903-935) from a plain-JSON-body handler to a
`Form()`/`File()` multipart handler, mirroring `create_game`'s route (lines 377-500) field-for-field for
every `CloneGameRequest` field, plus the four existing clone-specific carryover/deadline `Form()` fields,
plus `thumbnail`/`image` `File()` params:

```python
@router.post("/{game_id}/clone", response_model=game_schemas.GameResponse, status_code=http_status.HTTP_201_CREATED)
async def clone_game(
    game_id: str,
    scheduled_at: Annotated[str, Form()],
    title: Annotated[str | None, Form()] = None,
    description: Annotated[str | None, Form()] = None,
    where: Annotated[str | None, Form()] = None,
    signup_instructions: Annotated[str | None, Form()] = None,
    max_players: Annotated[int | None, Form()] = None,
    expected_duration_minutes: Annotated[int | None, Form()] = None,
    reminder_minutes: Annotated[str | None, Form()] = None,
    signup_method: Annotated[str | None, Form()] = None,
    participants: Annotated[str | None, Form()] = None,
    host: Annotated[str | None, Form()] = None,
    remind_host_rewards: Annotated[bool | None, Form()] = None,
    reminders_as_dms: Annotated[bool | None, Form()] = None,
    post_at: Annotated[str | None, Form()] = None,
    recur_rule: Annotated[str | None, Form()] = None,
    player_carryover: Annotated[str, Form()] = "NO",
    player_deadline: Annotated[str | None, Form()] = None,
    waitlist_carryover: Annotated[str, Form()] = "NO",
    waitlist_deadline: Annotated[str | None, Form()] = None,
    thumbnail: Annotated[UploadFile | None, File()] = None,
    image: Annotated[UploadFile | None, File()] = None,
    *,
    current_user: _CurrentUserDep,
    game_service: _GameServiceDep,
    role_service: _RoleServiceDep,
) -> game_schemas.GameResponse:
    ...
```

Parse `reminder_minutes`/`participants` as JSON arrays (mirroring `create_game`'s route lines 410-416),
`scheduled_at`/`post_at`/`player_deadline`/`waitlist_deadline` via
`datetime.fromisoformat(x.replace("Z", "+00:00"))` (mirroring line 418-421), build a `CloneGameRequest`
from the parsed values, read/validate `thumbnail`/`image` uploads via the existing
`_validate_image_upload` helper (mirroring lines 443-475), and call
`game_service.clone_game(game_id, clone_data, current_user, role_service, thumbnail_data=..., ...)`
inside the same `try: ... except (resolver_module.ValidationError, ValueError) as e:
_handle_game_operation_errors(e, clone_data)` block from Task 4.1.

- **Files**:
  - `services/api/services/games.py` — widen `clone_game`'s signature (Task 6.1).
  - `services/api/routes/games.py` — rewrite the clone route to multipart (Task 6.2).
  - `tests/unit/services/test_clone_game.py` — add tests for the ref-copy-vs-raw-upload branch (using the
    `create_game`-mocking pattern; assert `thumbnail_data`/`image_data` are forwarded to the mocked
    `create_game` call, and that `increment_image_ref` is/isn't called depending on whether the mocked
    `create_game` return value already has a `thumbnail_id` set).
  - `tests/integration/test_clone_game_endpoint.py` — every existing test using
    `authenticated_client.post(..., json={...})` for the clone endpoint must switch to
    `data={...}` (Form fields), mirroring however the equivalent `create_game` integration tests already
    post multipart bodies; add a new test posting a real `thumbnail`/`image` file on a clone request and
    asserting the new game's image is the newly uploaded one (not a reference copy of the source's).
- **Success**:
  - A clone request with no `thumbnail`/`image` file attached still carries over the source's images by
    reference exactly as before (all Phase 4/5 tests continue passing).
  - A clone request with a `thumbnail`/`image` file attached results in the new game having a freshly
    stored image (`increment_image_ref` not called for that field).
  - `cd frontend`-independent: `scripts/run-integration-tests.sh` (scoped, output via `tee`) passes.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 167-168) —
    "Image carry-over by reference ... if no new file is uploaded."
  - Design Note 6 above (`GameForm`'s always-present file inputs) — the reason this phase's scope is
    "raw upload support," not merely "reference copy," which was the entirety of the prior plan draft's
    (and the original research's Technical Requirements section's) image-handling scope.
- **Dependencies**: Phase 4, Phase 5 (this phase touches the same method body and the same route function
  as both; land after both so the route rewrite only has to happen once).

## Phase 7: Full Integration Test Pass Against the New Request Contract

### Task 7.1: Expand `tests/integration/test_clone_game_endpoint.py`

With Phases 1-6 complete, add integration coverage (no TDD stub/xfail — integration tests are written
after the implementation exists, per `.github/instructions/test-driven-development.instructions.md`'s
Integration Tests section) exercising the real HTTP endpoint end-to-end: overriding
`title`/`description`/`max_players`/`signup_method` in one request and asserting the persisted game
reflects every override and that unmentioned fields inherit the source's; a bot-manager `host` override
succeeding and a non-bot-manager attempt failing; a source-host-no-longer-eligible clone attempt failing
with the new, intentional host-role-recheck error (Design Note/"Verified Against Current Code" item 3);
the submitted-participants-drive-roster-and-deadline behavior from Phase 5 exercised over real DB rows
(source game with confirmed+waitlist participants, clone with a submitted list that drops one and adds a
new one, assert final roster order and deadline-schedule rows match Phase 5's semantics); `post_at`
omitted defaults to immediate publish (a `BotActionQueue` row with `action_type="game_created"` exists,
matching today's already-passing `test_clone_game_endpoint_publishes_game_created_event` — this specific
test needs no behavioral change, only its request body's Content-Type per Phase 6); a future `post_at`
results in no immediate `BotActionQueue` row (deferred, per `create_game`'s existing, already-tested
branch); a template deleted out from under a clonable game causes a 404 (Design Note 9).

- **Files**: `tests/integration/test_clone_game_endpoint.py`.
- **Success**: `scripts/run-integration-tests.sh` (scoped appropriately per
  `.github/instructions/test-execution.instructions.md`, output captured with `tee`) passes.
- **Dependencies**: Phases 1-6 all complete.

## Phase 8: Rebuild `CloneGame.tsx` — Two-Stage `GameForm`-Based Screen

### Task 8.1: Stub the new page shape and write failing component tests

Structure `frontend/src/pages/CloneGame.tsx` as two stages within one component:

- **Stage 1** (rendered once `sourceGame` has loaded): a summary of the game being cloned, the existing
  `player_carryover`/`waitlist_carryover` `Select` controls (reuse today's `CARRYOVER_OPTIONS`), the
  conditional `YES_WITH_DEADLINE` deadline `DateTimePicker`s (reuse today's validation), and a "Continue"
  button.
- **Stage 2** (rendered only after "Continue" is clicked): mounts `<GameForm mode="create" ... />` with a
  single, stable `initialData` object computed exactly once (via `useMemo`/lazy `useState` initializer
  keyed on `sourceGame` plus the carryover selections frozen at the moment "Continue" was clicked — not on
  live carryover state afterward) built as: a shallow copy of `sourceGame` with `post_at` cleared so
  `GameForm`'s own default logic leaves the picker empty ("leave empty = post now," honored automatically
  per Phase 6/create_game's existing deferred logic), `scheduled_at` overridden to
  `addDays(new Date(sourceGame.scheduled_at), 14).toISOString()` (preserving today's `DEFAULT_DAYS_AHEAD`
  default), and `confirmed_participants`/`waitlist_participants`/`participants` present or stripped to
  `[]` depending on whether the frozen `playerCarryover`/`waitlistCarryover` were `NO` vs
  `YES`/`YES_WITH_DEADLINE` (`GameForm.buildParticipantList`, lines 185-240, already branches on
  `signup_method === HOST_SELECTED_WITH_WAITLIST`).

The carryover Stage-1 controls remain visible/editable in Stage 2 too (rendered adjacent to `<GameForm>`,
still using their own local state) — changing them after Stage 2 has begun affects only what gets
submitted for deadline-carryover purposes (Phase 9's payload), not the already-mounted `GameForm`'s
participant editor contents, per the Resolved Design Decision.

Build the `channels` prop as a single-item array synthesized directly from
`sourceGame.channel_id`/`sourceGame.channel_name` once `sourceGame` loads (Design Note 7 — **no**
`/guilds/{id}/channels` fetch needed), and determine `isBotManager` via
`canUserManageBotSettings(sourceGame.guild_id)` (`frontend/src/utils/permissions.ts`, the same helper
`CreateGame.tsx` already uses) — both needed as `<GameForm channels={...} isBotManager={...} .../>` props.
**No** `/guilds/{id}/roles` fetch is needed either (Design Note 7 — `GameForm` has no `roles` prop).

Per TDD, write `frontend/src/pages/__tests__/CloneGame.test.tsx`'s new test cases (using `test.failing`
markers per `.github/instructions/test-driven-development.instructions.md`'s TypeScript RED-phase
convention) _before_ rewriting the component: assert Stage 1 renders the carryover selects/deadline
pickers and a "Continue" button; assert clicking "Continue" reveals `GameForm`'s title/description/etc.
fields pre-populated from `sourceGame`; assert toggling `playerCarryover` in Stage 1 before clicking
Continue changes whether Stage 2's participant editor is pre-populated; assert toggling the same select
_after_ Stage 2 has mounted does NOT clear any host-edited title/description text (the direct regression
test for Design Note 5's hazard). All 16 of today's existing test cases (research line 51) test UI that
will no longer exist and must be deleted as part of this same change, not left behind as dead/failing
cruft.

- **Files**:
  - `frontend/src/pages/CloneGame.tsx` — full rewrite.
  - `frontend/src/pages/__tests__/CloneGame.test.tsx` — full rewrite.
- **Success**: New tests fail (`test.failing`) against a minimal stub (component renders only a loading
  spinner and a Stage 1 shell with no `GameForm` mount yet).
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 9-14, 30-37,
    146-153) — `CloneGame.tsx`'s current structure, `GameForm`'s create-mode behavior with real-game
    `initialData`, and the participant-editing decision this stage implements.
- **Dependencies**: Phase 2 (final `CloneGameRequest` field set), though Stage 1/2 rendering has no
  runtime dependency on the backend phases landing first.

### Task 8.2: Implement Stage 1/Stage 2 and remove `test.failing` markers

Implement the component per Task 8.1's design; remove `test.failing` markers; do not modify the test
assertions themselves (only the markers).

- **Files**: same as Task 8.1.
- **Success**: `cd frontend && npm run test` passes for `CloneGame.test.tsx`; `npm run build` succeeds
  with no TypeScript errors.
- **Dependencies**: Task 8.1.

### Task 8.3: Refactor and edge-case tests

Add tests for: `HOST_SELECTED_WITH_WAITLIST` source games (confirms the `confirmed_participants`/
`waitlist_participants` stripping branch, not the `participants` branch); a source game with
`has_thumbnail`/`has_image` true (confirm no crash/no accidental UI — intentionally out of scope per
research's "no image preview exists" finding, just confirm no regression, and that the file-upload inputs
remain empty/optional so the user can still add a _new_ file per Phase 6); fetch-error and loading states
(preserve today's existing `fetchError`/loading behavior).

- **Files**: same as Task 8.1.
- **Dependencies**: Task 8.2.

## Phase 9: Wire `CloneGame.tsx`'s Submit Handler to the Extended Clone Endpoint

### Task 9.1: Write failing submit-handler tests

Add `test.failing`-marked tests asserting the submit handler builds a `multipart/form-data` `FormData`
payload (mirroring `CreateGame.tsx`'s `handleSubmit`, lines 164-249, field-for-field — **not** a JSON
body, per Phase 6) containing: `scheduled_at` (required), and, only when non-empty/non-null (mirroring
`CreateGame.tsx`'s exact "omit if unset, let the backend inherit/default" pattern):
`title`/`description`/`where`/`signup_instructions`/`max_players`/`expected_duration_minutes`/
`signup_method`/`recur_rule`/`post_at`, `reminder_minutes` (JSON-stringified array, always sent, empty
array means "no reminders" exactly as `CreateGame.tsx` does), `participants` (JSON-stringified array,
mapped from `formData.participants` via `p.resolvedMention ?? p.mention.trim()` filtered to non-empty,
mirroring `CreateGame.tsx` lines 219-224 — **not** `EditGame.tsx`'s `participant_id`-based payload, since
the new game has no pre-existing `GameParticipant` rows to reference), `host` (bot-manager only, mirroring
`isBotManager && formData.host && formData.host.trim()`), `thumbnail`/`image` (raw `File` objects, only if
`formData.thumbnailFile`/`imageFile` is set — this is what Phase 6 exists to receive),
`remind_host_rewards`/`reminders_as_dms` (always sent as `'true'`/`'false'`), plus the clone-specific
`player_carryover`/`waitlist_carryover`/`player_deadline`/`waitlist_deadline` from Stage 1's
(possibly-since-changed) live state.

Also test the error-handling path: an `invalid_mentions` 422 response populates `validationErrors`/
`channelValidationErrors`/`validParticipants` state passed into `<GameForm>`, mirroring `CreateGame.tsx`'s
existing handler (lines 253-288) almost verbatim; a plain-message error sets a generic error banner;
success navigates to `/games/${response.data.id}` (preserving today's existing navigation target).

- **Files**: `frontend/src/pages/__tests__/CloneGame.test.tsx`.
- **Success**: New tests fail against Task 8.2's implementation (no real submit wiring yet).
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Lines 38-40) —
    `CreateGame.tsx`'s payload-building pattern used as the template here.
- **Dependencies**: Task 8.2, Phase 6 (final multipart contract, including file fields).

### Task 9.2: Implement the submit handler; remove `test.failing` markers

Implement `handleSubmit(formData: GameFormData)` passed as `<GameForm onSubmit={...} />`, per Task 9.1.

- **Files**: `frontend/src/pages/CloneGame.tsx`.
- **Success**: `cd frontend && npm run test` and `npm run build` both pass.
- **Dependencies**: Task 9.1.

### Task 9.3: Refactor and full end-to-end frontend verification

Confirm the whole Stage 1 → Stage 2 → submit flow renders and submits correctly in a full RTL test
exercising the entire component, and that no field silently fails to round-trip, including a case where a
new thumbnail file is attached (asserting the outgoing `FormData` contains a `thumbnail` file part, not
just text fields).

- **Files**: `frontend/src/pages/__tests__/CloneGame.test.tsx`.
- **Dependencies**: Task 9.2.

## Phase 10: Update the E2E Test to Reflect Title-At-Clone-Time

### Task 10.1: Remove the post-clone rename workaround from the e2e test

`tests/e2e/test_clone_game_e2e.py` currently does a separate `PUT` immediately after cloning specifically
to rename the game "so our DM check can find it by title" (research lines 155-161) — a live illustration
of exactly the UX problem this whole redesign fixes. Update the test to set the desired title directly in
the clone request's `title` override field (now a multipart Form field, per Phase 6), removing the
follow-up `PUT` entirely, and switch the clone request itself from a JSON body to a multipart form post if
the e2e test drives the HTTP layer directly rather than through the rebuilt UI.

- **Files**: `tests/e2e/test_clone_game_e2e.py`.
- **Success**: `scripts/run-e2e-tests.sh` (output captured with `tee`, per
  `.github/instructions/test-execution.instructions.md`) passes with the simplified single-request flow.
- **Research References**:
  - .copilot-tracking/research/20260915-01-clone-game-review-redesign-research.md (Line 55) — the exact
    rename-workaround this task removes.
- **Dependencies**: All prior phases (exercises the fully-implemented feature end-to-end).

## Dependencies

- Python: pytest, mypy, Pydantic v2, SQLAlchemy async session patterns already used throughout
  `services/api/services/games.py`. No new external dependencies.
- TypeScript/React: Vitest/RTL (`test.failing`), MUI `DateTimePicker`/`Select`, existing
  `EditableParticipantList`/`GameForm` components (unmodified).
- No database migration required — every touched column already exists on `GameSession`; only
  Pydantic/TypeScript request-shape fields and one shared-regex fix are added.

## Success Criteria

- A host can clone a game, edit every field `GameForm` exposes (title, description, where, max players,
  reminders, duration, signup method, host override, recurrence, posting time, and optionally a new
  thumbnail/banner image) plus the clone-specific carryover/deadline options and the participant roster,
  and submit once — nothing is created server-side until that submit.
- `clone_game` delegates the entire mechanical pipeline (template loading, host resolution, free-text
  mention/channel/emoji resolution, participant resolution and creation, deferred/immediate publish) to
  `create_game`, adding only two genuinely new, additive steps: image carry-over-by-reference when no new
  file is uploaded, and deadline-carryover scheduling re-derived from the submitted roster matched against
  the source game's own confirmed/waitlist partition by `discord_id`.
- The host-role-permission recheck against the carried-over/overridden host is a real, intentional,
  tested behavior change from today (Design Note/"Verified" item 3) — not bypassed.
- Every cloned game has a concrete, non-NULL `post_at` and correct deferred/immediate publish behavior,
  achieved entirely via delegation with no clone-specific publish code remaining.
- All updated/added unit, integration, and e2e tests pass; `uv run mypy shared/ services/` passes;
  `cd frontend && npm run build` and `npm run test` pass.

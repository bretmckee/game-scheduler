<!-- markdownlint-disable-file -->

# Changes: Clone Game Review/Edit-Before-Create Redesign

## Summary

Tracks implementation of the 10-phase clone-game redesign (GameForm-based review/edit-before-create
clone screen delegating to `create_game`). This file is updated as each phase completes.

## Phase 1: Fix `resolve_mentions_in_text`'s Regex To Skip Already-Resolved `<@id>` Tokens

Bug fix: `resolve_mentions_in_text`'s mention-token regex (`@\w+(?:\.\w+)*`) matched the `@<id>`
substring inside an already-resolved Discord mention token (`<@discord_id>`), causing it to be
re-parsed as an unresolved `@<id>` username and produce a spurious "User not found" validation
error. Fixed by adding a `(?<!<)` negative lookbehind, mirroring the identical exclusion already
used by `channel_resolver.py`'s `#`-mention regex (`(?<!<)#([^\s<>#]+)`). This is a prerequisite
for Phase 4's delegation, which will unconditionally re-run mention resolution against inherited
free-text fields that may already contain resolved mentions.

### Added

- `tests/unit/services/api/services/test_participant_resolver.py` — three new regression tests for
  `resolve_mentions_in_text` (Task 1.1):
  - `test_resolve_mentions_in_text_skips_already_resolved_mention` — RED case; written first with
    `@pytest.mark.xfail(strict=True)`, confirmed `XFAIL` before the fix, marker removed after
  - `test_resolve_mentions_in_text_mixed_resolved_and_unresolved` — RED case (mixed `<@111>` and
    `@bob` in one string); same xfail→remove cycle
  - `test_resolve_mentions_in_text_real_mention_still_resolved` — regression guard for
    already-correct behavior (plain `@alice` mention); written to pass immediately, no xfail

### Modified

- `services/api/services/participant_resolver.py` (`resolve_mentions_in_text`) — changed
  `tokens = re.findall(r"@\w+(?:\.\w+)*", text)` to
  `tokens = re.findall(r"(?<!<)@\w+(?:\.\w+)*", text)`; updated the surrounding comment and the
  method's docstring to document the exclusion (Task 1.1)

### Verification

- `uv run pytest tests/unit` — 2580 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 2: Extend `CloneGameRequest` With Override Fields, `post_at`, and `participants`

Added 14 new optional fields to `CloneGameRequest` (13 nullable overrides plus `participants`,
which defaults to `[]` rather than `None`), copied verbatim from `GameCreateRequest`'s field
constraints (`shared/schemas/game.py`). These are pure schema additions — nothing reads them yet
(that starts in Phase 4's `clone_game` delegation). No `channel_id`, `rewards`,
`allowed_player_role_ids`, or `notify_role_ids` fields were added, per the details file's Design
Note 4 (none of these are overridable anywhere in the system today). No `signup_method` value
validator or `post_at < scheduled_at` validator was added to `CloneGameRequest` itself — both are
already enforced for free when `clone_game` constructs the delegated `GameCreateRequest` in
Phase 4.

### Added

- `tests/unit/schemas/test_clone_game_schema.py` — five new tests for the new fields (Task 2.2):
  - `test_clone_request_accepts_override_fields` — RED case; written first with
    `@pytest.mark.xfail(strict=True)`, confirmed `XFAIL` before the fields were added, marker
    removed after; constructs a `CloneGameRequest` with all 14 new fields set and asserts each
    stored value
  - `test_clone_request_override_fields_default_to_none_when_omitted` — RED case; same
    xfail→remove cycle; confirms the 13 nullable fields default to `None` when omitted
    (backward compatibility with every existing caller)
  - `test_clone_request_participants_defaults_to_empty_list` — RED case; same xfail→remove
    cycle; confirms `participants` defaults to `[]`, not `None`, when omitted
  - `test_clone_request_title_exceeds_max_length_is_rejected` — RED case; same xfail→remove
    cycle; regression guard that `title`'s `max_length=200` constraint (copied from
    `GameCreateRequest`) is actually enforced, not just a bare `str | None` type hint
  - `test_clone_request_max_players_out_of_range_is_rejected` — RED case; same xfail→remove
    cycle; same regression guard for `max_players`'s `ge=1, le=100` constraint

### Modified

- `services/api/schemas/clone_game.py` (`CloneGameRequest`) — added `title`, `description`,
  `signup_instructions`, `where`, `max_players`, `reminder_minutes`, `expected_duration_minutes`,
  `signup_method`, `participants`, `host`, `remind_host_rewards`, `reminders_as_dms`, `post_at`,
  `recur_rule` fields (Task 2.1)

### Verification

- `uv run pytest tests/unit/schemas/test_clone_game_schema.py -v` — 5 new tests confirmed
  `XFAIL` before the field additions, all 12 tests `PASSED` after (xfail markers removed)
- `uv run pytest tests/unit` — 2585 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 3: Add `default_host_user_id` To `create_game`/`_resolve_game_host`

Added a new, optional `default_host_user_id: str | None = None` parameter to both
`_resolve_game_host` and `create_game`, threaded through unchanged. This decouples "who is
performing the request" (the bot-manager-permission-check subject, still `requester_user_id`/
`host_user_id`) from "who the game's host should default to when no `host` override is
specified" (previously always the requester). `clone_game` (Phase 4) will pass
`source_game.host_id` as `default_host_user_id` while still passing `current_user`'s ID as
`host_user_id`, so a bot-manager-only host override on a clone is still checked against the
cloning user, not the source game's host. Purely additive: when the new parameter is omitted
(both existing call sites — `services/api/routes/games.py`'s `create_game` route, and
`create_game`'s internal call to `_resolve_game_host`), behavior is byte-for-byte identical to
before, since `default_host_user_id` defaults to `None`, which falls back to
`requester_user_id`/`host_user_id` exactly as the old unconditional assignment did.

### Added

- `tests/unit/services/api/services/test_games_service.py` — two new tests for
  `_resolve_game_host` (Task 3.1):
  - `test_resolve_game_host_default_host_user_id_used_when_no_override` — RED case; written
    first with `@pytest.mark.xfail(strict=True)` (confirmed `XFAIL` against pre-Phase-3 code,
    since `_resolve_game_host` didn't accept the keyword yet), marker removed after the change;
    asserts that with no `host` override, the resolved host is `default_host_user_id`, not the
    requester
  - `test_resolve_game_host_default_host_user_id_does_not_change_permission_subject` — RED case;
    same xfail→remove cycle; with a `host` override set and `default_host_user_id` also passed,
    asserts the override still wins and `check_bot_manager_permission` was called with the
    requester's `discord_id` (not the default host's) — confirming the two identities stay
    decoupled

### Modified

- `services/api/services/games.py` — `_resolve_game_host` gained `default_host_user_id: str |
None = None`; `actual_host_user_id` now initializes from
  `default_host_user_id if default_host_user_id is not None else requester_user_id` instead of
  unconditionally from `requester_user_id`. `create_game` gained the same parameter (positioned
  after `host_user_id`) and forwards it to `_resolve_game_host`. Docstrings updated on both
  methods. No call sites changed — both existing calls use keyword arguments unaffected by the
  new parameter's position, or omit it and get identical behavior. Not yet wired to
  `clone_game` (Phase 4's job).

### Verification

- `uv run pytest tests/unit/services/api/services/test_games_service.py -k default_host_user_id -v`
  — 2 new tests confirmed `XFAIL` before the parameter was added, both `PASSED` after (xfail
  markers removed)
- `uv run pytest tests/unit` — 2587 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 4: Rewrite `clone_game` To Delegate To `create_game`; Wire Route-Level `ValidationError` Handling

Replaced `clone_game`'s ~140-line body (verbatim field-copy `GameSession` construction, its own
`partition_participants`-driven roster build, its own unconditional `_setup_game_schedules`/
`_publish_game_created` calls) with construction of a fully-resolved `GameCreateRequest` (reusing
`source_game.template_id`, falling back to `source_game`'s value for every field `clone_data` left
unset) and delegation to `create_game`, passing `host_user_id=current_user.user.id` and the Phase
3 `default_host_user_id=source_game.host_id`. This means `clone_game` now re-runs `create_game`'s
own host-role-permission check against the carried-over/overridden host — an intentional behavior
change per the research doc, not a bypass. Image carry-over-by-reference
(`increment_image_ref`/`thumbnail_id`/`banner_image_id`) is layered on unconditionally afterward as
the one still-irreducible additive step for this phase; deadline-carryover scheduling remains
unwired until Phase 5 (`_apply_deadline_carryover`/`_add_participant_carryover_schedules`/
`_process_carryover_group` were kept unchanged and unremoved, per the plan, for Phase 5 to reuse).
The route's clone endpoint now shares `_handle_game_operation_errors` with the create/update
routes instead of a hand-rolled `except ValueError` block, so a `resolver_module.ValidationError`
raised by the delegated `create_game` call (e.g. an unresolvable `@mention` in an overridden field)
now correctly surfaces as 422 `invalid_mentions` instead of an unhandled 500.

Fixing this exposed a pre-existing test-fixture gap: `tests/integration/test_clone_game_endpoint.py`
and `tests/integration/test_recurrence_clone.py` both created/inserted source games with
`template_id=None` (harmless for the old field-copy `clone_game`, which never validated
`template_id`, but a hard failure once `clone_game` builds a `GameCreateRequest`, whose
`template_id` is a required string consumed by `create_game`'s real template-loading step). Fixed
by passing a real `template_id` from each test's already-created template fixture.

Two existing integration tests assert behavior this phase intentionally does not implement yet and
are marked `@pytest.mark.skip` with a reason pointing at Phase 5/Phase 7, rather than deleted or
silently left broken:

- `test_clone_game_endpoint_yes_carryover_copies_new_game_participants` — asserted server-side
  `player_carryover: YES` roster construction, which no longer exists in `clone_game` (Phase 5
  re-adds a submitted-list-driven equivalent; Phase 7 restores/rewrites this scenario against the
  final contract).
- `test_clone_game_endpoint_yes_with_deadline_creates_action_and_notification_schedules` — asserted
  `_apply_deadline_carryover` being invoked by `clone_game`, which Phase 5 re-adds as an additive
  step.

### Added

- `tests/integration/test_clone_game_endpoint.py` —
  `test_clone_game_endpoint_unresolvable_mention_in_override_returns_422`: new case per the details
  file's Task 4.1 file list — an unresolvable `@mention` in an overridden `description` returns 422
  with `error: "invalid_mentions"` (Task 4.1).
- `tests/unit/services/test_clone_game.py` — 9 new tests replacing the delegation-mocking gap (Task
  4.2), all written first against the not-yet-rewritten `clone_game` and confirmed as a genuine RED
  signal (`mock_create.assert_called_once_with(...)`-style assertions failing outright since the old
  `clone_game` never called `self.create_game`), then confirmed GREEN after Task 4.1:
  - `test_clone_game_builds_payload_from_source_when_no_overrides` — every `GameCreateRequest` field
    falls back to `source_game`'s value when `clone_data` leaves it unset
  - `test_clone_game_overridden_fields_use_clone_data` — every override field wins over the
    corresponding source value
  - `test_clone_game_omitting_host_decouples_default_host_from_requester` — confirms
    `host_user_id`/`default_host_user_id` stay decoupled (requester vs. source host)
  - `test_clone_game_copies_images_by_reference_when_source_has_images` — both image ids copied
    onto the returned game, `increment_image_ref` awaited twice, `db.add`/`db.flush` called
  - `test_clone_game_skips_image_ref_increment_when_source_has_no_images` — no image-related DB
    writes when the source has neither image
  - `test_clone_game_propagates_create_game_value_error` — a `ValueError` from the delegated
    `create_game` call (e.g. deleted template) propagates unchanged
  - `test_clone_game_propagates_create_game_validation_error` — a `resolver_module.ValidationError`
    from the delegated call propagates unchanged
  - `test_clone_game_source_not_found_raises_value_error`, `test_clone_game_non_host_raises_value_error`
    — retained/adapted permission-gate regression tests (now also assert `create_game` is never
    called when the gate rejects)

### Modified

- `services/api/services/games.py` (`clone_game`) — full rewrite per Task 4.1: builds a
  `GameCreateRequest` from `clone_data`/`source_game` fallbacks, delegates to
  `self.create_game(game_data, host_user_id=current_user.user.id, default_host_user_id=source_game.host_id)`,
  then unconditionally carries over `thumbnail_id`/`banner_image_id` by reference. Old body
  (verbatim `GameSession(...)` construction, `partition_participants`-driven carryover loop,
  `_setup_game_schedules`, `_apply_deadline_carryover` call, `_publish_game_created` call) deleted.
  `_apply_deadline_carryover`, `_add_participant_carryover_schedules`, `_process_carryover_group`
  left unchanged, per the plan, for Phase 5.
- `services/api/routes/games.py` — `_handle_game_operation_errors`'s `form_data` type union widened
  to include `CloneGameRequest`; the clone route's `try/except ValueError` replaced with
  `except (resolver_module.ValidationError, ValueError) as e: _handle_game_operation_errors(e, clone_data)`,
  matching the `create_game`/`update_game` routes' pattern (Task 4.1).
- `tests/unit/services/test_clone_game.py` — near-total rewrite of fixtures and test bodies per
  Task 4.2: `game_service` fixture no longer needs the old generic `db.execute` MagicMock tailored
  to the old body (kept as-is since `_apply_deadline_carryover`'s direct-invocation tests still use
  it); all `clone_game`-level tests now use `patch.object(game_service, "create_game", AsyncMock(...))`
  instead of mocking every DB round-trip. The four `_apply_deadline_carryover` direct-invocation
  tests (unaffected by the `clone_game` rewrite, since that method itself is untouched) were kept
  unchanged. Net: 14 tests → 13 tests (11 old `clone_game`-body tests replaced by 9 new
  delegation-mocking tests; 4 `_apply_deadline_carryover` tests retained as-is; 1 net fewer test in
  the file, reflected in the `uv run pytest tests/unit` total below).
- `tests/integration/test_clone_game_endpoint.py` — added `template_id=env["template"]["id"]` to
  all five `create_game(...)` calls (previously omitted; harmless under the old `clone_game`, a hard
  failure under the new `create_game`-delegating one); added `@pytest.mark.skip` (with reason) to
  the two carryover/deadline tests described above; added the new
  `test_clone_game_endpoint_unresolvable_mention_in_override_returns_422` case.
- `tests/integration/test_recurrence_clone.py` — `_insert_game_with_recur_rule` gained an optional
  `template_id: str | None = None` parameter, included in the raw `INSERT`;
  `test_recur_rule_propagated_through_clone_endpoint` now creates a real template via
  `create_template` and passes its id, since the source game it clones now goes through
  `create_game`'s template-loading step (outside this task's originally-listed file set — called
  out here as a divergence: this was a pre-existing test-fixture gap only exposed by Phase 4's
  delegation, not a change anticipated by the details file's Task 4.1 file list).

### Verification

- `uv run pytest tests/unit/services/test_clone_game.py -v` — all 9 new orchestration tests
  confirmed failing against the not-yet-rewritten `clone_game` (genuine RED: `create_game` never
  called), then all 13 tests in the file `PASSED` after Task 4.1's rewrite
- `uv run pytest tests/unit` — 2586 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files
- `scripts/run-integration-tests.sh` (scoped to `tests/integration/test_clone_game_endpoint.py`) —
  4 passed, 2 skipped
- `scripts/run-integration-tests.sh` (scoped to `tests/integration/test_recurrence_clone.py`) —
  4 passed
- `scripts/run-integration-tests.sh` (full suite) — 347 passed, 2 skipped, 2731 deselected

## Phase 5: Re-Add Deadline-Carryover Scheduling (Additive, Submitted-List-Driven)

Added the one additive block Phase 4 deliberately deferred: after the delegated
`create_game()` call returns, `clone_game` now computes carryover-eligible
groups from the **source game's own** confirmed/overflow partition
(`partition_participants(source_game.participants, source_game.max_players,
signup_method=source_game.signup_method)` — the source's own values, not any
resolved/overridden value, since this answers "who was confirmed/waitlisted in
the game being cloned," a fact about the source game alone), filters each
group down to the discord_ids actually present in `new_game.participants`
(the roster `create_game` already built "for free" from the submitted
`clone_data.participants` list), and calls the unchanged
`_apply_deadline_carryover` with the two filtered lists. `partition_participants`
and `_apply_deadline_carryover`/`_add_participant_carryover_schedules`/
`_process_carryover_group` required no changes — the latter three already only
need two lists of source `GameParticipant` rows matched into
`new_game.participants` by `user_id`, which works unchanged since both point
to the same canonical `User` row for a given Discord account. Roster
membership was already fully determined by `clone_data.participants` as of
Phase 4; this phase makes deadline-schedule creation match that same
submitted-list-driven model, rather than the old carryover-flag-driven
roster-construction model Phase 4 removed.

### Added

- `tests/unit/services/test_clone_game.py` — 4 new tests (Task 5.1), all
  written first against the not-yet-updated `clone_game` and confirmed
  `XFAIL` (`strict=True`) before the change, then confirmed `PASSED` after —
  the two negative-outcome tests use `patch.object(game_service,
"_apply_deadline_carryover", new=AsyncMock(wraps=...))` (rather than a bare
  "nothing was added" assertion, which would have trivially held even before
  Phase 5 wired the call at all) so the RED phase is a genuine signal:
  - `test_clone_game_deadline_carryover_omitted_participant_gets_no_schedule`
    — a source-confirmed participant left out of the submitted roster gets no
    deadline schedule even with `player_carryover=YES_WITH_DEADLINE`
    (`_apply_deadline_carryover` called with `players_to_carry=[]`)
  - `test_clone_game_deadline_carryover_new_participant_gets_no_schedule` — a
    submitted participant with no source-partition match (brand-new addition)
    gets no deadline schedule
  - `test_clone_game_deadline_carryover_excludes_group_regardless_of_match` —
    `player_carryover=NO` excludes the confirmed-player group entirely even
    when that source-confirmed player is resubmitted, while a sibling
    `waitlist_carryover=YES_WITH_DEADLINE` group with its own resubmitted
    participant is scheduled normally (proves group-level exclusion, not
    merely "no deadlines configured at all")
  - `test_clone_game_deadline_carryover_full_round_trip_schedules_both_groups`
    — with both groups resubmitted and both `YES_WITH_DEADLINE`, every
    resubmitted source-confirmed/waitlisted participant gets a
    `ParticipantActionSchedule` and `clone_confirmation` `NotificationSchedule`
- `tests/unit/services/test_clone_game.py` — `_new_participant_mock` and
  `_schedules_from_add_calls` helpers for building submitted-roster
  participant mocks and extracting typed schedule objects from
  `db.add.call_args_list`, shared by the four new tests.

### Modified

- `services/api/services/games.py` (`clone_game`) — added the Task 5.1 block
  after the existing image-carryover step: `partition_participants` call
  against `source_game`, `submitted_discord_ids` set built from
  `new_game.participants`, `players_to_carry`/`waitlist_to_carry` list
  comprehensions gated on `clone_data.player_carryover`/`waitlist_carryover`
  being `YES` or `YES_WITH_DEADLINE`, and the `_apply_deadline_carryover`
  call — verbatim per the details file's Task 5.1 spec. No changes to
  `_apply_deadline_carryover`, `_add_participant_carryover_schedules`, or
  `_process_carryover_group`.
- `tests/unit/services/test_clone_game.py` — moved the `DEADLINE` constant
  next to `SCHEDULED_AT`/`CLONE_AT` (previously defined lower in the file,
  just above the pre-existing `_apply_deadline_carryover` direct-invocation
  tests) so the new Phase 5 tests can share it; updated the module docstring
  to describe the Phase 5 additions.
- `tests/integration/test_clone_game_endpoint.py` — removed the two
  `@pytest.mark.skip` markers left by Phase 4 and updated both tests for the
  submitted-list-driven contract (previously they only set
  `player_carryover`/`waitlist_carryover` and relied on `clone_game` to
  construct the roster server-side, which no longer happens as of Phase 4):
  - `test_clone_game_endpoint_yes_carryover_copies_new_game_participants` —
    added a `<@discord_id>` mention for the pre-inserted source participant
    to the request's new `participants` field, and seeded a minimal guild
    member-projection cache entry (via the new `_seed_guild_member` helper)
    so `create_game`'s real participant-resolution pipeline can resolve that
    mention without a real Discord call; updated the docstring to explain
    that roster membership now comes from the submitted list, with
    `player_carryover` only controlling deadline-carryover eligibility.
  - `test_clone_game_endpoint_yes_with_deadline_creates_action_and_notification_schedules`
    — same `participants` field + member-projection seeding addition;
    updated docstring accordingly.
  - Added the `_seed_guild_member` module-level helper (mirrors the
    `_seed_guild_member_projection` pattern already used by
    `tests/integration/test_games_crud.py`, adapted for `<@discord_id>`
    internal-mention-format resolution, which only needs the `proj_member`
    cache key and not the `proj_usernames` sorted set that `@username`
    resolution requires) and the `asyncio`/`RedisClient`/`CacheKeys` imports
    it needs.

### Verification

- `uv run pytest tests/unit/services/test_clone_game.py -v` — the 4 new
  tests confirmed `XFAIL` against pre-Task-5.1 `clone_game`, all 17 tests in
  the file `PASSED` after the change
- `uv run pytest tests/unit` — 2590 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source
  files
- `uv run ruff check services/api/services/games.py
tests/unit/services/test_clone_game.py tests/integration/test_clone_game_endpoint.py`
  — All checks passed
- `scripts/run-integration-tests.sh tests/integration/test_clone_game_endpoint.py`
  — 6 passed, 0 skipped (confirms both previously-skipped tests now pass for
  real, un-skipped)
- `scripts/run-integration-tests.sh` (full suite) — 349 passed, 0 skipped,
  2735 deselected — no regressions elsewhere

## Phase 6: Multipart Route + Raw Image Upload, With Ref-Copy Fallback

Widened `clone_game`'s signature with the same four media parameters
`create_game` already accepts (`thumbnail_data`/`thumbnail_mime_type`/
`image_data`/`image_mime_type`, all optional, default `None`), forwarded
straight through to the delegated `self.create_game(...)` call unchanged.
Replaced the unconditional image-reference-copy block (added in Phase 4)
with two independent per-field guards, each keyed on `thumbnail_data is
None`/`image_data is None`: when a new file is uploaded for a field,
`create_game`'s own `_build_game_session` has already called `store_image`
and set that field on the returned game, so the guard leaves it alone and
skips `increment_image_ref` for that field; when no new file is uploaded for
a field and the source game has an image there, the prior ref-copy-and-
increment behavior applies unchanged. The `db.add`/`db.flush` step now only
runs when at least one field actually needed a ref-copy. Rewrote the
`POST /{game_id}/clone` route from a plain-JSON-body handler to a
`Form()`/`File()` multipart handler, field-for-field mirroring
`create_game`'s own route: every `CloneGameRequest` field becomes a `Form()`
parameter (parsing `reminder_minutes`/`participants` as JSON via
`json.loads`, `scheduled_at`/`post_at`/`player_deadline`/`waitlist_deadline`
via `datetime.fromisoformat(x.replace("Z", "+00:00"))`, and
`player_carryover`/`waitlist_carryover` explicitly coerced to
`CarryoverOption` for mypy), plus `thumbnail`/`image` `File()` params read
and validated via the existing `_validate_image_upload` helper exactly as
`create_game`'s route already does, all inside the same
`try: ... except (resolver_module.ValidationError, ValueError) as e:
_handle_game_operation_errors(e, clone_data)` block from Phase 4.

Converting the route to multipart broke every other test that posted to the
clone endpoint with a JSON body (`Content-Type: application/json` against a
handler now expecting `multipart/form-data`/`application/x-www-form-urlencoded`
Form fields). Fixed by switching each to `data={...}` (JSON-encoding any list
field, e.g. `participants`, via `json.dumps`) and updating two route-level
unit test files that called `games_routes.clone_game(...)` directly with the
old `clone_data=` keyword argument:

- `tests/integration/test_clone_game_endpoint.py` — all six existing
  `json={...}` clone POSTs switched to `data={...}`; `participants` fields
  JSON-encoded via `json.dumps`.
- `tests/integration/test_recurrence_clone.py` — one clone POST switched
  from `json=` to `data=`.
- `tests/integration/test_games_crud.py` — `test_clone_game_not_found`'s
  clone POST switched from `json=` to `data=`.
- `tests/integration/test_rewards_fields.py` — three clone POSTs (rewards,
  `remind_host_rewards`, `reminders_as_dms` carryover tests) switched from
  `json=` to `data=`.
- `tests/e2e/test_clone_game_e2e.py` — one clone POST switched from `json=`
  to `data=` (mechanical fix only, tied directly to this phase's route
  content-type change; the file's deeper rewrite, including the post-clone
  rename workaround, remains Phase 10's scope and this test is not part of
  Phase 6's gates).
- `tests/unit/services/api/routes/test_games_endpoint_errors.py` and
  `tests/unit/services/api/routes/test_games_routes.py` — the four
  `TestCloneGame`/`TestCloneGameRouteCanManage` tests that called
  `games_routes.clone_game(...)` directly now pass `scheduled_at=` (a plain
  Form-shaped string) instead of a `clone_data=CloneGameRequest(...)` object;
  the now-unused `clone_data` fixture and `CloneGameRequest`/
  `CarryoverOption` imports were removed from both files.

The Python diff-coverage pre-commit gate (unit-test coverage only, measured
against `origin/develop`) initially failed at 81% on
`services/api/routes/games.py`: the new route's `if thumbnail:`/`if image:`
truthy branches (validate, read, log) were exercised only by the Phase 6
integration test, which doesn't feed unit-test coverage.xml. Fixed by adding
`test_clone_game_route_reads_and_forwards_uploaded_images` to
`tests/unit/services/api/routes/test_games_routes.py` (retrofit test for
already-correct code, per that instruction file's rule — no xfail needed):
builds two real `UploadFile`s via a new local `_mock_upload_file` helper
(mirroring `test_games_image_validation.py`'s pattern), calls
`games_routes.clone_game(...)` directly with both, and asserts
`thumbnail_data`/`thumbnail_mime_type`/`image_data`/`image_mime_type` are
forwarded correctly to the mocked `game_service.clone_game`. Diff coverage
is 100% after this addition.

The `complexipy` pre-commit gate then failed on the route's `clone_game`
function (cognitive complexity 18, threshold 15) because of the two
duplicated validate-read-log blocks for thumbnail/image. Fixed by reusing
the existing `_process_image_upload` helper (already used by `update_game`'s
route for the same purpose, with `remove_flag=False` since clone has no
image-removal option) instead of inlining the logic a second time --
`complexipy` reports no functions over the threshold afterward.

### Added

- `tests/unit/services/test_clone_game.py` — 3 new tests (Task 6.1), all
  written first against the not-yet-widened `clone_game` and confirmed
  `XFAIL` (`strict=True`) before the change, then confirmed `PASSED` after:
  - `test_clone_game_forwards_media_params_to_create_game` — asserts
    `thumbnail_data`/`thumbnail_mime_type`/`image_data`/`image_mime_type`
    are forwarded unchanged to the mocked `create_game` call
  - `test_clone_game_skips_ref_copy_for_fields_with_new_upload` — with both
    a new thumbnail and a new image uploaded (and the mocked `create_game`
    return value already carrying freshly-uploaded ids, simulating its own
    `_build_game_session`/`store_image` step), asserts both fields are left
    untouched, `increment_image_ref` is never awaited, and no `db.add`/
    `db.flush` occurs
  - `test_clone_game_ref_copies_banner_only_when_only_thumbnail_uploaded` —
    a mixed case (new thumbnail uploaded, no new banner image) asserts the
    thumbnail is left alone while the banner is still ref-copied from the
    source by reference, proving the two guards are independent
- `tests/integration/test_clone_game_endpoint.py` —
  `test_clone_game_endpoint_with_uploaded_thumbnail_uses_new_image_not_ref_copy`:
  creates a source game with a real thumbnail via `POST /api/v1/games`,
  clones it with a different thumbnail file attached, and asserts the new
  game's `thumbnail_id` differs from the source's and that the source
  image's `reference_count` stays at 1 (proving no ref-copy occurred for the
  uploaded field).

### Modified

- `services/api/services/games.py` (`clone_game`) — signature gained
  `thumbnail_data`/`thumbnail_mime_type`/`image_data`/`image_mime_type`
  (all optional, default `None`), forwarded to the delegated `create_game`
  call; the Phase 4 unconditional image-ref-copy block replaced with the
  two independent conditional guards described above (Task 6.1).
- `services/api/routes/games.py` — `clone_game` route rewritten from a
  `clone_data: CloneGameRequest` JSON-body parameter to the full set of
  `Form()`/`File()` parameters mirroring `create_game`'s route, including
  parsing, `CloneGameRequest` construction, and forwarding the media data
  to `game_service.clone_game(...)` (Task 6.2); thumbnail/image validation
  and reading reuses the existing `_process_image_upload` helper (already
  used by `update_game`'s route) with `remove_flag=False`, rather than
  inlining the validate-read-log logic a second time -- required to keep
  `clone_game`'s cognitive complexity under the `complexipy` gate's
  threshold; added `CarryoverOption` to the existing
  `from services.api.schemas.clone_game import ...` import.
- `tests/unit/services/api/routes/test_games_endpoint_errors.py`,
  `tests/unit/services/api/routes/test_games_routes.py` — updated direct
  route-function calls and pruned now-unused fixtures/imports, as described
  above.
- `tests/integration/test_clone_game_endpoint.py`,
  `tests/integration/test_recurrence_clone.py`,
  `tests/integration/test_games_crud.py`,
  `tests/integration/test_rewards_fields.py`,
  `tests/e2e/test_clone_game_e2e.py` — clone-endpoint POST calls switched
  from `json=` to `data=` (multipart/form-encoded), as described above.

### Verification

- `uv run pytest tests/unit/services/test_clone_game.py -v` — the 3 new
  tests confirmed `XFAIL` against pre-Task-6.1 `clone_game`, all 20 tests in
  the file `PASSED` after the change
- `uv run pytest tests/unit` — 2594 passed
- `uv run mypy shared/ services/` — Success: no issues found in 155 source
  files
- `uv run ruff check services/ tests/` — All checks passed
- `scripts/run-integration-tests.sh tests/integration/test_clone_game_endpoint.py`
  — 7 passed (6 previously-passing tests plus the new upload-vs-ref-copy
  test)
- `scripts/run-integration-tests.sh` (full suite) — 350 passed, 0 skipped,
  2738 deselected — no regressions elsewhere
- diff-cover against `origin/develop`: `services/api/routes/games.py`,
  `services/api/schemas/clone_game.py`, `services/api/services/games.py`,
  `services/api/services/participant_resolver.py` all 100% (54/54 lines)

## Phase 7: Full Integration Test Pass Against the New Request Contract

Expanded `tests/integration/test_clone_game_endpoint.py` (no TDD stub/xfail cycle -- integration
tests are written after the implementation exists, per this phase's designation as
integration-only) with 7 new end-to-end HTTP tests closing the coverage gaps Phases 1-6 left open
per the details file's Task 7.1 spec. Reviewed the file's 7 existing tests first (basic 201, 403
non-host, `game_created` event publish, YES carryover roster, YES_WITH_DEADLINE schedules,
unresolvable-mention 422, uploaded-thumbnail-vs-ref-copy) to avoid duplicating coverage; every new
test below exercises a scenario none of those touched.

### Added

- `tests/integration/test_clone_game_endpoint.py` — 7 new tests (Task 7.1):
  - `test_clone_game_endpoint_field_overrides_apply_and_unmentioned_fields_inherit` — overrides
    `title`/`description`/`max_players`/`signup_method` in one request and asserts the persisted
    game reflects every override while an unmentioned field (`where`, set to a distinguishing
    source-only value beforehand) inherits `source_game`'s own value, not a default
  - `test_clone_game_endpoint_bot_manager_host_override_succeeds` — a bot manager overriding `host`
    with a valid `<@discord_id>` mention gets that user as the new game's host; confirms the
    Phase 3/4 host-role recheck is correctly skipped for an overridden host against a template with
    no `allowed_host_role_ids`
  - `test_clone_game_endpoint_non_bot_manager_host_override_returns_403` — a non-bot-manager host
    attempting to override `host` while cloning their own game is rejected with
    `_verify_bot_manager_permission`'s "Only bot managers..." error (403), exactly as `create_game`
    rejects it today
  - `test_clone_game_endpoint_source_host_no_longer_eligible_returns_403` — regression test for the
    new, intentional host-role recheck (Design Note/"Verified Against Current Code" item 3): a
    non-bot-manager source-game host with no qualifying role clones their own game (no host
    override, so `can_manage_game`'s host-of-own-game path admits the request) and is rejected by
    `create_game`'s delegated `check_game_host_permission` recheck; also asserts no new game row was
    created
  - `test_clone_game_endpoint_deleted_template_returns_404` — regression test for Design Note 9's
    accepted trade-off. Since `game_sessions.template_id`'s plain FK normally prevents deleting a
    referenced template, the test genuinely deletes the template anyway by momentarily dropping and
    restoring (as `NOT VALID`, since the source game's own row is intentionally left dangling) the
    FK constraint around the delete -- driving `clone_game`'s delegated `create_game()` through a
    real DB-lookup-miss "Template not found" `ValueError`, not the unrelated Pydantic
    input-validation error a merely-`NULL` `template_id` would raise instead
  - `test_clone_game_endpoint_submitted_roster_drops_one_adds_one_with_deadline_carryover` — a
    richer roster scenario than Phase 5's existing single-participant-resubmission tests: source
    game has two confirmed participants; the clone's submitted `participants` list drops one and
    adds a brand-new (no source-side match) participant. Asserts the new game's roster is built from
    exactly the submitted list in submitted order, and that `_apply_deadline_carryover` creates a
    schedule only for the resubmitted participant with a source-side carryover-eligible match --
    neither the dropped participant (never makes it onto the new game) nor the brand-new one (no
    source match) gets one
  - `test_clone_game_endpoint_future_post_at_defers_publish` — a future `post_at` (before
    `scheduled_at`) results in no immediate `bot_action_queue` `game_created` row, exercising
    `create_game`'s existing deferred-publish branch end-to-end through `clone_game`'s delegation;
    confirms the new game still gets a concrete `post_at` and `status=SCHEDULED`

### Modified

- `tests/integration/test_clone_game_endpoint.py` — added `base64` import and a
  `_make_discord_token`/`HOST_ONLY_DISCORD_TOKEN`/`HOST_ONLY_DISCORD_ID` fixture-identity helper for
  a third (non-bot-manager) authenticated identity needed by two of the new tests; extended
  `_setup_environment` with an optional `allowed_signup_methods` parameter (passed through to
  `create_template`, defaulting to `None` so every existing call site is unaffected) so the
  field-overrides test can override `signup_method` to a value the default template wouldn't allow.

### Verification

- `uv run ruff check tests/integration/test_clone_game_endpoint.py` — All checks passed
- `uv run pytest tests/unit` — 2594 passed (unchanged from Phase 6 -- this phase touches only
  integration tests)
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files
- `scripts/run-integration-tests.sh tests/integration/test_clone_game_endpoint.py` — 14 passed (7
  previously-passing tests plus the 7 new ones)
- `scripts/run-integration-tests.sh` (full suite) — 357 passed, 0 skipped, 2739 deselected -- no
  regressions elsewhere

## Phase 8: Rebuild `CloneGame.tsx` — Two-Stage `GameForm`-Based Screen

Replaced `CloneGame.tsx`'s bespoke small form (a single-stage `DateTimePicker` +
carryover-`Select` form posting a small hand-rolled JSON payload) with a two-stage,
`GameForm`-based screen. Stage 1 (unchanged from the old component visually: game
summary, `player_carryover`/`waitlist_carryover` `Select`s reusing the existing
`CARRYOVER_OPTIONS`, conditional `YES_WITH_DEADLINE` deadline `DateTimePicker`s, and a
"Continue" button) gates entry to Stage 2, which mounts `<GameForm mode="create" ... />`
with a frozen `initialData` object built once, at the moment "Continue" is clicked, by
the new `buildStage2InitialData` helper: a shallow copy of `sourceGame` with `post_at`
cleared (so `GameForm`'s own "leave empty = post now" default applies) and
`scheduled_at` re-derived as `sourceGame.scheduled_at + 14 days` (preserving the old
component's `DEFAULT_DAYS_AHEAD` behavior), plus either `confirmed_participants`/
`waitlist_participants` (for a `HOST_SELECTED_WITH_WAITLIST` source game) or
`participants` (every other signup method) included or stripped to `[]` depending on
whether the frozen `playerCarryover`/`waitlistCarryover` selections were `NO` vs.
`YES`/`YES_WITH_DEADLINE` at the moment Continue was clicked -- `GameForm`'s own
`buildParticipantList` (unmodified) does the rest. The carryover `Select`s/pickers stay
rendered and editable above `<GameForm>` after Stage 2 mounts, still bound to their own
local state, so changing them post-Continue affects only what Phase 9's submit payload
will send for deadline-carryover purposes, never the already-mounted `GameForm`'s
participant editor -- verified by a direct regression test (Design Note 5's hazard).

No `/guilds/{id}/channels` or `/guilds/{id}/roles` fetch was added: the `channels` prop
is a single-item array synthesized directly from `sourceGame.channel_id`/
`sourceGame.channel_name` (mirroring `CreateGame.tsx`'s single-channel synthesis
pattern), and `GameForm` has no `roles` prop at all. `canChangeChannel={false}` is
passed since clone has no channel-override field anywhere in the backend contract.
`isBotManager` is resolved via `canUserManageBotSettings(sourceGame.guild_id)`
(`frontend/src/utils/permissions.ts`, the same helper `CreateGame.tsx` uses) in a
`useEffect` keyed on `sourceGame`, once the source game has loaded.

`GameForm`'s `onSubmit` prop is wired to a stub (`throw new Error('Clone submission not
yet implemented')`) since wiring the real multipart `POST /{gameId}/clone` submission is
Phase 9's scope, not this phase's; Phase 8 covers Stage 1/Stage 2 rendering and
pre-population only.

**TDD process note (divergence from the details file's literal `test.failing` marker
instruction):** this project's installed `vitest` is v4, which removed the `.failing()`
test marker (already discovered and documented by a prior phase's
`GameForm.errors-location.test.tsx`, written before this phase). Followed that same
established convention instead: the five Task 8.1 tests were written first against a
minimal RED-phase stub (`CloneGame.tsx` implementing only real fetch/loading/error
handling plus a bare Stage 1 shell with no carryover selects/pickers and a `Continue`
button that mounted nothing), run and confirmed failing for real reasons (missing
selects/pickers, no Stage 2 mount), then the full Stage 1/Stage 2 implementation
(Task 8.2) was written without changing any test assertion, and the tests were
re-run and confirmed passing.

### Added

- `frontend/src/pages/__tests__/CloneGame.test.tsx` — full rewrite; all 16 tests against
  the old bespoke single-stage UI deleted. 15 new tests (Tasks 8.1-8.3):
  - `renders Stage 1 carryover selects, deadline pickers, and a Continue button` —
    RED-first against the minimal stub, confirmed failing, then passing after Task 8.2
  - `clicking Continue reveals GameForm fields pre-populated from the source game` — same
    RED→GREEN cycle
  - `does not pre-populate the participant editor when playerCarryover is NO (default)` —
    same RED→GREEN cycle
  - `pre-populates the participant editor when playerCarryover is YES before Continue` —
    same RED→GREEN cycle
  - `toggling playerCarryover after Stage 2 has mounted does not clear host-edited title
text` — same RED→GREEN cycle; the direct regression test for Design Note 5's hazard
  - `strips confirmed_participants/waitlist_participants -- not participants -- for a
HOST_SELECTED_WITH_WAITLIST source game` (Task 8.3 edge case; retrofit test for
    already-correct code, no RED phase per that instruction file's rule)
  - `does not crash and leaves file inputs empty when the source game has a
thumbnail/banner` (Task 8.3 edge case; same retrofit rule)
  - `shows a loading spinner while fetching the source game` (Task 8.3; preserves the old
    component's behavior)
  - `shows an error and a Back button when the fetch fails` (Task 8.3; preserves the old
    component's behavior)
  - `blocks Continue with an error when the player deadline is missing` (Task 8.3;
    retrofit test for the old component's carried-over `YES_WITH_DEADLINE` validation)
  - `blocks Continue with an error when the player deadline is in the past` (Task 8.3;
    same retrofit rule)
  - `blocks Continue with an error when the waitlist deadline is missing` (Task 8.3; same
    retrofit rule)
  - `blocks Continue with an error when the waitlist deadline is in the past` (Task 8.3;
    same retrofit rule)
  - `clicking Cancel in Stage 2 navigates back to the source game` (Task 8.3; retrofit
    test for `GameForm`'s `onCancel` wiring)
  - `surfaces an error when Stage 2 is submitted (clone submission not yet wired)` (Task
    8.3; retrofit test confirming the Phase 9 stub's error path renders correctly)

  The six tests above were added while closing out Task 8.3's diff-coverage gate (added
  to `.github/instructions/task-implementation.instructions.md`'s pre-commit-gate list,
  not called out individually by the details file): the initial 9-test suite left
  `handleContinue`'s four deadline-validation branches, the `handleSubmit` stub's
  `throw`, and `GameForm`'s `onCancel` prop uncovered on `git diff` against
  `origin/develop`, which `diff-cover`'s 90%-threshold pre-commit hook
  (`scripts/check_diff_coverage_frontend.py`) caught at 80.6%. All six are retrofit tests
  for already-correct code (no RED phase), consistent with Task 8.3's "add edge-case
  tests" scope.

### Modified

- `frontend/src/pages/CloneGame.tsx` — full rewrite (Tasks 8.1-8.3): two-stage component
  replacing the old single-stage bespoke form; added the `buildStage2InitialData` helper
  function (pure, exported implicitly via the module, documented with its "compute
  exactly once" invariant); `isBotManager` state resolved asynchronously via
  `canUserManageBotSettings`; `handleContinue` retains the old component's
  `YES_WITH_DEADLINE` deadline-required/deadline-must-be-future validation before
  freezing Stage 2's `initialData`.

### Verification

- `npx vitest run src/pages/__tests__/CloneGame.test.tsx` — all 5 Task 8.1/8.2 tests
  confirmed failing against the RED-phase stub, then all 15 tests (Task 8.1/8.2's 5, plus
  Task 8.3's 10 edge-case/retrofit tests) `PASSED` after the full implementation
- `cd frontend && npm run test` — 47 files, 509 tests passed (no regressions elsewhere)
- `cd frontend && npm run build` — `tsc` + `vite build` succeeded, no TypeScript errors
- `npx eslint src/pages/CloneGame.tsx src/pages/__tests__/CloneGame.test.tsx` — no issues
- `npx prettier --check src/pages/CloneGame.tsx src/pages/__tests__/CloneGame.test.tsx` —
  all matched files use Prettier code style
- `scripts/run-frontend-coverage.sh` + `diff_cover.diff_cover_tool` against
  `origin/develop` — `frontend/src/pages/CloneGame.tsx` 100% diff coverage (31/31 lines)
- `uv run pytest tests/unit` — 2594 passed (unchanged from Phase 7 -- this phase touches
  only frontend files)
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

## Phase 9: Wire `CloneGame.tsx`'s Submit Handler to the Extended Clone Endpoint

Replaced Phase 8's `handleSubmit` stub (`throw new Error('Clone submission not yet
implemented')`) with a real handler that maps the full `GameFormData` (plus Stage 1's live
`playerCarryover`/`waitlistCarryover`/`playerDeadline`/`waitlistDeadline` state at submit
time) onto a `multipart/form-data` `FormData` payload matching the Phase 6 `POST
/api/v1/games/{gameId}/clone` route's `Form()`/`File()` contract field-for-field, mirroring
`CreateGame.tsx`'s `handleSubmit` almost verbatim: `scheduled_at` always sent; `title`/
`description`/`where`/`signup_instructions`/`max_players`/`expected_duration_minutes`/
`signup_method`/`recur_rule`/`post_at` sent only when non-empty/non-null (omit-if-unset, so
the backend inherits the source game's value); `reminder_minutes` and `participants` always
sent as JSON-stringified arrays (`participants` mapped via `p.resolvedMention ?? p.mention
.trim()`, filtered to non-empty, exactly as `CreateGame.tsx` does -- not `EditGame.tsx`'s
`participant_id`-based payload, since the cloned game has no pre-existing `GameParticipant`
rows to reference); `host` sent only when `isBotManager` and non-empty; `thumbnail`/`image`
raw `File` objects sent only when a new file was attached; `remind_host_rewards`/
`reminders_as_dms` always sent as `'true'`/`'false'`; `player_carryover`/`waitlist_carryover`
always sent, `player_deadline`/`waitlist_deadline` sent only when set. On success, navigates
to `/games/{response.data.id}` (unchanged target). On an `invalid_mentions` 422 response,
partitions `invalid_mentions` into participant vs. channel errors (deduplicated by input,
mirroring `CreateGame.tsx` lines 253-288 almost verbatim) and populates new local
`validationErrors`/`channelValidationErrors`/`validParticipants` state, now passed into
`<GameForm>`, without rethrowing (leaves the form open for corrections). Any other error
(network failure, a plain-message 4xx/5xx) is rethrown unchanged so `GameForm`'s own
existing submit handler surfaces its generic fallback error banner -- no duplicate
CloneGame-level error banner was added, since `GameForm` already renders one.

**Notable finding, out of scope for this phase:** while writing Task 9.1's tests, a
pre-existing infinite-render-loop bug was discovered in `DurationSelector.tsx` (used by
`GameForm`, and therefore by `CreateGame.tsx`/`EditGame.tsx`/`CloneGame.tsx` alike): when a
game's `expected_duration_minutes` is a non-preset custom value (anything other than `120`,
`240`, or `null`) at mount time, `DurationSelector` starts in "custom" mode, and its
`useEffect`/`useCallback` pair depends on the unmemoized `onChange` prop (`GameForm`'s
`handleDurationChange`, a fresh function identity every render) -- calling it triggers a
parent re-render, which creates a new `onChange` identity, which re-fires the effect,
forming a synchronous infinite loop that pegs the CPU and hangs the whole page (reproduced
and bisected down to this single field via a throwaway repro test; not a vitest/jsdom
quirk). No test anywhere in the existing suite had ever set a non-preset
`expected_duration_minutes` on a game mounted into `GameForm`, so this had never
surfaced before. Not fixed here (out of Phase 9's scope -- `DurationSelector.tsx` is
unrelated to the clone-game redesign); this phase's own test data uses `120` (a preset) to
avoid triggering it. Flagged for a future, separately-scoped fix.

### Added

- `frontend/src/pages/__tests__/CloneGame.test.tsx` — new `describe('submit handler (Task
9.1/9.2/9.3)')` block, written first against Task 8's stub (this project's vitest 4 has no
  `.failing()` marker; followed the same established RED-stub convention as Task 8.1: run
  and confirmed failing for a real reason -- `apiClient.post` never called, all payload
  assertions failing -- then Task 9.2 implemented the real handler with no assertion
  changes, tests re-run and confirmed passing):
  - `posts a multipart clone request mapping every GameFormData field plus Stage 1
carryover/deadline state, and navigates to the new game on success` — sets both
    carryover selects (`YES_WITH_DEADLINE` with a deadline, and `YES`), edits the title and
    host fields, attaches a new thumbnail file, and asserts every `FormData` field
    (including the `thumbnail` file part, satisfying Task 9.3's explicit file-upload
    assertion) matches
  - `omits optional text fields and the host override, and sends an empty participants
list, when nothing was carried over or edited` — default Stage 1 state (`NO`/`NO`),
    confirms the omit-if-unset fields are absent and `participants`/carryover fields reflect
    the empty/default state
  - `populates GameForm validation state and does not navigate when the clone request
returns an invalid_mentions 422 response` — asserts both the participant-mention
    (`ValidationErrors`) and channel-mention (`ChannelValidationErrors`) error UI render and
    that `mockNavigate` is never called
  - `richGame`/`richGetImpl` fixtures (a source game with `where`/`signup_instructions`/
    `expected_duration_minutes`/`recur_rule`/`remind_host_rewards`/`reminders_as_dms`/
    `reminder_minutes` all set to non-default values) shared by the first two new tests, to
    exercise the omit-if-unset fields' truthy branches without needing fragile UI
    interaction with `DurationSelector`/`RecurrenceSelector`/`ReminderSelector`
- Renamed the pre-existing Task 8.3 test `surfaces an error when Stage 2 is submitted
(clone submission not yet wired)` to `shows GameForm generic error banner when the clone
request fails for an unhandled reason` (Task 9.3 refactor -- the old name described the
  Phase 8 stub, which Phase 9 replaced) and gave it an explicit
  `apiClient.post.mockRejectedValueOnce(new Error('Network error'))` instead of relying on
  the implicit auto-mock-returns-`undefined` `TypeError` it exercised before; the assertion
  (`'Failed to submit. Please try again.'` renders, via `GameForm`'s own fallback banner) is
  unchanged and still passes against the real handler, since a non-`invalid_mentions` error
  is still rethrown.

### Modified

- `frontend/src/pages/CloneGame.tsx` — added `StatusCodes` import and the
  `ValidationError`/`ChannelValidationError`/`ValidationErrorResponse` local interfaces
  (duplicated per-page, matching `CreateGame.tsx`/`EditGame.tsx`'s existing convention
  rather than a shared module); added `validationErrors`/`validParticipants`/
  `channelValidationErrors` state, now passed into `<GameForm>`; replaced the Phase 8
  `handleSubmit` stub with the real implementation described above (Task 9.2).

### Verification

- `npx vitest run src/pages/__tests__/CloneGame.test.tsx` — the 3 new Task 9.1 tests
  confirmed failing against Task 8's stub (genuine RED: `apiClient.post` never called),
  all 18 tests in the file `PASSED` after Task 9.2's implementation
- `cd frontend && npm run test` — 47 files, 512 tests passed (509 Phase-8 baseline + 3 net
  new; no regressions elsewhere)
- `cd frontend && npm run build` — `tsc` + `vite build` succeeded, no TypeScript errors
- `npx eslint src/pages/CloneGame.tsx src/pages/__tests__/CloneGame.test.tsx` — no issues
- `npx prettier --check src/pages/CloneGame.tsx src/pages/__tests__/CloneGame.test.tsx` —
  all matched files use Prettier code style
- `scripts/run-frontend-coverage.sh` + `python3 scripts/check_diff_coverage_frontend.py`
  (staged diff against `origin/develop`) — exits 0 (no output); `CloneGame.tsx` file-level
  line coverage 100% (statement coverage 96.66%, the few uncovered statements are pre-Phase-9
  Stage 1 lines outside this phase's diff)
- `uv run pytest tests/unit` — 2594 passed (unchanged from Phase 8 -- this phase touches
  only frontend files)
- `uv run mypy shared/ services/` — Success: no issues found in 155 source files

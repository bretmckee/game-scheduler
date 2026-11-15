<!-- markdownlint-disable-file -->

# Task Details: Multiple Reward Entries Input

## Research Reference

**Source Research**: .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md

Phase layout: P1 backend storage + API + migration (formatter takes a list, simple inline rendering); P2 embed fit-vs-link logic (TDD); P3 frontend (types, form, submit, display). Each phase is independently committable. Between P1 and P3 the web form still sends a plain string, which the API rejects at runtime; nothing is deployed between commits and all gates (pytest, mypy, npm build/test) stay green.

## Phase 1: Storage, Migration and API

### Task 1.1: Constants and migration SQL module (TDD RED: integration tests)

Add `MAX_REWARD_ENTRIES = 20`, `MAX_REWARD_LENGTH = 2000` to `shared/utils/limits.py`. Create `shared/utils/rewards_migration.py` (with copyright header) holding the upgrade USING expression constant and the downgrade `string_agg` constant. Write integration tests first.

- **Files**:
  - shared/utils/limits.py - add the two constants
  - shared/utils/rewards_migration.py - SQL constants (new)
  - tests/integration/test_rewards_migration.py - follows tests/integration/test_template_signup_method_backfill_migration.py
- **Success**:
  - Upgrade expr run via `SELECT <expr> FROM (VALUES ('a'),(''),('  '),(NULL),(E'line1\nline2')) t(rewards)` yields `["a"]`, NULL, NULL, NULL, `["line1\nline2"]`
  - Downgrade aggregate joins a multi-entry list with `\n\n`
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 82-97) - migration SQL and downgrade
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 138-143) - integration test spec
- **Dependencies**: none

### Task 1.2: Alembic revision, model, schema, route, service, formatter signature (GREEN)

All in one task because the type change must update every caller.

- New Alembic revision (`down_revision` = current head; find with `uv run alembic heads`): upgrade `ALTER TABLE game_sessions ALTER COLUMN rewards TYPE json USING <const>`; downgrade via temp text column, UPDATE with string_agg, drop, rename.
- `shared/models/game.py`: `rewards: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)`.
- `shared/schemas/game.py`: update `rewards: list[str] | None` (`max_length=MAX_REWARD_ENTRIES`, items `StringConstraints(max_length=MAX_REWARD_LENGTH)`), validator strips and drops blanks; response `rewards: list[str] | None`.
- `services/api/routes/games.py`: keep `Form()` string, `json.loads` like `reminder_minutes`; response builder passes list through (~:795, :854, :1402).
- `services/api/services/games.py:1309`: store `update_data.rewards or None`.
- `services/bot/formatters/game_message.py`: `rewards: list[str] | None`; render one field per entry (`||entry||`; first named `EMBED_FIELD_REWARDS`, others `_ZERO_WIDTH_SPACE`), no fit logic yet. Update `handlers.py` caller (:1517) types if needed; truthiness uses (:1345, :1400) unchanged.
- Update existing tests to list format: tests/unit/services/api/services/test_games_service.py, tests/unit/services/api/services/test_update_game_fields_helpers.py (:452, `GameUpdateRequest(rewards="a bag of gold")` fails list validation), tests/unit/services/api/routes/test_games_helpers.py, tests/unit/bot/test_game_message_formatter.py, tests/integration/test_rewards_fields.py (:88, :298, :371), tests/e2e/test_game_rewards.py (:108, :223, :292 post `json.dumps([...])`).
- Add unit tests: schema blank stripping and caps, service `[]` -> NULL, per-entry field naming.
- Extend integration test :88: PUT `json.dumps(["a","multi\nline"])` round-trips in DB and GET; `[]`/all-blank -> NULL; >20 entries or >2000-char entry -> 422.
- **Files**: files listed above plus a new file under alembic/versions/ named *_rewards_to_json_list.py (new, with copyright header; generate id via `uv run alembic revision`)
- **Success**:
  - `uv run pytest tests/unit`, `uv run mypy shared/ services/` pass; integration tests for rewards pass via `scripts/run-integration-tests.sh |& tee output-integration.txt`
  - Existing single-string rows migrate to one-entry lists
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 9-42) - touchpoints
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 76-103) - storage, migration, API
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 126-129) - unchanged callers
- **Dependencies**: Task 1.1

## Phase 2: Discord Embed Fit-vs-Link (TDD)

### Task 2.1: RED - stubs and failing tests

Add to `game_message.py` a stub helper (e.g. `_rewards_fit_inline(...) -> bool` raising `NotImplementedError`) in this phase, and xfail unit tests in tests/unit/bot/test_game_message_formatter.py for: all fit -> per-entry fields; entry > `DISCORD_EMBED_FIELD_VALUE_LIMIT - 4` -> single link field; total field count > 25 -> link; total embed length > `DISCORD_EMBED_TOTAL_SAFE_LIMIT` (description counted as trimmable) -> link; long description trimmed rather than forcing link; no partial display; link text `[View rewards](game_url)`.

- **Files**: services/bot/formatters/game_message.py, tests/unit/bot/test_game_message_formatter.py
- **Success**: new tests collected and xfail (follow .github/instructions/test-driven-development.instructions.md)
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 112-119) - embed rules
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 51-57) - Discord limits
- **Dependencies**: Phase 1 completion

### Task 2.2: GREEN and REFACTOR - implement decision, make game_url non-optional on rewards path

Implement the all-or-nothing check before `_trim_embed_if_needed`; require `game_id` (hence `game_url`) when `rewards` is set so mypy guarantees the URL; update every formatter caller (handlers.py :1333, :1383, :1495) and tests. Remove xfail markers.

- **Files**: services/bot/formatters/game_message.py, services/bot/events/handlers.py, affected unit tests
- **Success**: unit tests pass, mypy clean, no xfail left
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 21-26) - formatter details
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 112-119) - rules
- **Dependencies**: Task 2.1

### Task 2.3: E2E tests

Extend tests/e2e/test_game_rewards.py: multiple rewards -> one spoiler field each (first `🏆 Rewards`, rest zero-width); at-limit 1020-char entry edits successfully and renders inline; overflow (too many or too long) -> single link field and edit succeeds; archive repost (:108) keeps per-entry fields. Run `scripts/run-e2e-tests.sh |& tee output-e2e.txt` (scope args as needed).

- **Files**: tests/e2e/test_game_rewards.py
- **Success**: e2e tests pass against real Discord
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 145-151) - e2e spec
- **Dependencies**: Task 2.2

## Phase 3: Frontend

### Task 3.1: Constants, types, GameDetails (tests first)

Create exported frontend constants module (e.g. `frontend/src/constants/rewards.ts`: max entries 20, max length 2000, mirroring Python). `frontend/src/types/index.ts:123` -> `rewards?: string[] | null`. GameDetails (:365-388): each entry its own block inside the blur-to-reveal box with `whiteSpace: 'pre-line'`. Update GameDetails.test.tsx first (per-entry render). GameCard unchanged. Because the type change breaks consumers, Task 3.2 must land in the same phase (it does).

- **Files**: frontend/src/constants/rewards.ts (new), frontend/src/types/index.ts, frontend/src/pages/GameDetails.tsx, `frontend/src/pages/__tests__/GameDetails.test.tsx`
- **Success**: `npm run build` and `npm run test` pass after Task 3.2
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 120-125) - web display
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 108-110) - constants
- **Dependencies**: Phase 1 completion

### Task 3.2: GameForm list UI, EditGame submit, Save-and-Archive gate

`formData.rewards: string[]` initialized `initialData.rewards ?? ['']` (GameForm :112, :313, :348); one multiline TextField per entry (:709-726) with `maxLength` from constants; "+ Add another reward" appends `''` (disabled at max entries); per-row remove button hidden when one row remains; Save-and-Archive gate (:1095) = any non-blank entry. EditGame (:229 pattern, :268, :406): trim, drop blanks, `payload.append('rewards', JSON.stringify(list))`. Write vitest tests first: add/remove, blank drop, JSON submit, `[]` clears, gate. Update GameForm.rewards.test.tsx and EditGame*.test.tsx.

- **Files**: frontend/src/components/GameForm.tsx, frontend/src/pages/EditGame.tsx, `frontend/src/components/__tests__/GameForm.rewards.test.tsx`, `frontend/src/pages/__tests__/EditGame*.test.tsx`
- **Success**: `cd frontend && npm run build && npm run test` pass; edit -> save -> reload round-trips multiple entries with newlines
- **Research References**:
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 31-37) - frontend touchpoints
  - .copilot-tracking/research/20261115-01-multiple-rewards-input-research.md (Lines 104-111) - form spec
- **Dependencies**: Task 3.1

## Dependencies

- No new libraries; one Alembic migration; real Postgres and Discord for integration/e2e runs

## Success Criteria

- Existing string rewards migrate to one-entry lists and display unchanged
- Multiple entries with newlines round-trip; blanks dropped; clearing stores NULL
- Discord shows per-entry spoiler fields when they fit, otherwise one link field; at-limit e2e passes
- API rejects >20 entries or >2000-char entries

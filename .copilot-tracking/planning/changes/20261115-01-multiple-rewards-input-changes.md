<!-- markdownlint-disable-file -->

# Changes: Multiple Reward Entries Input

## Phase 1: Storage, Migration and API

### Task 1.1: Constants, migration SQL module, migration integration tests

#### Added

- shared/utils/rewards_migration.py - `REWARDS_TEXT_TO_JSON_EXPR` (ALTER ... USING expression) and `REWARDS_JSON_TO_TEXT_EXPR` (downgrade `string_agg` subquery), shared by the migration and its test.
- tests/integration/test_rewards_migration.py - runs both expressions against literal values in real Postgres (NULL, blank, whitespace-only, single and multi-line, empty list).

#### Modified

- shared/utils/limits.py - added `MAX_REWARD_ENTRIES = 20` and `MAX_REWARD_LENGTH = 2000`.

**Off-plan change**: the upgrade expression trims `' \t\r\n'` (not just spaces) when deciding a value is blank, so newline-only text also becomes NULL. A test row covers this.

### Task 1.2: Alembic revision, model, schema, route, service, formatter, tests

#### Added

- alembic/versions/310018d6a131_rewards_to_json_list.py - upgrade converts `game_sessions.rewards` to `json` via the shared USING expression; downgrade goes through a temporary text column.

#### Modified

- shared/models/game.py - `rewards: Mapped[list[str] | None]` stored as `JSON(none_as_null=True)`.
- shared/schemas/game.py - `GameUpdateRequest.rewards` is a list capped at `MAX_REWARD_ENTRIES` entries of up to `MAX_REWARD_LENGTH` chars each; new `strip_blank_rewards` validator trims entries and drops blank ones. `GameResponse.rewards` is `list[str] | None`.
- services/api/routes/games.py - PUT `json.loads` the `rewards` form string.
- services/api/services/games.py - an empty rewards list is stored as NULL.
- services/bot/formatters/game_message.py - `rewards: list[str] | None`; new `_add_rewards_fields` adds one `||entry||` field per reward (the first is named `EMBED_FIELD_REWARDS`, the rest `_ZERO_WIDTH_SPACE`). Fit/link logic is not added yet (Phase 2).
- tests/unit/shared/schemas/test_game_schema.py - tests for trimming, blank dropping, the entry cap, the length cap, and the response list type.
- tests/unit/services/api/services/test_update_game_fields_helpers.py - list update, `[]` -> None, omitted rewards left unchanged.
- tests/unit/bot/test_game_message_formatter.py - list inputs and a per-entry field naming test.
- tests/unit/bot/events/test_handlers_misc.py - `game.rewards` mocks are now lists.
- tests/integration/test_rewards_fields.py - multi-entry round-trip (response, GET, DB); `[]` and all-blank lists stored as SQL NULL; over-count and over-length -> 422; raw SQL and the archive-delay test send JSON lists.
- tests/e2e/test_game_rewards.py - PUTs send `json.dumps([...])`.

**Off-plan changes**:

- `JSON(none_as_null=True)` on the model column: the integration test showed that plain `JSON` stores Python `None` as a JSON `'null'` value, not SQL NULL. That broke the "no rewards is always NULL" rule, both on clearing and on the recurrence clone (`rewards=None`).
- tests/e2e/test_game_rewards.py - added the `test_user_discord_user_id` fixture to the save-and-archive and reminder-DM tests. Both left an untracked `users` row for DISCORD_USER_ID, which made the conftest hermeticity check fail at teardown. This happened before this change; it is the same bug class fixed in 8cda1b62.
- tests/unit/bot/events/test_handlers_misc.py was not listed in the plan; I updated its mocks to the list type so they match the new data shape.

**Verification**: `uv run pytest tests/unit`: 2697 passed. `uv run mypy shared/ services/`: clean. `scripts/run-integration-tests.sh`: 381 passed. `scripts/run-e2e-tests.sh tests/e2e/test_game_rewards.py`: 3 passed.

## Phase 2: Discord Embed Fit-vs-Link

### Task 2.1: RED - stub and xfail unit tests

#### Modified

- services/bot/formatters/game_message.py - added the `GameMessageFormatter._rewards_fit_inline(embed, rewards) -> bool` stub, which raises `NotImplementedError`. Nothing calls it yet, so the existing inline behavior still works.
- tests/unit/bot/test_game_message_formatter.py - 10 strict-xfail tests. Helper: all fit; entry at `DISCORD_EMBED_FIELD_VALUE_LIMIT - 4` fits; one char over does not; field count of exactly 25 fits and 26 does not; a 4000-char description is treated as trimmable; rewards alone over the total limit do not fit. Embed: an oversize entry, too many fields, or total-length overflow each produce a single `[View rewards](game_url)` field with no partial display.

**Off-plan note**: `test_create_game_embed_long_description_trimmed_instead_of_linking_rewards` has no xfail marker. The current code already shows rewards inline and trims the description, so the test passes now. It stays as a guard for the new decision logic.

### Task 2.2: GREEN/REFACTOR - fit decision, required game_id

#### Modified

- shared/utils/limits.py - added `DISCORD_EMBED_MAX_FIELDS = 25`.
- services/bot/formatters/game_message.py:
  - `create_game_embed` now requires `game_id: str`, and `_prepare_description_and_urls` returns `calendar_url` and `game_url` as `str`, so the rewards link URL is always set.
  - `_rewards_fit_inline` is implemented. It returns False if any `||entry||` is over 1024 chars, if the field count would go over 25, or if the total length would go over `DISCORD_EMBED_TOTAL_SAFE_LIMIT` once the description is counted as trimmable down to `...`.
  - The new `_reward_field_contents` builds the (name, value) pairs for both the fit check and the rendering.
  - `_add_rewards_fields(embed, rewards, game_url)` adds either all spoiler fields or a single `[View rewards](game_url)` field.
  - The footer is now added before rewards so the fit check counts it.
  - The `"..."` marker is now the `_TRIM_MARKER` constant.
- tests/unit/bot/test_game_message_formatter.py - xfail markers removed; `_BASE_KWARGS` now includes `game_id`.
- tests/unit/services/bot/formatters/test_game_message.py - added `game_id="game-123"` to the 29 `create_game_embed` calls that omitted it. Removed `test_prepare_description_and_urls_without_game_id` and `test_embed_excludes_links_field_without_calendar_url`, because a missing `game_id` is no longer possible. The short-description test now passes a `game_id`.

**Off-plan note**: services/bot/events/handlers.py needed no change. Its only formatter call is `format_game_announcement`, which already required `game_id: str`.

**Verification**: `uv run pytest tests/unit`: 2706 passed, 0 xfail. `uv run mypy shared/ services/`: clean.

### Task 2.3: E2E tests

#### Modified

- tests/e2e/test_game_rewards.py:
  - New helpers: `_post_in_progress_game`, `_set_rewards_and_wait_for_embed`, `_reward_fields`, `_expected_inline_fields` and `_is_rewards_link_field`.
  - `test_discord_embed_shows_rewards_spoiler` is renamed to `test_discord_embed_shows_one_spoiler_field_per_reward`. It uses three entries, one of them multi-line, and checks the exact field names and values.
  - New `test_discord_embed_accepts_reward_at_field_value_limit`: a 1020-char entry, which makes a 1024-char spoiler value, renders inline.
  - New parametrized `test_discord_embed_overflowing_rewards_show_single_link_field`. The `entry-too-long` case uses a 1021-char entry. The `too-many-fields` case uses 20 entries on top of 7 base fields. Both produce a single `[View rewards](.../games/{id})` field with no spoilers.
  - The save-and-archive test now sends two entries and checks that the archive repost keeps one spoiler field per entry.

**Verification**: `scripts/run-e2e-tests.sh tests/e2e/test_game_rewards.py`: 6 passed against real Discord. Output is in output-e2e.txt.

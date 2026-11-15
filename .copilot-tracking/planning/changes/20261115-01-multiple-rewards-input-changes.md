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

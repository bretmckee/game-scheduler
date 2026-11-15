<!-- markdownlint-disable-file -->

# Task Research Notes: Multiple Reward Entries (one text box per reward, "+ Add another reward")

## Research Executed

### File Analysis

- alembic/versions/20260321_add_rewards_fields.py
  - Added `game_sessions.rewards` (`sa.Text`, nullable) and `remind_host_rewards` on sessions + templates. Templates have no `rewards` column.
- shared/models/game.py:70, :81-82
  - `rewards: Mapped[str | None] = mapped_column(Text, nullable=True)`; list precedent in same model: `reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, ...)`, `notify_role_ids: Mapped[list[str] | None]`.
- shared/schemas/game.py:137, :166, :253
  - Update: `rewards: str | None = Field(None, max_length=2000)`; response: `rewards: str | None`. Other text limits are inline literals (e.g. `where` `max_length=500` at :137).
- services/api/routes/games.py:235-241, :795, :854, :1402
  - PUT takes `rewards: Annotated[str | None, Form()]` (multipart). List fields already arrive as JSON strings and are parsed with `json.loads` (`reminder_minutes`, `notify_role_ids`). Response builder passes `game.rewards` through. Create/clone routes do not accept rewards.
- services/api/services/games.py:1309-1310
  - `if update_data.rewards is not None: game.rewards = update_data.rewards` — clearing currently stores `""`, not NULL.
- shared/services/game_schedules.py:238
  - Recurrence clones set `rewards=None`.
- services/bot/formatters/game_message.py:153, :217-330, :229, :615-616, :623-628
  - `game_url = f"{config.frontend_url}/games/{game_id}"` (:150-153). `game_id` is typed Optional, but every production caller passes it (handlers.py:1333, :1383, :1495), so a game with rewards always has a URL.
  - Fields before rewards: Game Time, Host, Run Time + spacer, Add to Calendar + spacer, Where, Voice Channel, participant/waitlist columns (~8-12 of 25).
  - Spacer fields use `_ZERO_WIDTH_SPACE` names (:229).
  - Rewards today: `embed.add_field(name=EMBED_FIELD_REWARDS, value=f"||{rewards}||", inline=False)`.
  - `_trim_embed_if_needed` trims only `embed.description` when `len(embed) > DISCORD_EMBED_TOTAL_SAFE_LIMIT`.
- shared/utils/limits.py
  - Holds `EMBED_FIELD_REWARDS`, `DISCORD_EMBED_FIELD_VALUE_LIMIT` (1024), `DISCORD_EMBED_TOTAL_SAFE_LIMIT`.
- services/bot/events/handlers.py:1345-1346, :1400, :1517
  - Truthiness only: reminder DM when `not game.rewards`; archive post @mentions players if `game.rewards`; passes `rewards=game.rewards` to the formatter.
- frontend/src/components/GameForm.tsx:112, :313, :348, :709-726, :1095
  - `formData.rewards: string`; single `TextField multiline rows={3}`, shown only in edit mode when status ≠ SCHEDULED; Save-and-Archive gated on `formData.rewards.trim() !== ''`.
  - Frontend limits are local literals (`MAX_LOCATION_LENGTH = 500` duplicated at :417 and :444).
- frontend/src/pages/EditGame.tsx:229, :268, :406
  - `payload.append('rewards', formData.rewards || '')` in both save and save-and-archive paths; list precedent `payload.append('reminder_minutes', JSON.stringify(arr))` at :229.
- frontend/src/pages/GameDetails.tsx:365-388
  - Single blurred click-to-reveal box rendering `game.rewards` in one `Typography` (newlines not preserved).
- frontend/src/components/GameCard.tsx:251-253 — "🏆 Rewards available" if truthy.
- frontend/src/types/index.ts:123 — `rewards?: string | null`.
- frontend/src/App.tsx:66 + services/api/routes/games.py:655
  - `/games/:gameId` is behind login; API verifies guild membership + player roles. Relevant to the link fallback (players may need to sign in).

### Code Search Results

- `reward` (py/ts): non-test touchpoints are exactly those above.
- Tests touching rewards: tests/unit/bot/test_game_message_formatter.py, tests/unit/services/api/services/test_games_service.py, tests/unit/services/api/routes/test_games_helpers.py, tests/integration/test_rewards_fields.py, tests/e2e/test_game_rewards.py, `frontend/src/components/__tests__/GameForm.rewards.test.tsx`, `frontend/src/pages/__tests__/EditGame*.test.tsx`, GameDetails.test.tsx.
  - tests/integration/test_rewards_fields.py:88 `test_rewards_field_persists_through_game_update`, :298/:371 save-and-archive tests.
  - tests/e2e/test_game_rewards.py:108 save-and-archive repost, :223 reminder DM, :292 embed spoiler (posts `data={"rewards": "magic sword"}`, asserts `||magic sword||`).
- Migration-test precedent: tests/integration/test_template_signup_method_backfill_migration.py — a migration has already run against an empty DB, so the test imports the migration's SQL constants from `shared/utils/...` and runs them against hand-inserted pre-migration rows.

### External Research

- Source: https://docs.discord.com/developers/resources/message (Embed Limits; discord.com/developers/docs/... 301-redirects here)
  - `field.value` ≤ 1024, `field.name` ≤ 256, ≤ 25 fields per embed; title+description+field names/values+footer+author ≤ 6000 **across all embeds in a message**; violations → 400 Bad Request.
  - Existing latent bug: schema allows 2000-char rewards but the field caps at 1024 (incl. `||` × 2). Fixed by this design.
- Source: https://www.postgresql.org/docs/current/sql-altertable.html — `ALTER COLUMN ... TYPE ... USING expr`; transform expressions cannot contain subqueries (affects downgrade).

### Project Conventions

- Standards referenced: .github/instructions/python.instructions.md, test-driven-development.instructions.md, unit-tests.instructions.md, integration-tests.instructions.md, reactjs.instructions.md, fastapi-transaction-patterns.instructions.md, copyright-headers.instructions.md (new migration file)
- Instructions followed: .github/instructions/researcher-enhancements.instructions.md (no new software)

## Key Discoveries

### Current behavior

Host edits an IN_PROGRESS/COMPLETED game, types free text in one box → stored verbatim in `rewards TEXT` → bot renders one `||text||` field; GameDetails shows one blurred box; everything else only checks truthiness.

### Implementation Patterns

- JSON list column + `JSON.stringify` over multipart + `json.loads` in the route is the established pattern (`reminder_minutes`, `notify_role_ids`).
- Zero-width-space field names for continuation fields already used in the embed.

## Recommended Approach

### Storage: JSON `list[str]` column

- `shared/models/game.py`: `rewards: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)` (plain `JSON`, matching existing columns).
- "No rewards" is always NULL: the service stores `update_data.rewards or None` (empty list → NULL).
- The DB imposes no practical size limit; caps live only in code constants.

### Migration (new Alembic revision; `down_revision` = current head)

```sql
-- upgrade: existing text becomes a single entry; blank/NULL become NULL
ALTER TABLE game_sessions
  ALTER COLUMN rewards TYPE json
  USING CASE
    WHEN rewards IS NULL OR btrim(rewards) = '' THEN NULL
    ELSE json_build_array(rewards)
  END;
```

- After upgrade every row has the same shape — no legacy-format handling anywhere in code.
- Keep the USING expression and the downgrade aggregate as constants in a `shared/utils/` module imported by the migration, so integration tests can exercise the exact SQL (see Testing Strategy).
- Downgrade: USING cannot contain subqueries, so add a temp `text` column, `UPDATE ... SET tmp = (SELECT string_agg(value, E'\n\n') FROM json_array_elements_text(rewards))`, drop `rewards`, rename `tmp` → `rewards`. Entry boundaries are lost on downgrade (acceptable).

### API

- `shared/utils/limits.py`: add `MAX_REWARD_ENTRIES = 20`, `MAX_REWARD_LENGTH = 2000` (abuse caps only; raise by changing the constant).
- `shared/schemas/game.py`: update `rewards: list[str] | None` with `max_length=MAX_REWARD_ENTRIES` and per-item `Annotated[str, StringConstraints(max_length=MAX_REWARD_LENGTH)]`; strip and drop blank items in a validator. Response: `rewards: list[str] | None`.
- `services/api/routes/games.py`: keep `rewards: Form()` as a string; `json.loads` it like `reminder_minutes`.

### Form (GameForm / EditGame)

- `formData.rewards: string[]`, initialized from `initialData.rewards ?? ['']`.
- One multiline `TextField` per entry (internal newlines allowed); "+ Add another reward" appends `''`; per-row × remove, hidden when only one row remains.
- On submit (both EditGame paths, :268 and :406): trim, drop blanks, `payload.append('rewards', JSON.stringify(list))` (`[]` clears).
- Save-and-Archive gate (:1095): any non-blank entry.
- Frontend caps in one exported constants module (not inline literals); they mirror the Python constants — if they drift, the API rejects with a validation error (safe failure). Cross-language constant sharing was considered and deferred.

### Discord embed (all-or-nothing inline, link fallback)

1. Inline: one field per reward, value `||entry||`; first field named `🏆 Rewards` (`EMBED_FIELD_REWARDS`), the rest `_ZERO_WIDTH_SPACE`.
2. Inline only if ALL hold: every entry ≤ `DISCORD_EMBED_FIELD_VALUE_LIMIT - 4`; total field count ≤ 25; total embed length ≤ `DISCORD_EMBED_TOTAL_SAFE_LIMIT`, counting the description as trimmable.
3. Otherwise a single `🏆 Rewards` field with `[View rewards](game_url)`. Make `game_url` non-optional on the rewards path (e.g. require `game_id` when `rewards` is set) so the type checker guarantees it; no no-URL branch.
4. No partial display.
5. The fit decision runs before `_trim_embed_if_needed`, so a long description is trimmed rather than pushing rewards to the link.

### Web display

- GameDetails: each entry as its own block inside the existing blur-to-reveal box, `whiteSpace: 'pre-line'`.
- GameCard: unchanged (truthiness).
- `frontend/src/types/index.ts`: `rewards?: string[] | null`.

### Unchanged (verified truthiness-only)

handlers.py reminder DM and archive @mentions (NULL and `[]` both falsy), recurrence clone (`rewards=None`), create/clone routes.

### Testing Strategy (what each layer uniquely proves)

| Layer                             | Covers                                                                                                                                                                   | Cannot prove                                        |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------- |
| Unit (pytest, vitest)             | fit-vs-link decision; field naming; schema validators (blank stripping, caps); service `[]` → NULL; form add/remove/blank-drop/JSON submit; GameDetails per-entry render | Postgres accepts the SQL; Discord accepts the embed |
| Integration (real Postgres + API) | migration SQL; multipart → `json.loads` → Pydantic → SQLAlchemy JSON → response round-trip                                                                               | Discord behavior                                    |
| E2E (real Discord)                | Discord accepts the embeds we build, and our length math matches Discord's counting                                                                                      | —                                                   |

Integration tests:

- Migration conversion: run the shared USING-expression constant as `SELECT <expr> FROM (VALUES ('a'), (''), ('  '), (NULL), (E'line1\nline2')) t(rewards)`; assert `["a"]`, NULL, NULL, NULL, `["line1\nline2"]`. Same approach for the downgrade aggregate (multi-entry list → `\n\n`-joined text). Follow the test_template_signup_method_backfill_migration.py precedent.
- Extend test_rewards_fields.py:88: PUT `rewards=json.dumps(["a", "multi\nline"])` → DB JSON value and GET response match.
- `[]` and all-blank lists store NULL; >`MAX_REWARD_ENTRIES` entries or an entry >`MAX_REWARD_LENGTH` → 422.
- Save-and-archive tests (:298, :371) pass with list rewards.

E2E tests (tests/e2e/test_game_rewards.py):

- Extend :292: multiple rewards → one spoiler field each; first named `🏆 Rewards`, the rest zero-width.
- At-limit: one 1020-char entry → message edit succeeds and renders inline. Highest-value new test: it checks our arithmetic against Discord's real counting (whitespace trimming, zero-width names, non-ASCII). A miscount means a 400 in production.
- Overflow: too many or too-long entries → single link field, and the edit succeeds.
- Archive repost (:108) keeps the per-entry fields.
- No e2e for the form itself; frontend unit tests cover it.

## Implementation Guidance

- **Objectives**: Hosts enter each reward in its own box (multi-line allowed) with add/remove; rewards display per entry on web and Discord without ever exceeding Discord limits.
- **Key Tasks**:
  1. Constants in shared/utils/limits.py + frontend constants module.
  2. Migration SQL constants in `shared/utils/`, the Alembic migration, and the model type change; migration integration tests.
  3. Schema list type + validators; route `json.loads`; service empty → NULL (TDD unit tests; round-trip and 422 integration tests).
  4. Embed formatter: inline-vs-link decision, fields, non-optional `game_url` on the rewards path; unit tests for fit, field-count overflow, total-length overflow, oversize entry; e2e inline, at-limit, overflow and archive tests.
  5. GameForm list UI + EditGame JSON submit + Save-and-Archive gate.
  6. GameDetails per-entry rendering; types update.
  7. Update existing tests to the list format: GameForm.rewards.test.tsx, EditGame/GameDetails tests, test_games_service.py, test_games_helpers.py, test_game_message_formatter.py.
- **Dependencies**: None new. Requires one migration.
- **Success Criteria**:
  - Existing single-string rewards migrate to one-entry lists and display unchanged.
  - Multiple entries, including internal newlines, round-trip edit → save → reload; blank rows dropped; clearing stores NULL.
  - Discord shows per-entry spoiler fields when they fit, otherwise the single link field; no embed update fails due to rewards, including the at-limit e2e case.
  - Migration SQL verified against real Postgres for NULL, blank, whitespace-only, single-line and multi-line values.
  - API rejects >20 entries or >2000-char entries.

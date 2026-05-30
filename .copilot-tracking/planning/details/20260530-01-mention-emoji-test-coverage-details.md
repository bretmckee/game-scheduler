<!-- markdownlint-disable-file -->

# Task Details: Mention and Emoji Resolution Test Coverage

## Research Reference

**Source Research**: #file:../research/20260530-01-mention-emoji-test-coverage-research.md

## Phase 1: Integration Tests

### Task 1.1: Create `tests/integration/test_games_field_display.py`

Create a new integration test file following the `test_games_where_display.py` pattern.
Three tests seed Redis with fake data and verify the full resolution pipeline via HTTP requests.

**Test 1 — Custom emoji round-trip**: Seeds `discord:guild_emojis:{guild_id}` with
`[{"id": "406497579061215235", "name": "testwave", "animated": False}]`. Posts a game with
`:testwave:` and `:thumbsup:` in title, description, and signup_instructions. GETs the game
and asserts all three fields contain `:testwave:` (rendered back from stored token) and
`:thumbsup:` (standard emoji passes through unchanged). Asserts `<:testwave:` is NOT present
in any field.

**Test 2 — Channel mention in description**: Seeds `discord:guild_channels:{guild_id}` with
the posting channel plus a second channel (`LOCATION_CHANNEL_DISCORD_ID = "406497579061215235"`,
`LOCATION_CHANNEL_NAME = "test-general"`). Posts a game with `#test-general` in description.
GETs and asserts `#test-general` is in `description` and `<#406497579061215235>` is not.

**Test 3 — User mention reverse-render**: Seeds `proj:member:1:{guild_id}:{user_id}` with
`global_name="Test Player"`, `username="testplayer"` (key format:
`proj:member:1:{guild_discord_id}:{user_discord_id}`). Injects stored token
`<@987654321098765432>` via template default `description` kwarg (bypasses forward
`resolve_mentions_in_text` regex that would corrupt a raw `<@snowflake>` in POST body).
GETs and asserts `@Test Player` is in `description` and `<@987654321098765432>` is not.

Seed helpers:

- `_seed_guild_emojis(guild_discord_id, emojis)` — calls `redis.set_json(CacheKeys.discord_guild_emojis(guild_discord_id), emojis, ttl=300)`
- `_seed_member_for_display(guild_discord_id, user_discord_id, display_name, username)` — builds member dict and calls `redis.set(CacheKeys.proj_member("1", guild_discord_id, user_discord_id), json.dumps(data), ttl=300)`

The `gen = "1"` value is set by the `seed_bot_freshness` autouse fixture already present in
`tests/integration/conftest.py` — no new fixture is needed.

- **Files**:
  - `tests/integration/test_games_field_display.py` — new file (create)
- **Success**:
  - All three tests pass: `scripts/run-integration-tests.sh tests/integration/test_games_field_display.py` exits 0
  - No xfail markers — this is retrofitting tests against already-correct production code
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 103-338) — complete test code for all three tests
- **Dependencies**:
  - None — tests seed their own Redis data and use existing fixtures

## Phase 2: Augment Existing E2E Tests

### Task 2.1: Augment `test_channel_mention_in_location_displays_as_discord_link`

In `tests/e2e/test_channel_mentions.py`, add description content and `embed.description`
assertions to the existing test function (no new function).

Changes to make:

1. After `target_channel` is determined, fetch the test user:
   `test_user = await discord_helper.client.fetch_user(int(discord_user_id))`
   `test_username = test_user.name`
2. Add to `game_data`: `"description": f"Players should gather in #{channel_name} and ping @{test_username}"`
3. After `embed = message.embeds[0]` and the existing `Where` field assertions, add:
   - Assert `f"<#{target_channel.id}>"` is in `embed.description`
   - Assert `f"<@{discord_user_id}>"` is in `embed.description`

Note: `embed.description` is the main body set via `discord.Embed(description=...)`, not a
named field in `embed.fields`.

- **Files**:
  - `tests/e2e/test_channel_mentions.py` — modify existing test function
- **Success**:
  - Test passes end-to-end with the augmented assertions
  - No new test function added
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 339-365) — augmentation code
- **Dependencies**:
  - `DISCORD_USER_ID` env var (already required by e2e suite)
  - `DISCORD_GUILD_A_CHANNEL_ID` env var (already required by e2e suite)

### Task 2.2: Augment `test_join_notification_with_signup_instructions`

In `tests/e2e/test_join_notification.py`, add channel mention and optional custom emoji to
`signup_instructions` and assert they are resolved in the delivered DM.

Changes to make:

1. Add `import os` if not already present
2. Before building `signup_instructions`:
   - `posting_channel = await main_bot_helper.client.fetch_channel(int(discord_channel_id))`
   - `channel_name = posting_channel.name`
   - `emoji_name = os.environ.get("DISCORD_TEST_EMOJI_NAME", "")`
3. Build `signup_instructions` to include `#{channel_name}`; if `emoji_name` is non-empty, append `:{emoji_name}:` line
4. After existing DM content assertions:
   - Assert `f"<#{discord_channel_id}>"` is in `join_dm.content`
   - If `emoji_name`: assert `f"<:{emoji_name}:"` is in `join_dm.content`

- **Files**:
  - `tests/e2e/test_join_notification.py` — modify existing test function
- **Success**:
  - Test passes with channel mention assertion using existing required env vars
  - Emoji assertion is absent (not evaluated) when `DISCORD_TEST_EMOJI_NAME` is unset
  - Emoji assertion passes when `DISCORD_TEST_EMOJI_NAME` is set and emoji exists in the guild
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 367-393) — augmentation code
- **Dependencies**:
  - Task 3.2 — `compose.e2e.yaml` must pass `DISCORD_TEST_EMOJI_NAME` to the container before this assertion can work

## Phase 3: Add `DISCORD_TEST_EMOJI_NAME` Environment Variable

### Task 3.1: Update `config.template/env.template`

Add a commented-out entry for `DISCORD_TEST_EMOJI_NAME` near the other optional test vars
(near `DISCORD_TEST_ROLE_A_ID` at line 383).

Entry to add:

```
# DISCORD_TEST_EMOJI_NAME=testwave  # Optional: name of a custom emoji in the test guild for e2e emoji resolution tests
```

- **Files**:
  - `config.template/env.template` — add one commented line near line 383
- **Success**:
  - Entry is present and commented out
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 79-84) — optional env var pattern
- **Dependencies**:
  - None

### Task 3.2: Update `compose.e2e.yaml`

Add `DISCORD_TEST_EMOJI_NAME: ${DISCORD_TEST_EMOJI_NAME:-}` to the e2e environment section
near `DISCORD_TEST_ROLE_A_ID` (line 150).

- **Files**:
  - `compose.e2e.yaml` — add one line near line 150
- **Success**:
  - Variable is passed to the e2e container with empty-string fallback
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 79-84) — optional env var pattern
- **Dependencies**:
  - None

### Task 3.3: Update `docs/developer/TESTING.md`

Add a "Custom Emoji E2E Testing" section describing `DISCORD_TEST_EMOJI_NAME`, what it
enables, and how to set it. Place it near the Role-Based Signup Testing section.

- **Files**:
  - `docs/developer/TESTING.md` — add section
- **Success**:
  - Section is present and explains the optional env var and what tests it unlocks
- **Research References**:
  - #file:../research/20260530-01-mention-emoji-test-coverage-research.md (Lines 416-444) — implementation guidance
- **Dependencies**:
  - None

## Dependencies

- Integration test infrastructure (Docker Compose via `scripts/run-integration-tests.sh`)
- E2E test infrastructure (Docker Compose via `scripts/run-e2e-tests.sh`)
- Existing integration fixtures: `create_user`, `create_guild`, `create_channel`, `create_template`, `seed_redis_cache`

## Success Criteria

- `scripts/run-integration-tests.sh tests/integration/test_games_field_display.py` passes (3 tests)
- E2E augmented tests pass for channel and user mention assertions
- E2E emoji assertions skip gracefully when `DISCORD_TEST_EMOJI_NAME` is absent
- `DISCORD_TEST_EMOJI_NAME` is documented and wired through env.template and compose.e2e.yaml

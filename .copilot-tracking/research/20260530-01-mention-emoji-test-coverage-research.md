<!-- markdownlint-disable-file -->

# Task Research Notes: Mention and Emoji Resolution Test Coverage

## Research Executed

### File Analysis

- `services/api/services/emoji_resolver.py`
  - `EmojiResolver.resolve_emoji_mentions()`: forward — reads `discord:guild_emojis:{guild_id}` from Redis, converts `:name:` → `<:name:id>` (animated: `<a:name:id>`)
  - `render_emoji_for_display()`: reverse — converts stored `<:name:id>` / `<a:name:id>` → `:name:` for API response display
  - Standard emoji (`:thumbsup:`, etc.) pass through both directions unchanged since they have no snowflake ID in the Redis cache

- `services/api/services/channel_resolver.py`
  - `ChannelResolver.resolve_channel_mentions()`: forward — reads `discord:guild_channels:{id}` from Redis, converts `#channel-name` → `<#channel_id>`
  - `render_text_for_display()`: reverse — converts `<#id>` → `#name` AND `<@id>` → `@display_name`
  - `extract_user_mention_ids()`: extracts snowflake IDs from `<@id>` tokens for display-name lookup

- `services/api/services/participant_resolver.py`
  - `resolve_mentions_in_text()`: scans text for `r"@\w+(?:\.\w+)*"` tokens, resolves each via Redis member projection prefix search
  - Only handles `@username` input format; `<@snowflake>` in free text would match `@<digits>` and fail lookup
  - Safe inputs for POST: `@username` (resolved forward), or no `@` at all

- `services/api/routes/games.py` (`_render_text_fields`, `_build_game_response`)
  - `_render_text_fields(title, description, signup_instructions, channels, guild_discord_id)` returns 3-tuple
  - Applies `render_emoji_for_display` to all three fields
  - Applies `render_text_for_display` (channel + user reverse) to description and signup_instructions only; title gets emoji reverse only
  - `GameResponse` fields `title`, `description`, `signup_instructions` are ALWAYS the rendered/display versions — no separate `_display` suffix

- `tests/integration/test_games_where_display.py`
  - Template for new integration tests: seeds Redis directly, creates game via POST, GETs and asserts API response fields
  - Uses `_seed_guild_channels()` helper, fixtures: `create_user`, `create_guild`, `create_channel`, `create_template`, `seed_redis_cache`, `api_base_url`

- `tests/e2e/test_channel_mentions.py`
  - Only test: `test_channel_mention_in_location_displays_as_discord_link` — fetches live guild channels, creates game, asserts `where` embed field
  - Gap: description not tested; no emoji or user mention

- `tests/e2e/test_join_notification.py`
  - `test_join_notification_with_signup_instructions` already waits ~60 seconds for DM delivery; `signup_instructions` is plain text only
  - Gap: no emoji, channel, or user mentions in signup_instructions

- `tests/e2e/test_game_announcement.py`
  - `test_game_creation_posts_announcement_to_discord`: plain description and location, verifies embed via `verify_game_embed()`
  - Gap: no emoji, channel, or user mention in description or title

- `tests/e2e/helpers/discord.py`
  - `DiscordTestHelper.client` is a `discord.Client` with `fetch_user(user_id)` available (line 232)
  - `user.name` on the returned user object gives the Discord username for `@username` format in POST

### Code Search Results

- `DISCORD_TEST_ROLE_A_ID` optional env var pattern
  - `compose.e2e.yaml` line 150: `${DISCORD_TEST_ROLE_A_ID:-}` (empty string default)
  - `test_gateway_cache_e2e.py` line 132: `role_id = os.environ.get("DISCORD_TEST_ROLE_A_ID", "")` followed by `pytest.skip(...)` if empty
  - `config.template/env.template` line 383: commented-out entry with description

- Existing required env vars relevant to new tests
  - `DISCORD_USER_ID`: test user snowflake ID — username fetchable at runtime via `client.fetch_user()`
  - `DISCORD_GUILD_A_CHANNEL_ID`: channel snowflake ID — channel name fetchable at runtime via guild channels list (already done in `test_channel_mentions.py`)
  - No existing var for custom emoji name

### Project Conventions

- Optional env vars: commented out in `config.template/env.template`, passed as `${VAR:-}` in `compose.e2e.yaml`, guarded in test with `os.environ.get("VAR", "")` + `pytest.skip()` when absent
- Test augmentation strategy confirmed: add assertions to existing tests that already wait, to avoid duplicating expensive wait times (especially the ~60s DM delay)
- Standard emoji (`:thumbsup:`) pass through unchanged and can be tested without any env var or cache seeding

## Key Discoveries

### Resolution Pipeline Summary

| Field                 | Input Format                            | Forward Resolution                      | Stored Format                  | Display Format                          |
| --------------------- | --------------------------------------- | --------------------------------------- | ------------------------------ | --------------------------------------- |
| `title`               | `:emoji:`                               | `resolve_emoji_mentions()`              | `<:name:id>`                   | `:name:` via `render_emoji_for_display` |
| `description`         | `#channel-name`, `@username`, `:emoji:` | channel → participant → emoji resolvers | `<#id>`, `<@id>`, `<:name:id>` | `#name`, `@displayname`, `:name:`       |
| `signup_instructions` | same as description                     | same as description                     | same as description            | same as description                     |
| `where`               | `#channel-name`                         | `resolve_channel_mentions()`            | `<#channel_id>`                | separate `where_display` field          |

### Standard Emoji Passthrough

`:thumbsup:` and other standard Unicode emoji are NOT in the guild emoji Redis cache. `resolve_emoji_mentions()` skips them (no match), so they are stored as-is and returned as-is. Including one in a test verifies no accidental clobbering of non-custom emoji.

### User Mention Input Constraint

`@username` in description POST resolves via Redis member projection. To use in e2e tests without hardcoding a username: fetch `DISCORD_USER_ID` user object at test time via `discord_helper.client.fetch_user(int(discord_user_id))` and read `.name`. This is a fast REST call and the pattern is already available in the existing helper.

### Channel Name in Description

The `test_channel_mentions.py` test already fetches live guild channels via `guild.fetch_channels()`. The same list can be reused to get the name for the posting channel (`DISCORD_GUILD_A_CHANNEL_ID`), avoiding an extra API call.

### Embed Structure Confirmed

`GameMessageFormatter.build_game_embed()` sets description via `discord.Embed(title=..., description=truncated_description, ...)` — it is `embed.description` (the main body), not a named field. The `verify_game_embed()` helper does not check `embed.description`, so description assertions must be added explicitly to augmented tests.

### Member Projection Key Format Confirmed

`resolve_display_names()` reads `proj:member:{gen}:{guild_id}:{user_id}` (raw JSON, not the `set_json` path — use `redis.set(key, json.dumps(data))`). The `gen` value is seeded to `"1"` by the existing `seed_bot_freshness` autouse fixture in `tests/integration/conftest.py`. No new fixture is needed to support integration test 3.

## Recommended Approach

### Part 1: New Integration Test File — `tests/integration/test_games_field_display.py`

Follows `test_games_where_display.py` pattern exactly. Three tests covering emoji round-trip, channel mention in description, and user mention reverse-render.

#### Projection key format (display name resolution)

`resolve_display_names()` calls `member_projection.get_member(guild_id, user_id)` which reads:

```
proj:member:{gen}:{guild_id}:{user_id}
```

The `gen` value is set to `"1"` by the existing `seed_bot_freshness` **autouse** fixture already present in `tests/integration/conftest.py`. No extra action needed — the key to seed is always `proj:member:1:{guild_discord_id}:{user_discord_id}`.

Member dict shape (from `projection.py` docstring): `{"nick": str|None, "global_name": str|None, "username": str, "roles": list, "avatar_url": str|None}`

Display name fallback order: `nick` → `global_name` → `username`

#### Seed helpers

```python
import json

FAKE_EMOJI_ID = "406497579061215235"
FAKE_EMOJI_NAME = "testwave"
FAKE_MEMBER_DISCORD_ID = "987654321098765432"
FAKE_MEMBER_DISPLAY_NAME = "Test Player"
FAKE_MEMBER_USERNAME = "testplayer"
LOCATION_CHANNEL_DISCORD_ID = "406497579061215235"
LOCATION_CHANNEL_NAME = "test-general"

async def _seed_guild_emojis(guild_discord_id: str, emojis: list[dict]) -> None:
    redis = RedisClient()
    await redis.connect()
    try:
        await redis.set_json(CacheKeys.discord_guild_emojis(guild_discord_id), emojis, ttl=300)
    finally:
        await redis.disconnect()

async def _seed_member_for_display(guild_discord_id: str, user_discord_id: str, display_name: str, username: str) -> None:
    """Seed proj:member:1:{guild_id}:{user_id} so display name resolution works."""
    redis = RedisClient()
    await redis.connect()
    try:
        key = CacheKeys.proj_member("1", guild_discord_id, user_discord_id)
        member_data = {
            "nick": None,
            "global_name": display_name,
            "username": username,
            "roles": [],
            "avatar_url": None,
        }
        await redis.set(key, json.dumps(member_data), ttl=300)
    finally:
        await redis.disconnect()
```

#### Test 1 — Custom emoji round-trip (title + description + signup_instructions)

```python
@pytest.mark.asyncio
async def test_emoji_round_trip_in_all_text_fields(
    create_user, create_guild, create_channel, create_template, seed_redis_cache, api_base_url
):
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=posting_channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    await _seed_guild_emojis(
        guild["guild_id"],
        [{"id": FAKE_EMOJI_ID, "name": FAKE_EMOJI_NAME, "animated": False}],
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_resp = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": f"Tavern Night :{FAKE_EMOJI_NAME}: :thumbsup:",
                    "description": f"Come play :{FAKE_EMOJI_NAME}: :thumbsup: tonight",
                    "signup_instructions": f"DM me :{FAKE_EMOJI_NAME}: :thumbsup:",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200
        data = get_resp.json()
        # Custom emoji round-trips back to :name: shorthand
        assert f":{FAKE_EMOJI_NAME}:" in data["title"]
        assert f":{FAKE_EMOJI_NAME}:" in data["description"]
        assert f":{FAKE_EMOJI_NAME}:" in data["signup_instructions"]
        # Standard emoji passes through unchanged
        assert ":thumbsup:" in data["title"]
        assert ":thumbsup:" in data["description"]
        assert ":thumbsup:" in data["signup_instructions"]
        # Stored token is NOT returned (it has been rendered back)
        assert f"<:{FAKE_EMOJI_NAME}:" not in data["title"]
    finally:
        await cleanup_test_session(session_token)
```

#### Test 2 — Channel mention in description resolves to display name

```python
@pytest.mark.asyncio
async def test_channel_mention_in_description_resolves_to_display_name(
    create_user, create_guild, create_channel, create_template, seed_redis_cache, api_base_url
):
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    template = create_template(guild_id=guild["id"], channel_id=posting_channel["id"])

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    await _seed_guild_channels(
        guild["guild_id"],
        [
            {"id": posting_channel["channel_id"], "name": "general", "type": 0},
            {"id": LOCATION_CHANNEL_DISCORD_ID, "name": LOCATION_CHANNEL_NAME, "type": 0},
        ],
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_resp = await client.post(
                "/api/v1/games",
                data={
                    "template_id": template["id"],
                    "title": "Game Night",
                    "description": f"Meet in #{LOCATION_CHANNEL_NAME} for the game",
                    "scheduled_at": scheduled_at,
                },
            )
            assert create_resp.status_code == 201
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200
        data = get_resp.json()
        assert f"#{LOCATION_CHANNEL_NAME}" in data["description"], (
            f"description should contain #{LOCATION_CHANNEL_NAME}, got: {data['description']}"
        )
        assert f"<#{LOCATION_CHANNEL_DISCORD_ID}>" not in data["description"], (
            "stored token should not appear in API response"
        )
    finally:
        await cleanup_test_session(session_token)
```

#### Test 3 — User mention in description reverse-renders to display name

The forward path (`@username` → `<@id>`) requires the projection sorted set (complex). Instead, seed the stored token directly via template default or a description containing `<@user_id>`, then verify the GET response converts it to `@display_name`. Note: the `resolve_mentions_in_text` regex `r"@\w+(?:\.\w+)*"` would match `@<digits>` from `<@snowflake>` if passed in POST body, causing a failed lookup. To bypass forward resolution safely, use the template's default `description` field to inject the stored token.

```python
@pytest.mark.asyncio
async def test_user_mention_in_description_reverse_renders_to_display_name(
    create_user, create_guild, create_channel, create_template, seed_redis_cache, api_base_url
):
    guild = create_guild(bot_manager_roles=[BOT_MANAGER_ROLE_ID])
    posting_channel = create_channel(guild_id=guild["id"])
    create_user(discord_user_id=TEST_BOT_DISCORD_ID)
    # Template default description pre-contains the stored Discord token
    template = create_template(
        guild_id=guild["id"],
        channel_id=posting_channel["id"],
        description=f"Brought to you by <@{FAKE_MEMBER_DISCORD_ID}>",
    )

    await seed_redis_cache(
        user_discord_id=TEST_BOT_DISCORD_ID,
        guild_discord_id=guild["guild_id"],
        channel_discord_id=posting_channel["channel_id"],
        user_roles=[BOT_MANAGER_ROLE_ID],
    )
    await _seed_member_for_display(
        guild["guild_id"], FAKE_MEMBER_DISCORD_ID, FAKE_MEMBER_DISPLAY_NAME, FAKE_MEMBER_USERNAME
    )

    session_token, _ = await create_test_session(TEST_DISCORD_TOKEN, TEST_BOT_DISCORD_ID)
    try:
        async with httpx.AsyncClient(
            base_url=api_base_url, timeout=10.0,
            cookies={"session_token": session_token},
        ) as client:
            scheduled_at = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
            create_resp = await client.post(
                "/api/v1/games",
                data={"template_id": template["id"], "title": "Game Night", "scheduled_at": scheduled_at},
            )
            assert create_resp.status_code == 201
            game_id = create_resp.json()["id"]

            get_resp = await client.get(f"/api/v1/games/{game_id}")

        assert get_resp.status_code == 200
        data = get_resp.json()
        assert f"@{FAKE_MEMBER_DISPLAY_NAME}" in data["description"], (
            f"description should contain @{FAKE_MEMBER_DISPLAY_NAME}, got: {data['description']}"
        )
        assert f"<@{FAKE_MEMBER_DISCORD_ID}>" not in data["description"], (
            "stored token should not appear in API response"
        )
    finally:
        await cleanup_test_session(session_token)
```

**Note**: `create_template` accepts `description` as a keyword argument (confirmed in `tests/conftest.py` line 722). The default is `f"Test template: {name}"` when not provided, so passing an explicit `<@user_id>` token overrides it cleanly.

### Part 2: Augment Existing E2E Tests — No New Test Functions

#### Embed structure confirmed

The game description is stored in `embed.description` (the main Discord embed body), NOT as a named field in `embed.fields`. This is set directly in `GameMessageFormatter.build_game_embed()` via `discord.Embed(title=..., description=truncated_description, ...)`. All e2e description assertions must use `embed.description`, not field lookup.

#### Augment `test_channel_mention_in_location_displays_as_discord_link`

The test already fetches `guild.fetch_channels()` and stores `target_channel`. Add description to `game_data` before the POST, and add assertions on `embed.description` after embed retrieval. Also fetch the test user's username dynamically:

```python
# After target_channel is determined, before game_data dict:
test_user = await discord_helper.client.fetch_user(int(discord_user_id))
test_username = test_user.name

game_data = {
    ...existing fields...,
    "description": f"Players should gather in #{channel_name} and ping @{test_username}",
}

# After embed = message.embeds[0], after the existing Where assertions:
expected_channel_in_description = f"<#{target_channel.id}>"
expected_user_in_description = f"<@{discord_user_id}>"
assert expected_channel_in_description in embed.description, (
    f"embed.description should contain Discord channel token {expected_channel_in_description}, "
    f"got: {embed.description!r}"
)
assert expected_user_in_description in embed.description, (
    f"embed.description should contain Discord user mention {expected_user_in_description}, "
    f"got: {embed.description!r}"
)
```

#### Augment `test_join_notification_with_signup_instructions`

Add `:emoji_name:` and `#channel-name` to the `signup_instructions` string. The channel name comes from fetching `DISCORD_GUILD_A_CHANNEL_ID` via `main_bot_helper.client.fetch_channel()`. Emoji is conditional on `DISCORD_TEST_EMOJI_NAME`. Both resolve before the DM is sent, so the DM content will contain the Discord token forms.

```python
import os

emoji_name = os.environ.get("DISCORD_TEST_EMOJI_NAME", "")
# Fetch the channel name for the configured channel ID
posting_channel = await main_bot_helper.client.fetch_channel(int(discord_channel_id))
channel_name = posting_channel.name

signup_instructions = (
    f"Join our Discord server at https://discord.gg/example123\n"
    f"Check in at the #{channel_name} channel."
)
if emoji_name:
    signup_instructions += f"\nLook for the :{emoji_name}: reaction."

# After join_dm is received, add after existing assertions:
assert f"<#{discord_channel_id}>" in join_dm.content, (
    f"DM should contain resolved channel token <#{discord_channel_id}>"
)
if emoji_name:
    assert f"<:{emoji_name}:" in join_dm.content, (
        f"DM should contain resolved custom emoji <:{emoji_name}:...>"
    )
```

#### Augment `test_game_creation_posts_announcement_to_discord` (lower priority)

If `DISCORD_TEST_EMOJI_NAME` is set, add `:emoji_name:` to the description and assert in `embed.description`. Since this test doesn't have an expensive wait, it's also acceptable to leave it for a follow-up if the above two cover the critical paths.

### Part 3: New Env Var — `DISCORD_TEST_EMOJI_NAME`

One new optional variable following the `DISCORD_TEST_ROLE_A_ID` pattern:

- `config.template/env.template`: add commented-out entry near other optional test vars
- `compose.e2e.yaml`: add `DISCORD_TEST_EMOJI_NAME: ${DISCORD_TEST_EMOJI_NAME:-}`
- Tests: guard with `emoji_name = os.environ.get("DISCORD_TEST_EMOJI_NAME", "")` and skip/skip-assertions when empty
- `docs/developer/TESTING.md`: add section "Custom Emoji E2E Testing" near the Role-Based Signup section

## Implementation Guidance

- **Objectives**: Cover the user/channel/emoji resolution pipeline with both API-level (integration) and full-stack (e2e) tests
- **Key Tasks**:
  1. Create `tests/integration/test_games_field_display.py` with the three tests above
  2. Augment `test_channel_mention_in_location_displays_as_discord_link` with `description` containing `#channel-name` and `@username`, assert on `embed.description`
  3. Augment `test_join_notification_with_signup_instructions` with `#channel-name` and optional `:emoji_name:` in `signup_instructions`
  4. Add `DISCORD_TEST_EMOJI_NAME` to `env.template`, `compose.e2e.yaml`, and TESTING.md
- **Dependencies**:
  - Custom emoji tests require `DISCORD_TEST_EMOJI_NAME` to be set in the test environment
  - User/channel tests require no new env vars — use existing `DISCORD_USER_ID` and `DISCORD_GUILD_A_CHANNEL_ID`
  - Integration tests require no Discord at all — seed Redis with fake data
- **Success Criteria**:
  - Integration tests pass with fake Redis data, no Discord required
  - E2E channel + user mention assertions pass with existing required env vars
  - E2E emoji assertions skip gracefully when `DISCORD_TEST_EMOJI_NAME` is absent
  - E2E emoji assertions pass when emoji exists in test guild and env var is set

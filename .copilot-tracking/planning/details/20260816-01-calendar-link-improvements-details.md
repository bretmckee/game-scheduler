<!-- markdownlint-disable-file -->

# Task Details: Discord Embed Calendar Link Improvements

## Research Reference

**Source Research**: .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md

## Phase 1: Google Calendar Quick-Add URL Builder (bot-side, self-contained)

### Task 1.1: RED — stub `build_google_calendar_url` and write xfail tests

Add a new pure-function URL builder to `services/bot/utils/discord_format.py`, colocated with `format_duration`/`format_discord_timestamp`/`format_rules_section`. Create the stub first:

```python
def build_google_calendar_url(
    game_title: str,
    description: str | None,
    scheduled_at: datetime,
    expected_duration_minutes: int | None,
    where: str | None,
) -> str:
    """Build a Google Calendar quick-add TEMPLATE URL for a game session.

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("build_google_calendar_url not yet implemented")
```

Add module-level constants next to the stub: `_GOOGLE_CALENDAR_BASE_URL = "https://calendar.google.com/calendar/render"`, `_GOOGLE_CALENDAR_DEFAULT_DURATION_MINUTES = 120` (matches `calendar_export.py`'s duration default, research L109/L141/L273), `_GOOGLE_CALENDAR_TITLE_MAX_LENGTH = 100`, `_GOOGLE_CALENDAR_LOCATION_MAX_LENGTH = 100` (new, explicit caps per Decision 3 — research L274/L313, since `title` is `String(200)` and `where` is unbounded `Text` and neither is covered by the existing `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` constant). Import `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` from `shared.utils.limits` and reuse it as the `details`/description cap (research L156, L274).

Write tests in `tests/unit/services/bot/utils/test_discord_format.py` (new `TestBuildGoogleCalendarUrl` class) marked `@pytest.mark.xfail(reason="build_google_calendar_url not yet implemented", strict=True)`, with real, exact-string assertions:

- Full data (title, description, scheduled_at, expected_duration_minutes, where all provided): assert the exact resulting URL string (base URL + `action=TEMPLATE&text=...&dates=START/END&details=...&location=...`, params in that order, built via `urlencode`).
- Missing `description`: assert `details=` is absent from the URL (param omitted, not present as `details=`).
- Missing `where`: assert `location=` is absent from the URL.
- Missing `expected_duration_minutes`: assert the `dates=` end timestamp is exactly `start + 120 minutes` (`_GOOGLE_CALENDAR_DEFAULT_DURATION_MINUTES`).
- `scheduled_at` naive-vs-aware: assert a naive `datetime` (no tzinfo) and an equivalent UTC-aware `datetime` produce the identical `dates=` value (treat-as-UTC behavior, research L163/L272).
- Title longer than `_GOOGLE_CALENDAR_TITLE_MAX_LENGTH`: assert the raw text is truncated (with a `...` suffix, matching `format_rules_section`'s truncation style at L230-245 of `discord_format.py`) before being percent-encoded into `text=`.
- `where` longer than `_GOOGLE_CALENDAR_LOCATION_MAX_LENGTH`: assert the raw location text is truncated the same way before appearing in `location=`.
- `description` longer than `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`: assert truncation in `details=`.
- Special characters (spaces, `&`, unicode) in `game_title`/`where`: assert the exact percent-encoded output (spaces as `+` per `urlencode`'s default `quote_via=quote_plus`, research L114).

- **Files**:
  - `services/bot/utils/discord_format.py` — add stub, constants, and `import` of `urlencode` (`urllib.parse`) and `timedelta` (`datetime`)
  - `tests/unit/services/bot/utils/test_discord_format.py` — add xfail tests
- **Success**:
  - `uv run pytest tests/unit/services/bot/utils/test_discord_format.py -v` shows all new tests as `xfailed`
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 104-114) — Google Calendar TEMPLATE URL scheme, encoding rules
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 133-163) — recommended builder implementation
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 269-274, 313) — technical requirements and Decision 3 (explicit title/where length guards)
- **Dependencies**: None (first task in phase)

### Task 1.2: GREEN — implement `build_google_calendar_url` and remove xfail

Implement the function per the research's recommended approach (research L143-161), plus the title/where truncation guard from Decision 3:

```python
def build_google_calendar_url(...) -> str:
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)
    start = scheduled_at.strftime("%Y%m%dT%H%M%SZ")
    duration = expected_duration_minutes or _GOOGLE_CALENDAR_DEFAULT_DURATION_MINUTES
    end = (scheduled_at + timedelta(minutes=duration)).strftime("%Y%m%dT%H%M%SZ")

    params = {
        "action": "TEMPLATE",
        "text": _truncate_for_calendar_link(game_title, _GOOGLE_CALENDAR_TITLE_MAX_LENGTH),
        "dates": f"{start}/{end}",
    }
    if description:
        params["details"] = _truncate_for_calendar_link(description, GAME_LIST_DESCRIPTION_SNIPPET_LENGTH)
    if where:
        params["location"] = _truncate_for_calendar_link(where, _GOOGLE_CALENDAR_LOCATION_MAX_LENGTH)

    return f"{_GOOGLE_CALENDAR_BASE_URL}?{urlencode(params)}"
```

Add a small private helper `_truncate_for_calendar_link(text: str, max_length: int) -> str` matching `format_rules_section`'s truncation style (`text[: max_length - 3] + "..."` when over length, else unchanged).

Remove only the `@pytest.mark.xfail` markers from Task 1.1's tests — no assertion changes.

- **Files**:
  - `services/bot/utils/discord_format.py` — implement `build_google_calendar_url` and `_truncate_for_calendar_link`
  - `tests/unit/services/bot/utils/test_discord_format.py` — remove xfail markers only
- **Success**:
  - `uv run pytest tests/unit/services/bot/utils/test_discord_format.py -v` — all tests pass
  - `uv run mypy shared/ services/` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 133-163, 240-252) — builder implementation and URL scheme reference
- **Dependencies**: Task 1.1 completion

## Phase 2: Wire Google Calendar Link into Discord Embed Links Field

### Task 2.1: RED — write xfail tests for the two-link `Links` field

`_add_game_time_fields` (`services/bot/formatters/game_message.py` L136-192) gains a new trailing parameter `google_calendar_url: str | None = None` (default preserves every existing positional-args test unchanged — no existing test in `tests/unit/services/bot/formatters/test_game_message.py` needs modification). `create_game_embed` (L338-433) computes the Google URL via `build_google_calendar_url` (imported from `services.bot.utils.discord_format`, Phase 1) using its own `game_title`/`description`/`scheduled_at`/`expected_duration_minutes`/`where` parameters, and passes it through.

Add new xfail tests to `TestGameMessageFormatterHelpers` in `tests/unit/services/bot/formatters/test_game_message.py`:

- `test_add_game_time_fields_links_field_includes_google_calendar_link_when_provided`: call `_add_game_time_fields(..., calendar_url, google_calendar_url)` with both URLs set; assert the `Links` field's `value` contains both `"[Add to Calendar]"` + `calendar_url` and `"[Google Calendar]"` + `google_calendar_url`, on two separate lines (`\n`-joined).
- `test_add_game_time_fields_links_field_omits_google_calendar_link_when_not_provided`: `calendar_url` set, `google_calendar_url=None`; assert `Links` value does NOT contain `"Google Calendar"`.
- `test_add_game_time_fields_links_field_stays_under_discord_limit_with_long_inputs`: build `create_game_embed` (not the private helper) with a near-max `game_title` (200 chars, the `String(200)` bound from `shared/models/game.py` L58) and a very long `where` (several thousand characters, since `where` is an unbounded `Text` column — research L274/L313), plus a long `description`; assert the resulting `Links` field's rendered `value` length is `< 1024` (Discord's per-field cap).
- `test_create_game_embed_threads_google_calendar_url_into_links_field` (on `create_game_embed`, in whichever existing test class covers it): assert the embed's `Links` field value contains a `calendar.google.com/calendar/render` URL when `game_id` is provided.

Mark all four with `@pytest.mark.xfail(reason="Google Calendar link not yet wired into Links field", strict=True)`.

- **Files**:
  - `tests/unit/services/bot/formatters/test_game_message.py` — add 4 new xfail tests
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -v` shows the 4 new tests as `xfailed`; all pre-existing tests in the file still pass unmodified
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 11, 165-173) — Links field wiring pattern
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 274, 313) — length-guard requirement
- **Dependencies**: Phase 1 completion (`build_google_calendar_url` must exist)

### Task 2.2: GREEN — implement wiring and remove xfail

In `_add_game_time_fields`, extend the `Links` field construction (current code at L182-186):

```python
if calendar_url:
    links_value = f"📅 [Add to Calendar]({calendar_url})"
    if google_calendar_url:
        links_value += f"\n📅 [Google Calendar]({google_calendar_url})"
    embed.add_field(name="Links", value=links_value, inline=True)
else:
    embed.add_field(name="​", value="​", inline=True)
```

In `create_game_embed`, after computing `truncated_description, calendar_url, thumb_url, img_url` (L388-392), compute:

```python
google_calendar_url = discord_format.build_google_calendar_url(
    game_title, description, scheduled_at, expected_duration_minutes, where
)
```

and pass `google_calendar_url` as the new trailing argument to the `_add_game_time_fields(...)` call (L409-417). Add the import `from services.bot.utils.discord_format import build_google_calendar_url` (or `from services.bot.utils import discord_format` matching this file's existing import style at L36-42, whichever keeps the import block consistent — this file currently uses named imports from `discord_format`, so add `build_google_calendar_url` to that same `from ... import (...)` block).

Remove only the `xfail` markers from Task 2.1's tests.

- **Files**:
  - `services/bot/formatters/game_message.py` — wire `build_google_calendar_url` into `create_game_embed`/`_add_game_time_fields`
  - `tests/unit/services/bot/formatters/test_game_message.py` — remove xfail markers only
- **Success**:
  - `uv run pytest tests/unit/services/bot/formatters/test_game_message.py -v` — all tests pass
  - `uv run mypy shared/ services/` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 165-173, 185-204) — verbatim before/after wiring snippets
- **Dependencies**: Task 2.1 completion

### Task 2.3: Refactor — e2e coverage (optional, non-blocking)

Optionally extend `_verify_links_field` in `tests/e2e/helpers/discord.py` (L417-424) to also assert `"calendar.google.com"` appears in the `Links` field value when `expected_game_id` is provided, and add/extend an assertion in `tests/e2e/test_game_announcement.py`. E2E tests require no xfail (written after the implementation exists, per `.github/instructions/test-driven-development.instructions.md`). Existing e2e assertions (`f"/download-calendar/{expected_game_id}" in links_field`, a substring check) are unaffected by the added second line and need no changes regardless.

- **Files**:
  - `tests/e2e/helpers/discord.py` — optional additional assertion
  - `tests/e2e/test_game_announcement.py` — optional additional assertion
- **Success**:
  - If modified: `scripts/run-e2e-tests.sh |& tee output-e2e.txt` passes (per `.github/instructions/test-execution.instructions.md`)
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 76-84) — existing e2e/test coverage of the Links field
- **Dependencies**: Task 2.2 completion

## Phase 3: Redis-Backed Calendar Export Token Helpers (API backend)

### Task 3.1: Add `CacheTTL`/`CacheOperation` constants (trivial, no TDD ceremony)

These are plain data constants (no logic to stub), matching this codebase's existing convention for `CacheTTL`/`CacheOperation` members (see `tests/unit/shared/cache/test_ttl.py` and `test_cache_operation_fetch_guild_value` in `test_operations.py`, both plain non-xfail assertions).

- Add `CALENDAR_EXPORT_TOKEN: int = 300  # 5 minutes - TTL-only expiry, no delete-on-read (see Decisions)` to `CacheTTL` (`shared/cache/ttl.py` L28-46).
- Add `CALENDAR_EXPORT_TOKEN_LOOKUP = "calendar_export_token_lookup"` to `CacheOperation` (`shared/cache/operations.py` L53-68), and add the same string to the `_EXPECTED_OPERATIONS` set near the top of `tests/unit/shared/cache/test_operations.py` (`test_cache_operation_members` asserts the full member set — L50-52).
- Add a direct (non-xfail) test `test_calendar_export_token_ttl` to `tests/unit/shared/cache/test_ttl.py` asserting `CacheTTL.CALENDAR_EXPORT_TOKEN == 300`.
- Add a direct (non-xfail) test `test_cache_operation_calendar_export_token_lookup_value` to `tests/unit/shared/cache/test_operations.py` asserting the string value.

- **Files**:
  - `shared/cache/ttl.py`, `shared/cache/operations.py` — add constants
  - `tests/unit/shared/cache/test_ttl.py`, `tests/unit/shared/cache/test_operations.py` — add/update tests
- **Success**:
  - `uv run pytest tests/unit/shared/cache/test_ttl.py tests/unit/shared/cache/test_operations.py -v` passes
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 38-43, 261-267) — `CacheTTL`/`CacheOperation` conventions
- **Dependencies**: None

### Task 3.2: RED — stub `CacheKeys.calendar_export_token` and write xfail test

```python
@staticmethod
def calendar_export_token(token: str) -> str:
    """Return cache key for a calendar export token.

    Raises:
        NotImplementedError: Method not yet implemented
    """
    raise NotImplementedError("calendar_export_token not yet implemented")
```

Add to `tests/unit/shared/cache/test_keys.py` (matching its existing plain-assertion style at L28-97 — since these existing methods have no RED/GREEN ceremony in this file historically, but this is genuinely new production code, apply the stub+xfail cycle per TDD instructions):

```python
@pytest.mark.xfail(reason="calendar_export_token not yet implemented", strict=True)
def test_calendar_export_token_key():
    key = CacheKeys.calendar_export_token("abc123")
    assert key == "api:calendar_export:abc123"
```

- **Files**:
  - `shared/cache/keys.py` — add stub
  - `tests/unit/shared/cache/test_keys.py` — add xfail test
- **Success**:
  - `uv run pytest tests/unit/shared/cache/test_keys.py -v` shows the new test as `xfailed`
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 45-46) — `CacheKeys` convention
- **Dependencies**: None

### Task 3.3: GREEN — implement `CacheKeys.calendar_export_token` and remove xfail

```python
@staticmethod
def calendar_export_token(token: str) -> str:
    """Return cache key for a calendar export token."""
    return f"api:calendar_export:{token}"
```

- **Files**:
  - `shared/cache/keys.py`
  - `tests/unit/shared/cache/test_keys.py` — remove xfail marker only
- **Success**:
  - `uv run pytest tests/unit/shared/cache/test_keys.py -v` passes
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 45-46)
- **Dependencies**: Task 3.2 completion

### Task 3.4: RED — stub `mint_calendar_export_token`/`get_calendar_export_token` and write xfail tests

Add to `services/api/auth/tokens.py`, directly mirroring `store_user_tokens`/`get_user_tokens` (L89-173):

```python
async def mint_calendar_export_token(game_id: str) -> str:
    """Mint a short-lived opaque token for the public calendar export route.

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("mint_calendar_export_token not yet implemented")


async def get_calendar_export_token(token: str) -> str | None:
    """Resolve a calendar export token to its game_id, or None if missing/expired.

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("get_calendar_export_token not yet implemented")
```

Add xfail tests to `tests/unit/services/api/auth/test_tokens.py`, matching its existing `patch("services.api.auth.tokens.cache_client.get_redis_client", ...)` mocking style (L93-100):

- `test_mint_calendar_export_token_stores_game_id_with_ttl`: mock `RedisClient.set_json`; call `mint_calendar_export_token("game-123")`; assert `set_json` called once with the exact key `CacheKeys.calendar_export_token(<returned token>)` (or assert against `f"api:calendar_export:{token}"` directly), value `{"game_id": "game-123"}`, and `ttl=cache_ttl.CacheTTL.CALENDAR_EXPORT_TOKEN` — per `.github/instructions/unit-tests.instructions.md`'s call-verification requirement, use `assert_called_once_with(...)`, not `assert_called_once()`.
- `test_mint_calendar_export_token_returns_uuid4_token`: assert the returned token is parseable by `uuid.UUID(...)`.
- `test_get_calendar_export_token_returns_game_id_on_hit`: mock `cache_get` (patched at `services.api.auth.tokens.cache_get`) to return `{"game_id": "game-456"}`; assert `get_calendar_export_token("tok")` returns `"game-456"`, and `cache_get` was called with `(CacheKeys.calendar_export_token("tok"), CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP)`.
- `test_get_calendar_export_token_returns_none_on_miss`: mock `cache_get` to return `None`; assert result is `None`.
- `test_get_calendar_export_token_returns_none_on_malformed_data`: mock `cache_get` to return a non-dict (e.g. `"not-a-dict"`) or a dict missing `"game_id"`; assert result is `None` (mirrors `get_user_tokens`'s `isinstance` guard, L155-157).

Mark all with `@pytest.mark.xfail(reason="calendar export token functions not yet implemented", strict=True)`.

- **Files**:
  - `services/api/auth/tokens.py` — add stubs
  - `tests/unit/services/api/auth/test_tokens.py` — add xfail tests
- **Success**:
  - `uv run pytest tests/unit/services/api/auth/test_tokens.py -v` shows the 5 new tests as `xfailed`
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 27-31, 89-135, 206-232) — `store_user_tokens`/`get_user_tokens` template, verbatim code
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 275-278) — no encryption, TTL-only, key/TTL/operation conventions
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 311, 315) — Decisions 1 and 5
- **Dependencies**: Task 3.1, Task 3.3 completion (needs `CacheTTL.CALENDAR_EXPORT_TOKEN`, `CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP`, `CacheKeys.calendar_export_token`)

### Task 3.5: GREEN — implement token mint/get functions and remove xfail

```python
async def mint_calendar_export_token(game_id: str) -> str:
    """Mint a short-lived opaque token for the public calendar export route."""
    redis = await cache_client.get_redis_client()
    token = str(uuid.uuid4())
    key = CacheKeys.calendar_export_token(token)
    await redis.set_json(key, {"game_id": game_id}, ttl=cache_ttl.CacheTTL.CALENDAR_EXPORT_TOKEN)
    logger.info("Minted calendar export token for game %s", game_id)
    return token


async def get_calendar_export_token(token: str) -> str | None:
    """Resolve a calendar export token to its game_id, or None if missing/expired."""
    key = CacheKeys.calendar_export_token(token)
    data = await cache_get(key, CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP)
    if not isinstance(data, dict) or "game_id" not in data:
        logger.warning("No calendar export token found for %s", token)
        return None
    return str(data["game_id"])
```

Add `from shared.cache.keys import CacheKeys` to `tokens.py`'s imports. No encryption — do NOT call `encrypt_token`/`decrypt_token` (Decision, research L276). No `delete_calendar_export_token` counterpart — TTL-only expiry (Decision 1, research L311).

Remove only the `xfail` markers from Task 3.4's tests.

- **Files**:
  - `services/api/auth/tokens.py`
  - `tests/unit/services/api/auth/test_tokens.py` — remove xfail markers only
- **Success**:
  - `uv run pytest tests/unit/services/api/auth/test_tokens.py -v` — all tests pass
  - `uv run mypy shared/ services/` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 89-135, 206-232)
- **Dependencies**: Task 3.4 completion

## Phase 4: Authenticated Mint-Token Route (`services/api/routes/export.py`)

### Task 4.1: RED — stub `mint_calendar_token` route and write xfail tests

Add a new Pydantic response schema to a new file `shared/schemas/export.py`, matching `shared/schemas/auth.py`'s `TokenResponse` style (L49-53):

```python
class CalendarExportTokenResponse(BaseModel):
    """Response for the calendar-export token mint endpoint."""

    token: str = Field(..., description="Opaque short-lived token for the public .ics download route")
```

Add a stub route to `services/api/routes/export.py`, alongside `export_game` (L92-162):

```python
@router.post(
    "/game/{game_id}/token",
    summary="Mint a short-lived calendar export token",
    description="Mint a token for the public, unauthenticated .ics download route",
)
async def mint_calendar_token(
    game_id: str,
    user: Annotated[auth_schemas.CurrentUser, Depends(auth_deps.get_current_user)],
    db: Annotated[AsyncSession, Depends(database.get_db_with_user_guilds())],
    role_service: Annotated[
        roles_module.RoleVerificationService, Depends(permissions_deps.get_role_service)
    ],
) -> CalendarExportTokenResponse:
    """Mint a calendar export token.

    Raises:
        NotImplementedError: Route not yet implemented
    """
    raise NotImplementedError("mint_calendar_token not yet implemented")
```

Add xfail tests to `tests/unit/services/api/routes/test_export.py`, reusing the file's existing `app`/`mock_user`/`mock_game`/`mock_get_user_tokens` fixtures and dependency-override style (L42-133):

- `test_mint_calendar_token_as_host_success`: host requests a token; mock `services.api.auth.tokens.mint_calendar_export_token` to return `"minted-token"`; assert response `200`, `response.json() == {"token": "minted-token"}`, and the mock was called with the game's id.
- `test_mint_calendar_token_not_found`: game lookup returns `None`; assert `404`.
- `test_mint_calendar_token_permission_denied`: `can_export_game` (via role/participant mocks) returns `False`/raises; assert `403`.
- `test_mint_calendar_token_as_participant`: mirrors `test_export_game_as_participant` (L256+).

Mark all with `@pytest.mark.xfail(reason="mint_calendar_token route not yet implemented", strict=True)`.

- **Files**:
  - `shared/schemas/export.py` — new file, `CalendarExportTokenResponse`
  - `services/api/routes/export.py` — add stub route
  - `tests/unit/services/api/routes/test_export.py` — add xfail tests
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_export.py -v` shows the new tests as `xfailed`
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 56-59, 66-67) — `export_game`'s permission-check pattern and `can_export_game` to reuse unmodified
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 178, 296) — mint-route recommendation
  - `.github/instructions/api-authorization.instructions.md` (L188-203) — `can_export_game` worked example
- **Dependencies**: Phase 3 completion (`tokens.mint_calendar_export_token` must exist)

### Task 4.2: GREEN — implement `mint_calendar_token` and remove xfail

Copy `export_game`'s game-fetch + `can_export_game` permission-check block verbatim (L106-133), then replace the `CalendarExportService` call with:

```python
from services.api.auth import tokens
from shared.schemas.export import CalendarExportTokenResponse
...
    token = await tokens.mint_calendar_export_token(game_id)
    return CalendarExportTokenResponse(token=token)
```

Do NOT write inline authorization code — the `can_export_game(...)` call must be the unmodified helper (per `.github/instructions/api-authorization.instructions.md`).

Remove only the `xfail` markers from Task 4.1's tests.

- **Files**:
  - `services/api/routes/export.py`
  - `tests/unit/services/api/routes/test_export.py` — remove xfail markers only
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_export.py -v` — all tests pass
  - `uv run mypy shared/ services/` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 56-59, 178)
- **Dependencies**: Task 4.1 completion

## Phase 5: Public Unauthenticated `.ics` Route + App Registration + Integration Tests

### Task 5.1: RED — stub the second `APIRouter` and write xfail unit tests

Add a second router to `services/api/routes/public.py` (existing `router` is hardcoded to `/api/v1/public/images` and cannot be reused — research L49, Decision 6/L316):

```python
calendar_router = APIRouter(prefix="/api/v1/public/calendar", tags=["public"])


@calendar_router.get("/{token_with_ext}")
@_apply_rate_limits
async def get_calendar_export(
    request: Request,
    token_with_ext: Annotated[str, Path(description="Calendar export token, optionally with .ics")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Serve a game's .ics calendar export by opaque token, without authentication.

    Raises:
        NotImplementedError: Route not yet implemented
    """
    raise NotImplementedError("get_calendar_export not yet implemented")
```

Add xfail tests to `tests/unit/services/api/routes/test_public.py`, matching its `mock_request`/`mock_db` fixtures (L35-47) for direct-call tests, plus a new `calendar_app` fixture mirroring `public_app` (L142-157: `FastAPI()` + `app.include_router(calendar_router)` + `dependency_overrides[get_db]`):

- `test_get_calendar_export_success`: mock `tokens.get_calendar_export_token` to return a `game_id`; mock `db.execute` to return a `GameSession`-like row; mock `CalendarExportService.export_game` to return sample ical bytes; call `get_calendar_export(mock_request, "tok123.ics", mock_db)` directly; assert `response.status_code == 200`, `response.media_type == "text/calendar"`, `response.headers["Content-Disposition"] == 'inline; filename="..."'` (using `generate_calendar_filename`'s real output), `response.body == <ical bytes>`.
- `test_get_calendar_export_missing_extension_still_works`: same as above but token passed without `.ics` suffix.
- `test_get_calendar_export_token_not_found_returns_404`: mock `tokens.get_calendar_export_token` to return `None`; assert `404`.
- `test_get_calendar_export_game_deleted_after_mint_returns_404`: token resolves to a `game_id`, but the `GameSession` lookup returns `None`; assert `404`.
- `test_get_calendar_export_via_test_client_returns_200` (uses the new `calendar_app` fixture + `TestClient`, matching `test_get_image_with_gif_extension_returns_200`'s pattern at L160-164): exercises the `@_apply_rate_limits`-decorated path end-to-end at the unit level.

Mark all with `@pytest.mark.xfail(reason="get_calendar_export route not yet implemented", strict=True)`.

- **Files**:
  - `services/api/routes/public.py` — add `calendar_router` stub
  - `tests/unit/services/api/routes/test_public.py` — add xfail tests + `calendar_app` fixture
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_public.py -v` shows the new tests as `xfailed`
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 48-54, 59, 179) — `get_image`/`head_image` template, `generate_calendar_filename` reuse
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 312, 316, 317) — Decisions 2, 6, 7 (rate-limit tier, router placement, keep `filename=`)
- **Dependencies**: Phase 3 completion (`tokens.get_calendar_export_token`)

### Task 5.2: GREEN — implement `get_calendar_export`, register router, remove xfail

```python
from services.api.auth import tokens
from services.api.routes.export import generate_calendar_filename
from services.api.services.calendar_export import CalendarExportService
from shared.models.game import GameSession
...

@calendar_router.get("/{token_with_ext}")
@_apply_rate_limits
async def get_calendar_export(
    request: Request,
    token_with_ext: Annotated[str, Path(description="Calendar export token, optionally with .ics")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    token = token_with_ext.split(".")[0]
    game_id = await tokens.get_calendar_export_token(token)
    if game_id is None:
        raise HTTPException(status_code=404, detail="Calendar export link not found or expired")

    result = await db.execute(select(GameSession).where(GameSession.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    service = CalendarExportService(db)
    try:
        ical_data = await service.export_game(game_id, "", "", can_export=True)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    filename = generate_calendar_filename(game.title, game.scheduled_at)
    return Response(
        content=ical_data,
        media_type="text/calendar",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
```

Note: `can_export=True` is passed because permission was already verified once, at mint time, by `mint_calendar_token` (Phase 4) — do NOT re-run `can_export_game` here (research L275, matches `calendar_export.py`'s trust-the-caller contract at L62).

Register the new router in `services/api/app.py` next to the existing `app.include_router(public.router)` (L151):

```python
app.include_router(public.calendar_router)
```

Remove only the `xfail` markers from Task 5.1's tests.

- **Files**:
  - `services/api/routes/public.py`
  - `services/api/app.py` — register `public.calendar_router`
  - `tests/unit/services/api/routes/test_public.py` — remove xfail markers only
- **Success**:
  - `uv run pytest tests/unit/services/api/routes/test_public.py -v` — all tests pass
  - `uv run mypy shared/ services/` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 61-64, 179) — `CalendarExportService.export_game`'s trust-the-caller contract
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 89-90) — `app.py` router registration pattern
- **Dependencies**: Task 5.1 completion

### Task 5.3: Integration tests for the public `.ics` route (TDD not required — written after implementation)

Add `tests/integration/services/api/routes/test_public_calendar.py`, modeled on `tests/integration/services/api/routes/test_public_images.py` (store real fixture data via `admin_db`, hit the route through `async_client`, no auth headers):

- `test_get_calendar_export_returns_ics_without_auth`: create a real `GameSession` + mint a real token via `tokens.mint_calendar_export_token`; `GET /api/v1/public/calendar/{token}.ics`; assert `200`, `Content-Type: text/calendar`, `Content-Disposition` contains `inline` and `filename=`.
- `test_get_calendar_export_unknown_token_returns_404`.
- `test_get_calendar_export_expired_token_returns_404` (if feasible to simulate TTL expiry in the integration environment; otherwise cover via a token deleted directly through the Redis test client).

Optionally add `tests/integration/services/api/routes/test_public_calendar_rate_limit.py`, modeled on `test_public_images_rate_limit.py`, verifying the route is subject to the same global rate-limit tier.

Per `.github/instructions/test-driven-development.instructions.md`, integration tests are written directly (no stubs, no xfail — the route already exists after Task 5.2). Per `.github/instructions/test-execution.instructions.md`, run via `scripts/run-integration-tests.sh |& tee output-integration.txt`, never bare `pytest`.

- **Files**:
  - `tests/integration/services/api/routes/test_public_calendar.py` — new
  - `tests/integration/services/api/routes/test_public_calendar_rate_limit.py` — new (optional)
- **Success**:
  - `scripts/run-integration-tests.sh |& tee output-integration.txt` passes
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 123, 300) — integration test placement and precedent
- **Dependencies**: Task 5.2 completion

## Phase 6: Frontend Shared Mint Helper + `DownloadCalendar.tsx` Rewrite

### Task 6.1: RED — create shared mint helper stub and rewrite `DownloadCalendar.test.tsx` with failing tests

Create `frontend/src/api/calendarExport.ts`:

```typescript
import { apiClient } from './client';

export async function mintCalendarExportToken(gameId: string): Promise<string> {
  throw new Error('mintCalendarExportToken not yet implemented');
}

export function buildCalendarExportUrl(token: string): string {
  throw new Error('buildCalendarExportUrl not yet implemented');
}
```

Rewrite `frontend/src/pages/__tests__/DownloadCalendar.test.tsx`: replace the `globalThis.fetch`-mocking tests (the existing 8 tests described in research L76-77) with `test.failing` cases that mock `apiClient.post` (via `vi.mock('../../api/client')` or `vi.spyOn`) instead of `fetch`, and assert on `window.location.href` instead of `URL.createObjectURL`:

- "mints a token and navigates to the public calendar URL": mock `apiClient.post` to resolve `{ data: { token: 'abc123' } }`; assert `window.location.href` was set to `/api/v1/public/calendar/abc123.ics`.
- "shows permission denied message on 403": mock `apiClient.post` to reject with an Axios-shaped error (`response.status = 403`); assert the rendered `Alert` text matches the existing permission-denied copy.
- "shows not found message on 404".
- "shows generic error message on other failures" + assert `console.error` was called.
- "closing the error alert navigates to /my-games" (retained from the existing suite, adapted to the new mint-call failure path).
- Retain, unmodified (no `.failing`, since this behavior is not changing): the loading-state-render test for `authLoading`/`downloading` spinner — this is not new behavior, so no TDD ceremony applies to it (see `.github/instructions/test-driven-development.instructions.md`'s "Writing Tests for Already-Correct Code" — the spinner-render assertion is unchanged, keep as a passing test).

- **Files**:
  - `frontend/src/api/calendarExport.ts` — new stub
  - `frontend/src/pages/__tests__/DownloadCalendar.test.tsx` — rewritten with `test.failing` cases
- **Success**:
  - `cd frontend && npm run test -- DownloadCalendar` shows the new cases as expected failures
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 69-77, 180) — current flow, test coverage, and the mint-then-navigate design
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 71) — relative-URL precedent (`/api/v1/public/images/...` in `GameDetails.tsx`), `window.location.href` idiom precedent (`api/client.ts`, `LoginPage.tsx`)
- **Dependencies**: Phase 5 completion (public `.ics` route and mint route must exist for the flow to be meaningful, though the frontend tests themselves only need the backend's documented contract, not a running server)

### Task 6.2: GREEN — implement mint helper and `DownloadCalendar.tsx` rewrite, remove `.failing`

```typescript
// frontend/src/api/calendarExport.ts
import { apiClient } from './client';

export async function mintCalendarExportToken(gameId: string): Promise<string> {
  const response = await apiClient.post<{ token: string }>(`/api/v1/export/game/${gameId}/token`);
  return response.data.token;
}

export function buildCalendarExportUrl(token: string): string {
  return `/api/v1/public/calendar/${token}.ics`;
}
```

Rewrite `DownloadCalendar.tsx`'s `downloadCalendar` function to call `mintCalendarExportToken(gameId)` then `window.location.href = buildCalendarExportUrl(token)`; catch failures and map `error.response?.status` (403/404/other) to the same three `setError(...)` messages as today; remove the `fetch`/`Blob`/`createObjectURL`/`a.click()` code entirely (dead after this change — no other caller).

Remove only the `.failing` markers from Task 6.1's tests — no assertion changes.

- **Files**:
  - `frontend/src/api/calendarExport.ts`
  - `frontend/src/pages/DownloadCalendar.tsx`
  - `frontend/src/pages/__tests__/DownloadCalendar.test.tsx` — remove `.failing` markers only
- **Success**:
  - `cd frontend && npm run test -- DownloadCalendar` — all tests pass
  - `cd frontend && npm run build` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 180, 71) — rewrite design and relative-URL/navigation idiom
- **Dependencies**: Task 6.1 completion

## Phase 7: Frontend `ExportButton.tsx` / `GameDetails.tsx` Migration

### Task 7.1: RED — write failing tests for the migrated export handlers

`ExportButton.tsx` currently has no test file — create `frontend/src/components/__tests__/ExportButton.test.tsx` with `test.failing` cases (mocking `mintCalendarExportToken` from `frontend/src/api/calendarExport.ts`, Phase 6):

- "mints a token and navigates to the public calendar URL on click".
- "shows a permission-denied alert on 403 mint failure" (assert `window.alert` called with the existing copy, since this component uses `alert(errorMessage)` today, L70).
- "shows a generic alert on other mint failures".

`GameDetails.tsx`'s `handleDownloadCalendar` (L200-239) currently has no dedicated test — add `test.failing` cases to `frontend/src/pages/__tests__/GameDetails.test.tsx` (or a new `GameDetails.calendar_export.test.tsx` if the existing file's fixture setup is heavy, matching the pattern already used by `GameDetails.where_display.test.tsx` for a scoped concern):

- "clicking Export to Calendar mints a token and navigates to the public calendar URL".
- "shows a permission-denied alert on 403 mint failure".

- **Files**:
  - `frontend/src/components/__tests__/ExportButton.test.tsx` — new
  - `frontend/src/pages/__tests__/GameDetails.calendar_export.test.tsx` — new (or added to `GameDetails.test.tsx`)
- **Success**:
  - `cd frontend && npm run test -- ExportButton` and the new `GameDetails` calendar-export tests show as expected failures
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 73-74, 181) — `ExportButton.tsx`/`GameDetails.tsx` current Blob-download flow
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 314) — Decision 4 (migrate both, no desktop-browser regression)
- **Dependencies**: Phase 6 completion (`mintCalendarExportToken`/`buildCalendarExportUrl` must exist)

### Task 7.2: GREEN — migrate both components and remove `.failing`

Replace `ExportButton.tsx`'s `downloadCalendar` (L34-74) and `GameDetails.tsx`'s `handleDownloadCalendar` (L200-239) bodies with the same `mintCalendarExportToken` + `window.location.href = buildCalendarExportUrl(token)` pattern as `DownloadCalendar.tsx` (Phase 6), preserving each component's existing `alert(errorMessage)`-based error UI (do not change the error-presentation mechanism, only the success/token-acquisition mechanism). Remove the `axios.get(..., { responseType: 'blob' })` + Blob-download code from both — dead after this change, no other caller of that pattern remains for calendar export.

Remove only the `.failing` markers from Task 7.1's tests.

- **Files**:
  - `frontend/src/components/ExportButton.tsx`
  - `frontend/src/pages/GameDetails.tsx`
  - `frontend/src/components/__tests__/ExportButton.test.tsx` — remove `.failing` markers only
  - `frontend/src/pages/__tests__/GameDetails.calendar_export.test.tsx` — remove `.failing` markers only
- **Success**:
  - `cd frontend && npm run test` — full suite passes
  - `cd frontend && npm run build` — clean
- **Research References**:
  - .copilot-tracking/research/20260816-01-calendar-link-improvements-research.md (Lines 181, 314)
- **Dependencies**: Task 7.1 completion

## Dependencies

- Python 3.13+, `uv run pytest`, `uv run mypy` (backend)
- Node/`npm` toolchain for `frontend/` (Vitest, `npm run build`)
- Redis (existing `shared.cache` infrastructure) — no new infra
- No new environment variables or config; no database migrations

## Success Criteria

- Discord embed's `Links` field shows both the existing frontend calendar-download link and a new, correctly-encoded Google Calendar quick-add link for games with and without optional fields, staying under Discord's 1024-char field cap even with a long `where`/near-max `title`
- Tapping the Discord-embed calendar link (or either in-app Export button) results in the browser navigating to a `Content-Disposition: inline` `text/calendar` response (verifiable via unit/integration test header assertions), not a forced Blob download
- The new public `.ics` route 404s on missing/expired tokens and never re-runs `can_export_game`
- `services/api/routes/export.py`'s existing authenticated `GET /export/game/{game_id}` endpoint and `CalendarExportService` remain unchanged and functional (not removed)
- Full unit test suite (`uv run pytest tests/unit`), mypy (`uv run mypy shared/ services/`), and frontend build/test (`cd frontend && npm run build && npm run test`) are green
- New integration tests for the public `.ics` route pass via `scripts/run-integration-tests.sh`

<!-- markdownlint-disable-file -->

# Task Details: Auth Route Testing via Fake Discord Server

## Research Reference

**Source Research**: #file:../research/20260308-04-auth-oauth-testing-research.md

---

## Phase 1: `DiscordAPIClient` URL Refactor (TDD)

### Task 1.1: Stub `api_base_url` parameter

Add `api_base_url: str = "https://discord.com/api/v10"` to `DiscordAPIClient.__init__`. Store it as `self._api_base_url` but do not yet use it — the four existing module-level constants (`DISCORD_API_BASE`, `DISCORD_TOKEN_URL`, `DISCORD_USER_URL`, `DISCORD_GUILDS_URL`) continue to drive method behaviour at this step. This ensures the constructor signature is valid for the test file written in Task 1.2.

- **Files**:
  - `shared/discord/client.py` — add `api_base_url` parameter to `__init__`, store as `self._api_base_url`
- **Success**:
  - `DiscordAPIClient()` constructs with no arguments (default unchanged)
  - `DiscordAPIClient(api_base_url="http://localhost:8080")` constructs without error
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 76-90) — `DiscordAPIClient` refactor specification
- **Dependencies**:
  - None

### Task 1.2: Write unit tests for URL configurability (RED — `@pytest.mark.xfail`)

Create `tests/unit/test_discord_client.py` (or add to existing file if present). Write tests asserting that when `DiscordAPIClient` is constructed with `api_base_url="http://fake:9999"`, the HTTP calls made by `get_user_info()`, `get_user_guilds()`, `exchange_code()`, and `refresh_token()` target `http://fake:9999/...` rather than the real Discord base. Mark each with `@pytest.mark.xfail(strict=True, reason="RED: api_base_url not yet wired to internal URLs")`.

- **Files**:
  - `tests/unit/test_discord_client.py` — new or extended test file
- **Success**:
  - Tests are collected by pytest; all run and are reported as `xfail` (expected failures)
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 76-90) — URL derivation logic
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Implement full URL refactor — move constants to instance attributes (GREEN)

Replace all four module-level URL constants with instance attributes derived from `self._api_base_url`:

```python
self._token_url  = f"{api_base_url}/oauth2/token"
self._user_url   = f"{api_base_url}/users/@me"
self._guilds_url = f"{api_base_url}/users/@me/guilds"
```

Update every internal reference in the methods from the module-level names to `self._token_url`, `self._user_url`, `self._guilds_url`. Remove the `@pytest.mark.xfail` decorators from Task 1.2 tests — do NOT change any assertions.

- **Files**:
  - `shared/discord/client.py` — full URL refactor
  - `tests/unit/test_discord_client.py` — remove xfail markers only
- **Success**:
  - All Task 1.2 tests now pass (no longer xfail)
  - No module-level URL constants remain in use by methods
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 76-90) — instance attribute specification
- **Dependencies**:
  - Task 1.2 complete

### Task 1.4: Refactor — remove module-level constants entirely

Delete `DISCORD_API_BASE`, `DISCORD_TOKEN_URL`, `DISCORD_USER_URL`, `DISCORD_GUILDS_URL` from module scope to prevent accidental use. Confirm default construction (`DiscordAPIClient()`) still targets `https://discord.com/api/v10`. Run the full unit test suite.

- **Files**:
  - `shared/discord/client.py` — delete module-level constants
- **Success**:
  - No module-level URL constants remain in `shared/discord/client.py`
  - Full unit test suite passes without regressions
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 76-90)
- **Dependencies**:
  - Task 1.3 complete

---

## Phase 2: Config + OAuth URL Wiring (TDD)

### Task 2.1: Add config fields (stub — fields exist, not yet wired to callsites)

Add to `services/api/config.py` (`ApiConfig`):

```python
discord_api_base_url: str = "https://discord.com/api/v10"
discord_oauth_url: str = "https://discord.com/api/oauth2/authorize"
```

Add to bot config (locate the bot's settings class, likely `services/bot/config.py`):

```python
discord_api_base_url: str = "https://discord.com/api/v10"
```

Do **not** wire these to `DiscordAPIClient()` callsites yet.

- **Files**:
  - `services/api/config.py` — add two fields
  - `services/bot/config.py` — add one field
- **Success**:
  - Fields appear in config and default to current hardcoded values
  - Application starts without errors
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 91-106) — config changes specification
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Write unit tests verifying config fields are forwarded (RED — `@pytest.mark.xfail`)

Write tests confirming that:

1. `DiscordAPIClient()` in `services/api/dependencies/discord.py` receives `api_base_url` from `config.discord_api_base_url`
2. `DiscordAPIClient()` in `services/bot/dependencies/discord_client.py` receives `api_base_url` from `config.discord_api_base_url`
3. `/auth/login` redirect URL uses `config.discord_oauth_url`

Mark all with `@pytest.mark.xfail(strict=True, reason="RED: config fields not yet wired to callsites")`.

- **Files**:
  - `tests/unit/test_discord_dependency.py` — new test file
- **Success**:
  - Tests are collected and reported as `xfail`
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 91-115)
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Wire callsites and `oauth2.py` to config (GREEN)

Three targeted changes:

1. `services/api/dependencies/discord.py` line 44: `DiscordAPIClient(api_base_url=config.discord_api_base_url)`
2. `services/bot/dependencies/discord_client.py` line 44: `DiscordAPIClient(api_base_url=config.discord_api_base_url)`
3. `services/api/auth/oauth2.py`: replace `DISCORD_OAUTH_URL` module-level constant with `get_config().discord_oauth_url`

Remove xfail markers from Task 2.2 tests — do NOT change any assertions.

- **Files**:
  - `services/api/dependencies/discord.py`
  - `services/bot/dependencies/discord_client.py`
  - `services/api/auth/oauth2.py`
  - `tests/unit/test_discord_dependency.py` — remove xfail markers only
- **Success**:
  - All Task 2.2 tests pass
  - No hardcoded Discord URLs remain in any of the three changed files
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 91-115)
- **Dependencies**:
  - Task 2.2 complete

### Task 2.4: Refactor — verify no hardcoded URLs remain; confirm no regressions

Run `grep -rn "discord.com" services/ shared/ --include="*.py"` to confirm no residual hardcoded URLs outside of default values in config/`__init__`. Run full unit and integration test suites.

- **Files**:
  - No code changes expected; fix only if grep finds residual constants
- **Success**:
  - Only allowed occurrences of `discord.com` are default values in `services/api/config.py` and `services/bot/config.py` and the default arg in `shared/discord/client.py`
  - All existing tests pass
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 76-115)
- **Dependencies**:
  - Task 2.3 complete

---

## Phase 3: Fake Discord Service (Infrastructure)

### Task 3.1: Create fake Discord aiohttp script

Create `tests/integration/fixtures/fake_discord_app.py`. The script must:

- Accept `PORT` env var (default `8080`)
- Serve `POST /api/v10/oauth2/token`, `GET /api/v10/users/@me`, `GET /api/v10/users/@me/guilds`
- Return canned success responses suitable for auth flow (configurable via env vars `FAKE_TOKEN_RESPONSE`, `FAKE_USER_RESPONSE`, `FAKE_GUILDS_RESPONSE` as JSON strings, with sensible defaults)
- Exit cleanly on SIGTERM

Example default token response:

```json
{
  "access_token": "fake_access_token",
  "refresh_token": "fake_refresh_token",
  "token_type": "Bearer",
  "expires_in": 604800,
  "scope": "identify guilds"
}
```

Example default user response:

```json
{
  "id": "123456789012345678",
  "username": "testuser",
  "discriminator": "0",
  "global_name": "Test User",
  "avatar": null
}
```

Example default guilds response: `[]`

- **Files**:
  - `tests/integration/fixtures/fake_discord_app.py` — new file
- **Success**:
  - `python tests/integration/fixtures/fake_discord_app.py` starts and responds to `curl http://localhost:8080/api/v10/users/@me`
  - All three routes return 200 with JSON
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 118-155) — fixture design and route table
- **Dependencies**:
  - Phases 1 and 2 complete

### Task 3.2: Add `fake-discord` service to `compose.int.yaml`

Add a `fake-discord` service to `compose.int.yaml`:

- Build context points to `tests/integration/fixtures/fake_discord_app.py` (or use the test image)
- Exposes port 8080 within the integration network
- Add `DISCORD_API_BASE_URL=http://fake-discord:8080` to the `api` service environment in `compose.int.yaml`

- **Files**:
  - `compose.int.yaml` — new `fake-discord` service; `DISCORD_API_BASE_URL` env var on `api` service
- **Success**:
  - `docker compose -f compose.int.yaml up fake-discord` starts without errors
  - API container resolves `http://fake-discord:8080` and receives expected responses
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 156-175) — deployment option 1 (preferred)
- **Dependencies**:
  - Task 3.1 complete

---

## Phase 4: Auth Integration Tests (TDD)

### Task 4.1: Create test file skeleton

Create `tests/integration/test_auth_routes.py` with imports, fixtures, and empty test function stubs (one per endpoint per scenario). Do not add any assertions yet.

- **Files**:
  - `tests/integration/test_auth_routes.py` — new skeleton
- **Success**:
  - File is collected by pytest with no errors; all tests pass trivially (empty bodies)
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 50-74) — testability table
- **Dependencies**:
  - Phases 1–3 complete

### Task 4.2: Write integration tests with real assertions (RED — `@pytest.mark.xfail`)

For each of the 5 endpoints write at minimum a success-path test with real assertions. Mark all with `@pytest.mark.xfail(strict=True, reason="RED: integration infrastructure not yet verified")`.

Minimum test scenarios per endpoint:

| Endpoint             | Primary test                                                                                          |
| -------------------- | ----------------------------------------------------------------------------------------------------- |
| `GET /auth/login`    | Response is 302; `Location` header starts with `http://fake-discord:8080`; Redis contains a state key |
| `GET /auth/callback` | Valid code + matching state → 302 to frontend; user row created in DB; session cookie set             |
| `GET /auth/refresh`  | Valid session with refresh token → 200; new tokens stored in Redis                                    |
| `GET /auth/logout`   | Valid session → 200; session cleared from Redis                                                       |
| `GET /auth/me`       | Valid session → 200; response body contains `username` field                                          |

- **Files**:
  - `tests/integration/test_auth_routes.py` — add real assertions, mark xfail
- **Success**:
  - All new tests are collected and reported as `xfail`
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 50-74) — testability analysis per endpoint
- **Dependencies**:
  - Task 4.1 complete

### Task 4.3: Verify tests pass; remove xfail markers (GREEN)

Run integration tests against the fake Discord service. Debug any failures. Remove `@pytest.mark.xfail` decorators — do NOT change any assertions.

- **Files**:
  - `tests/integration/test_auth_routes.py` — remove xfail markers only
- **Success**:
  - All 5 primary-path tests pass with no xfail markers
  - No `patch()` calls in the test file
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 178-193) — success criteria
- **Dependencies**:
  - Task 4.2 complete; `compose.int.yaml` fake-discord service running

### Task 4.4: Add error-path and edge-case tests

Add tests covering:

- `GET /auth/callback` with state mismatch → 40x
- `GET /auth/callback` when fake Discord token endpoint returns 5xx → 50x
- `GET /auth/callback` with missing `code` query param → 40x
- `GET /auth/refresh` when fake Discord returns 401 → 401 returned to client
- `GET /auth/refresh` with no active session → 401
- `GET /auth/me` with no active session → 401

- **Files**:
  - `tests/integration/test_auth_routes.py` — additional error-path tests
- **Success**:
  - All error-path tests pass
  - Full integration suite passes lint and pre-commit hooks
- **Research References**:
  - #file:../research/20260308-04-auth-oauth-testing-research.md (Lines 50-74) — error scenarios per endpoint
- **Dependencies**:
  - Task 4.3 complete

---

## Dependencies

- `aiohttp` — already listed in `pyproject.toml`; `aiohttp.web` used for fake server
- Doc 03 coverage collection fix must be landed first (per research)

## Success Criteria

- All unit tests for `DiscordAPIClient` URL configurability pass with no xfail markers
- `ApiConfig` exposes `discord_api_base_url` and `discord_oauth_url`; bot config exposes `discord_api_base_url`
- Both production `DiscordAPIClient()` callsites pass `api_base_url` from config; `oauth2.py` reads `discord_oauth_url` from config
- `fake-discord` service starts cleanly in integration compose and is reachable from the API container
- Integration tests cover all 5 auth endpoints via real HTTP with no `patch()` calls
- All changed and new code passes lint and pre-commit hooks

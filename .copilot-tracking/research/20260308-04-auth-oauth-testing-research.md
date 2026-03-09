<!-- markdownlint-disable-file -->

# Task Research Notes: Auth Route Testing via Fake Discord Server

## Research Executed

### File Analysis

- `services/api/routes/auth.py`
  - 5 endpoints: `GET /auth/login`, `GET /auth/callback`, `GET /auth/refresh`, `GET /auth/logout`, `GET /auth/me`
  - 91 statements, 67 missed (26.37% combined at time of measurement — unreliable, see Doc 03)
  - `callback` exchanges an authorization code with Discord for tokens; `refresh` calls Discord token endpoint directly
- `services/api/auth/oauth2.py`
  - `DISCORD_OAUTH_URL = "https://discord.com/api/oauth2/authorize"` — hardcoded module-level constant
  - `exchange_code()` and `refresh_token()` call `DiscordAPIClient` methods
- `shared/discord/client.py`
  - `DISCORD_API_BASE = "https://discord.com/api/v10"` — hardcoded module-level constant
  - 3 derived constants: `DISCORD_TOKEN_URL`, `DISCORD_USER_URL`, `DISCORD_GUILDS_URL`
  - `DiscordAPIClient.__init__` takes no URL arguments; the 4 constants are module-level and baked in at import time
- `services/api/dependencies/discord.py` (line 44)
  - Only callsite constructing `DiscordAPIClient()` for API service — no URL arguments passed
- `services/bot/dependencies/discord_client.py` (line 44)
  - Only callsite constructing `DiscordAPIClient()` for bot service — no URL arguments passed
- `tests/e2e/conftest.py`
  - E2E tests use pre-seeded auth tokens injected directly into Redis; OAuth flow is never exercised

### Code Search Results

- `grep -rn "DiscordAPIClient(" services/ shared/ --include="*.py"` → 2 production callsites confirmed
- `grep -n "DISCORD_API_BASE|DISCORD_TOKEN_URL|DISCORD_USER_URL|DISCORD_GUILDS_URL" shared/discord/client.py` → all 4 are module-level constants
- `grep -n "DISCORD_OAUTH_URL" services/api/auth/oauth2.py` → 1 module-level constant
- `grep -rn "def test_" tests/e2e/ | grep -Ei "auth|login|logout|refresh|callback"` → 0 results
- `aiohttp` listed in `pyproject.toml` → already a project dependency; `aiohttp.test_utils.TestServer` available with no new deps

### Project Conventions

- Standards referenced: `.github/instructions/integration-tests.instructions.md`, `.github/instructions/python.instructions.md`, `.github/instructions/test-driven-development.instructions.md`
- Integration tests use real DB + real Redis + real RabbitMQ via compose infrastructure; no mocking of external HTTP — this is the gap

---

## Key Discoveries

### Why Auth Routes Are Untested

- E2E tests pre-seed tokens directly into Redis and bypass OAuth entirely — by design, since a real OAuth flow requires a human clicking "Authorize" in a browser
- No integration tests exist for any auth endpoint
- `/auth/callback` receives a `code` from Discord's redirect — this cannot be replicated without a real browser doing the OAuth round-trip
- However, the code exchange and all other steps are testable if the HTTP calls to Discord's API can be intercepted by a fake server

### Testability Without a Browser

All 5 auth endpoints are fully testable without a browser once Discord's API URLs are configurable:

| Endpoint             | What to test                                                                                     | Requires browser?                                    |
| -------------------- | ------------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| `GET /auth/login`    | Redirect URL contains correct `client_id`, `scope`, `state`; Redis state key is created          | No                                                   |
| `GET /auth/callback` | User + session created on success; state mismatch → 40x; Discord 5xx → 50x; missing `code` → 40x | No — fake server returns the token exchange response |
| `GET /auth/refresh`  | New tokens stored in Redis; Discord 401 → 401 returned; missing session → 401                    | No                                                   |
| `GET /auth/logout`   | Session + Redis state cleared; no session → 200                                                  | No — no Discord call needed                          |
| `GET /auth/me`       | Returns user from session; no session → 401                                                      | No — no Discord call needed                          |

### URL Hardcoding Problem

Module-level constants derived at import time cannot be monkeypatched in integration tests (the module is already loaded when the API process starts). Overriding them via `patch()` from the test runner container would affect a different process — it would not intercept calls made by the API container. Only configuring the URL before the API container starts (via environment variable) can work.

---

## Recommended Approach

### Part 1 — `DiscordAPIClient` URL Refactor

Make the Discord API base URL an instance attribute defaulting to the current hardcoded value.

**`shared/discord/client.py` changes:**

- Add `api_base_url: str = "https://discord.com/api/v10"` parameter to `__init__`
- Move 4 module-level constants to instance attributes:
  ```python
  self._api_base = api_base_url
  self._token_url = f"{api_base_url}/oauth2/token"
  self._user_url  = f"{api_base_url}/users/@me"
  self._guilds_url = f"{api_base_url}/users/@me/guilds"
  ```
- Update the 4 internal method references from module constants to `self._*`
- Keep no module-level URL constants (remove them entirely to prevent accidental use)

**`services/api/config.py` changes:**

- Add two env-var-backed fields with current hardcoded values as defaults:
  ```python
  discord_api_base_url: str = "https://discord.com/api/v10"
  discord_oauth_url: str = "https://discord.com/api/oauth2/authorize"
  ```

**`services/api/dependencies/discord.py` change:**

- Pass `api_base_url=config.discord_api_base_url` at the single `DiscordAPIClient()` callsite

**`services/bot/dependencies/discord_client.py` change:**

- Bot config does not need `discord_oauth_url` (bot never does OAuth); add `discord_api_base_url` field to bot config with same default
- Pass `api_base_url=config.discord_api_base_url` at the single `DiscordAPIClient()` callsite

**`services/api/auth/oauth2.py` change:**

- Replace `DISCORD_OAUTH_URL` module-level constant with a read from `ApiConfig`:
  ```python
  from services.api.dependencies.config import get_config
  # ...
  oauth_url = get_config().discord_oauth_url
  ```

No functional change in production — all defaults replicate the current hardcoded values.

### Part 2 — Fake Discord HTTP Server Fixture

Use `aiohttp.web` to build a minimal fake Discord API server. `aiohttp.test_utils.TestServer` manages lifecycle. No new dependencies — `aiohttp` is already a project dependency.

**Fake server routes:**

| Route                            | Purpose                                     |
| -------------------------------- | ------------------------------------------- |
| `POST /api/v10/oauth2/token`     | Token exchange (callback) and token refresh |
| `GET  /api/v10/users/@me`        | User info lookup                            |
| `GET  /api/v10/users/@me/guilds` | Guild list                                  |

**Fixture design:**

```python
# tests/integration/fixtures/fake_discord.py
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient

@pytest.fixture
async def fake_discord_server():
    app = web.Application()
    # per-test response configurator stored on app state
    app["responses"] = {}

    async def token_handler(request):
        return web.json_response(app["responses"].get("token", {"error": "not_configured"}),
                                  status=app["responses"].get("token_status", 200))

    async def user_handler(request):
        return web.json_response(app["responses"].get("user", {"error": "not_configured"}),
                                  status=app["responses"].get("user_status", 200))

    async def guilds_handler(request):
        return web.json_response(app["responses"].get("guilds", []),
                                  status=app["responses"].get("guilds_status", 200))

    app.router.add_post("/api/v10/oauth2/token", token_handler)
    app.router.add_get("/api/v10/users/@me", user_handler)
    app.router.add_get("/api/v10/users/@me/guilds", guilds_handler)

    async with TestServer(app) as server:
        yield server
```

Tests set `app["responses"]["token"]`, etc. before calling the endpoint. The `DISCORD_API_BASE_URL` env var is set to `http://localhost:<port>` for the integration test API container via compose override or by passing it directly to the `DiscordAPIClient` in unit tests.

**Deployment in integration tests:**

Because the fake server runs in the test runner container and the API runs in a separate container, the fake server must be reachable from the API container. Options:

1. **Preferred**: Start the fake server in a dedicated `fake-discord` service in `compose.int.yaml` using a small `aiohttp.web` script. Set `DISCORD_API_BASE_URL=http://fake-discord:8080` for the `api` service in the integration compose file. This keeps the fake server running for the entire test run.
2. **Alternative**: Test only the auth flow components that do not require the API container (unit-style integration tests that call `exchange_code()` and `refresh_token()` directly with a fake server port). This avoids needing a shared network server but gives shallower coverage.

Option 1 is recommended for full route coverage.

---

## Implementation Guidance

- **Objectives**: Enable non-mocked integration tests for all 5 auth route endpoints
- **Key Tasks**:
  1. Refactor `DiscordAPIClient` to accept `api_base_url` (prerequisite — enables all downstream steps)
  2. Add `discord_api_base_url` and `discord_oauth_url` to `ApiConfig`; `discord_api_base_url` to bot config
  3. Update the 2 `DiscordAPIClient()` callsites to pass `api_base_url` from config
  4. Update `oauth2.py` to read `discord_oauth_url` from config
  5. Add `fake-discord` service to `compose.int.yaml` (a minimal `aiohttp.web` script serving canned responses)
  6. Write integration tests for all 5 auth endpoints covering success and error paths
- **Dependencies**:
  - The URL refactor (steps 1–4) is a hard prerequisite for all auth integration tests
  - Do NOT start this work until Doc 03 coverage collection fix is landed — otherwise test results are untrustworthy
  - The refactor is a safe, standalone design improvement and can be done independently if desired
- **Success Criteria**:
  - After the fix, integration tests exercise `GET /auth/login`, `GET /auth/callback`, `GET /auth/refresh`, `GET /auth/logout`, `GET /auth/me` via real HTTP to the API container
  - The fake Discord service returns configurable success and error responses
  - No `patch()` calls in auth integration tests — all interactions go through the real request path

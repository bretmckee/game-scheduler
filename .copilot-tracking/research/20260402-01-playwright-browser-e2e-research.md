<!-- markdownlint-disable-file -->

# Task Research Notes: Browser-Driven E2E Tests with pytest-playwright

## Research Executed

### File Analysis

- `tests/e2e/conftest.py`
  - Uses `create_test_session(discord_token, bot_discord_id)` from `tests/shared/auth_helpers.py` to mint session tokens and inject them via `client.cookies.set("session_token", session_token)`
  - Existing fixtures: `authenticated_admin_client`, `authenticated_user_b_client`, `bot_discord_id`, `synced_guild`, `discord_helper`, `test_timeouts`, `admin_db`
- `tests/shared/auth_helpers.py`
  - `create_test_session(discord_token, bot_discord_id, ttl_seconds=604800) -> tuple[str, dict]`: writes a session record directly into Redis with encrypted Discord token; returns `(session_token_uuid, session_data)`
  - `cleanup_test_session(session_token)`: deletes the key from Redis
  - No OAuth involved — session is minted programmatically, bypassing Discord entirely
- `services/api/routes/auth.py`
  - `response.set_cookie(key="session_token", value=session_token, httponly=True, secure=is_production, samesite="lax", max_age=86400, domain=config.cookie_domain)`
  - `is_production` is currently `config.environment == "production"` — this couples the `Secure` flag to the full environment string
- `services/api/config.py`
  - `_get_cookie_domain(frontend_url, backend_url)`: returns `".boneheads.us"` when both URLs share that parent domain (e.g. `game-scheduler-e2e.boneheads.us` backend + a `*.boneheads.us` frontend), or `None` for same-host / unrelated hosts
  - `self.environment = os.getenv("ENVIRONMENT", "development")`
- `config/env.e2e`
  - `BACKEND_URL=http://game-scheduler-e2e.boneheads.us` (plain HTTP; cloudflared tunnel provides HTTPS externally)
  - `FRONTEND_URL` commented out — defaults to `http://localhost:3000`
  - `ENVIRONMENT` commented out — falls through to `"development"`, so `Secure` flag is currently **off** in e2e
  - `FRONTEND_HOST_PORT=3001`, `API_HOST_PORT=8001`
  - Cloudflare tunnel token present — the stack already has a valid HTTPS entry point
- `compose.e2e.yaml` — `e2e-tests` container
  - `BACKEND_URL: http://api:8000` (internal Docker network address, not the cloudflared URL)
  - On `app-network` alongside all services
  - No `FRONTEND_URL` set for the test container — browser tests will need it
- `docker/test.Dockerfile`
  - Based on `python:3.13-slim`; installs gcc, postgresql-client, curl
  - `uv pip install --system -e . && uv pip install --system --group dev`
  - No Playwright browsers installed
- `docker/Caddyfile.staging` — frontend serves on `:80` inside Docker; Caddy proxies `/api/*` to `api:8000`
- `pyproject.toml`
  - `pytest-asyncio>=0.24.0`, `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`
  - No playwright dependency present
  - `markers` list has `e2e` and `integration`; `addopts` excludes both by default

### Code Search Results

- `POST /api/v1/games` as test trigger
  - Used in: `test_game_announcement`, `test_game_cancellation`, `test_game_update`, `test_user_join`, `test_player_removal`, `test_game_image_display`, `test_channel_mentions`, `test_join_notification`, `test_signup_methods`, `test_game_rewards`, `test_game_status_transitions`, `test_game_archive`, `test_game_reminder`, `test_clone_game_e2e`, `test_role_based_signup`
- Frontend pages with direct GUI equivalents
  - `frontend/src/pages/CreateGame.tsx` — maps to `POST /api/v1/games`
  - `frontend/src/pages/EditGame.tsx` — maps to `PUT /api/v1/games/{id}`
  - `frontend/src/pages/CloneGame.tsx` — maps to `POST /api/v1/games/{id}/clone`
  - `frontend/src/components/EditableParticipantList.tsx` — maps to `PUT /api/v1/games/{id}` with `removed_participant_ids`

### External Research

- #fetch:https://pypi.org/project/pytest-playwright/
  - Latest: `pytest-playwright 0.7.2` (Released Nov 23, 2025) — sync fixtures
- #fetch:https://pypi.org/project/pytest-playwright-asyncio/
  - Latest: `pytest-playwright-asyncio 0.7.2` (Released Nov 23, 2025) — async fixtures; requires `pytest-asyncio>=0.26.0` and `asyncio_default_test_loop_scope = session`
- #fetch:https://pypi.org/project/playwright/
  - Latest: `playwright 1.58.0` (Released Jan 30, 2026)
- #fetch:https://playwright.dev/python/docs/test-runners
  - `browser_context_args` fixture at session scope customises all contexts
  - `pytest-playwright-asyncio` provides `async` versions of `page`, `context`, `browser` fixtures
  - Requires `asyncio_default_test_loop_scope = session` (conflicts with current project setting of `function`)
- #fetch:https://playwright.dev/python/docs/docker
  - Official Docker image: `mcr.microsoft.com/playwright/python:v1.58.0-noble`
  - Build-your-own pattern: `FROM python:3.13-... && pip install playwright==1.58.0 && playwright install --with-deps chromium`
  - `--ipc=host` recommended for Chromium in Docker
- #fetch:https://playwright.dev/python/docs/api/class-browsercontext#browser-context-add-cookies
  - `browser_context.add_cookies([{"name": str, "value": str, "domain": str, "path": str, "secure": bool, "httpOnly": bool, "sameSite": "Lax"|"Strict"|"None"}])`
  - Either `url` or both `domain`+`path` are required

### Project Conventions

- Standards referenced: `pyproject.toml` pytest config, `docker/test.Dockerfile` build pattern, `tests/shared/auth_helpers.py` session mint pattern
- Instructions followed: `.github/instructions/python.instructions.md`, `.github/instructions/integration-tests.instructions.md`, `.github/instructions/containerization-docker-best-practices.instructions.md`

---

## Key Discoveries

### Project Structure

- All e2e tests live in `tests/e2e/`, share `conftest.py`, and run via the `e2e-tests` Docker service defined in `compose.e2e.yaml`
- The test container reaches services over the internal `app-network` Docker bridge; the Cloudflare tunnel is the external HTTPS entry point for browsers
- `pytest-asyncio` is already present and configured with `asyncio_mode = "auto"`, but with `asyncio_default_fixture_loop_scope = "function"` — this is **incompatible** with `pytest-playwright-asyncio` which requires `session` scope for its loop

### Implementation Patterns

#### Auth injection pattern (existing, reusable)

```python
# tests/shared/auth_helpers.py — already in use by all e2e fixtures
session_token, _ = await create_test_session(discord_token, bot_discord_id)
client.cookies.set("session_token", session_token)
# cleanup in fixture finalizer:
await cleanup_test_session(session_token)
```

The identical token can be injected into a Playwright `BrowserContext`:

```python
await browser_context.add_cookies([{
    "name": "session_token",
    "value": session_token,
    "domain": ".boneheads.us",   # matches _get_cookie_domain output for e2e URLs
    "path": "/",
    "secure": True,
    "httpOnly": True,
    "sameSite": "Lax",
}])
```

#### Secure cookie flag — required API config change

Current code in `services/api/routes/auth.py`:

```python
is_production = config.environment == "production"
response.set_cookie(..., secure=is_production, ...)
```

This ties the `Secure` flag to the full `ENVIRONMENT` string, meaning e2e would need `ENVIRONMENT=production` to get a secure cookie — which has cascading side-effects on other environment-dependent behaviour.

**Required change:** introduce a dedicated `USE_SECURE_COOKIES` env var in `ApiConfig`:

```python
self.use_secure_cookies = os.getenv("USE_SECURE_COOKIES", "false").lower() == "true"
```

Then in `auth.py`:

```python
response.set_cookie(..., secure=config.use_secure_cookies, ...)
```

Set `USE_SECURE_COOKIES=true` in:

- `config/env.e2e`
- `config/env.staging`
- `config/env.prod`

Leave `config/env.dev` without it (defaults to `false`) so local HTTP development is unaffected.

#### asyncio loop scope conflict

These are two **separate** configuration keys that control different things:

```toml
# Current project setting — each test gets a fresh event loop for its fixtures
asyncio_default_fixture_loop_scope = "function"

# What pytest-playwright-asyncio requires — tests share one session-wide loop
asyncio_default_test_loop_scope = "session"
```

Setting both is syntactically valid. The conflict is **semantic**: `pytest-playwright-asyncio` makes the `playwright` and `browser` fixtures session-scoped, living on the session event loop. Existing async e2e fixtures (`admin_db`, `authenticated_admin_client`, `discord_helper`) are function-scoped and live on fresh per-test event loops. A browser test that needs both simultaneously — e.g. `page` to drive the UI and `discord_helper` to verify Discord results — hits:

```
RuntimeError: Future attached to a different loop
```

**Resolution options:**

**Option A — Change both settings to `session`** (recommended): add `asyncio_default_test_loop_scope = "session"` and change `asyncio_default_fixture_loop_scope` to `"session"`. All fixtures and tests share one loop. Risk: SQLAlchemy async sessions hold loop references at construction; connection pool teardown semantics may change across tests. Requires a full regression run of all e2e and integration tests before adding any browser tests.

**Option B — Use sync `pytest-playwright` instead of `pytest-playwright-asyncio`**: browser actions are synchronous; async helpers like `discord_helper` are called via `asyncio.run()` from the sync test body. Zero loop conflict — existing suite is untouched. More boilerplate at the bridge points.

**Option C — Separate `tests/e2e/browser/` package**: local `conftest.py` overrides loop scope for that subtree, with function-scoped playwright fixtures that match the function loop of existing fixtures. Most complex fixture wiring but cleanest isolation.

Option A is lowest boilerplate if the regression run passes. Option B is the safe fallback if SQLAlchemy session teardown breaks under a shared loop.

#### Docker — test container changes

Two options:

**Option A — extend `test.Dockerfile`** (add browser layer on top of existing image):

```dockerfile
RUN uv pip install --system playwright==1.58.0 pytest-playwright-asyncio==0.7.2
RUN playwright install --with-deps chromium
```

Adds ~400MB to the image. Chromium runs headless as root (sandbox disabled) inside Docker, which is acceptable for trusted test code per Playwright docs.

**Option B — use official Playwright base image** (`mcr.microsoft.com/playwright/python:v1.58.0-noble`) as a separate `browser-tests` service in `compose.e2e.yaml`, sharing `app-network`. Keeps the existing test image lean. More moving parts but cleaner separation.

Option A is lower friction for an initial implementation.

The `e2e-tests` container needs `--ipc=host` in `compose.e2e.yaml` for Chromium shared memory.

#### URL the browser navigates to

The browser inside the container connects to the frontend service over the internal Docker network. With `Caddyfile.staging` the frontend listens on `:80`. The test config needs:

```yaml
# compose.e2e.yaml e2e-tests environment:
FRONTEND_URL: http://frontend:80
```

Or the Playwright fixture uses `base_url="http://frontend:80"` in `browser_context_args`.

Cookies injected with `domain=".boneheads.us"` will **not** be sent to `http://frontend:80` because the domain doesn't match. For internal Docker navigation, use `domain="frontend"` and `path="/"` (no leading dot, exact host match), or use the external cloudflared HTTPS URL for both navigation and cookie domain.

**Recommended:** have browser tests navigate via the cloudflared HTTPS URL (`https://game-scheduler-e2e.boneheads.us`) so the domain matches `.boneheads.us`, the `Secure` flag is honoured correctly, and tests reflect real-world behaviour.

### E2E Tests: GUI Migration Candidates

#### Tier 1 — Direct form actions (highest value)

| Test                      | Current trigger                                 | GUI page                    | Notes                                          |
| ------------------------- | ----------------------------------------------- | --------------------------- | ---------------------------------------------- |
| `test_game_announcement`  | `POST /api/v1/games`                            | `CreateGame`                | Canonical "fill form → Discord announces" flow |
| `test_game_cancellation`  | `DELETE /api/v1/games/{id}`                     | Cancel button in `EditGame` | Destructive UI action                          |
| `test_game_update`        | `PUT /api/v1/games/{id}`                        | `EditGame` form submit      | Edit → Discord message refresh                 |
| `test_game_image_display` | `POST /api/v1/games` with image URLs            | `CreateGame` image fields   | Image fields are form inputs                   |
| `test_channel_mentions`   | `POST /api/v1/games` with `<#channel>` location | `CreateGame` location field | Specific input pattern                         |
| `test_join_notification`  | `POST /api/v1/games` with `signup_instructions` | `CreateGame` form           | Signup instructions is a form field            |

#### Tier 2 — Good fit once Tier 1 is proven

| Test                                                           | Current trigger                      | GUI page                                         |
| -------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------ |
| `test_signup_methods` (4 tests)                                | `POST` + `PUT /api/v1/games`         | `CreateGame` + `EditGame` signup method dropdown |
| `test_player_removal`                                          | `PUT` with `removed_participant_ids` | `EditGame` → `EditableParticipantList`           |
| `test_clone_game_e2e`                                          | `POST /api/v1/games/{id}/clone`      | `CloneGame` page                                 |
| `test_game_rewards` `test_discord_embed_shows_rewards_spoiler` | `POST` + `PUT /api/v1/games`         | `CreateGame` + `EditGame` rewards field          |

#### Keep as REST (time-driven, no GUI trigger)

`test_game_status_transitions`, `test_game_archive`, `test_game_reminder`, `test_game_rewards` `test_save_and_archive_*`, `test_waitlist_promotion`

### Technical Requirements

- `pytest-asyncio` loop scope change: add `asyncio_default_test_loop_scope = "session"` to `pyproject.toml` `[tool.pytest.ini_options]`, or annotate browser tests individually — needs decision
- `--ipc=host` on `e2e-tests` container for Chromium shared memory
- `USE_SECURE_COOKIES=true` in `config/env.e2e`, `config/env.staging`, `config/env.prod`
- `FRONTEND_URL` set to the cloudflared HTTPS URL in `config/env.e2e` for cookie domain alignment
- Browser tests need a new pytest marker (e.g. `browser`) to allow running them independently of non-browser e2e tests

---

## Recommended Approach

Use **`pytest-playwright-asyncio 0.7.2`** with **`playwright 1.58.0`** integrated into the existing pytest e2e suite. Authentication is handled by injecting a programmatically minted `session_token` cookie into the Playwright `BrowserContext` using `create_test_session` — the same helper already used by all existing e2e fixtures. No OAuth flow is automated.

Browsers navigate via the cloudflared HTTPS URL (`https://game-scheduler-e2e.boneheads.us`) so that the `Secure`+`.boneheads.us` cookie domain configuration is realistic end-to-end.

The `Secure` flag is decoupled from `ENVIRONMENT` by introducing `USE_SECURE_COOKIES` as a dedicated env var.

### Recommended Versions

**Software**: `playwright` (Python)
**Recommended Version**: 1.58.0
**Type**: Latest Release
**Support Until**: Rolling release; no LTS concept — pin to a specific version
**Reasoning**: Most recent stable; Docker image `mcr.microsoft.com/playwright/python:v1.58.0-noble` is pinned to match
**Source**: https://pypi.org/project/playwright/

**Software**: `pytest-playwright-asyncio`
**Recommended Version**: 0.7.2
**Type**: Latest Release
**Support Until**: Rolling release
**Reasoning**: Required for async pytest fixtures; same version as `pytest-playwright` sync counterpart; released Nov 23, 2025
**Source**: https://pypi.org/project/pytest-playwright-asyncio/

---

## Implementation Guidance

- **Objectives**:
  1. **Resolve asyncio loop scope** — add `asyncio_default_test_loop_scope = "session"` to `pyproject.toml`, run the full integration and e2e suites, verify no regressions in fixture teardown or DB connection pool behaviour. This is a hard prerequisite: nothing else can proceed until it passes.
  2. Add `USE_SECURE_COOKIES` env var to `ApiConfig` and replace `is_production` in `auth.py`
  3. Add `playwright==1.58.0` and `pytest-playwright-asyncio==0.7.2` to `pyproject.toml` dependencies
  4. Add `playwright install --with-deps chromium` to `docker/test.Dockerfile`
  5. Add `--ipc=host` to `e2e-tests` service in `compose.e2e.yaml`
  6. Set `FRONTEND_URL=https://game-scheduler-e2e.boneheads.us` and `USE_SECURE_COOKIES=true` in `config/env.e2e`
  7. Add `browser` marker to `pyproject.toml`
  8. Add `authenticated_browser_context` fixture to `tests/e2e/conftest.py` using `create_test_session` + `browser_context.add_cookies`
  9. Port Tier 1 tests starting with `test_game_announcement`

- **Key Tasks**:
  - `pyproject.toml`: add `asyncio_default_test_loop_scope = "session"`, then run full suite to confirm teardown correctness
  - `services/api/config.py`: add `self.use_secure_cookies = os.getenv("USE_SECURE_COOKIES", "false").lower() == "true"`
  - `services/api/routes/auth.py`: replace `is_production` with `config.use_secure_cookies`
  - `config/env.e2e`, `config/env.staging`, `config/env.prod`: add `USE_SECURE_COOKIES=true`
  - `pyproject.toml`: add playwright dependency and `browser` marker
  - `docker/test.Dockerfile`: install playwright + chromium
  - `compose.e2e.yaml`: `e2e-tests` service needs `ipc: host` and `FRONTEND_URL`
  - New fixture `authenticated_browser_context` in `tests/e2e/conftest.py`

- **Dependencies**:
  - Loop scope validation must pass before any other step
  - `USE_SECURE_COOKIES` API change must land before browser fixture can work over HTTPS

- **Success Criteria**:
  - `test_game_announcement` passes driven by `CreateGame` page form submission
  - Existing non-browser e2e tests are unaffected
  - Cookie is marked `Secure` in e2e (verified via browser devtools or Playwright `context.cookies()`)
  - `ENVIRONMENT` remains `"development"` in e2e with no side-effects

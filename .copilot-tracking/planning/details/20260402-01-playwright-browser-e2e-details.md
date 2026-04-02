<!-- markdownlint-disable-file -->

# Task Details: Browser-Driven E2E Tests with pytest-playwright

## Research Reference

**Source Research**: #file:../research/20260402-01-playwright-browser-e2e-research.md

## Phase 1: Resolve asyncio Loop Scope

### Task 1.1: Add asyncio_default_test_loop_scope to pyproject.toml

Add `asyncio_default_test_loop_scope = "session"` to the `[tool.pytest.ini_options]` section of `pyproject.toml`. This is required by `pytest-playwright-asyncio` so that the `playwright`, `browser`, and `browser_context` fixtures (which are session-scoped) share the same session-level event loop. The existing `asyncio_default_fixture_loop_scope = "function"` setting can remain — the two keys control different things.

- **Files**:
  - `pyproject.toml` — add `asyncio_default_test_loop_scope = "session"` under `[tool.pytest.ini_options]`
- **Success**:
  - `pyproject.toml` contains both `asyncio_default_fixture_loop_scope = "function"` and `asyncio_default_test_loop_scope = "session"`
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 130-165) — asyncio loop scope conflict and resolution options
- **Dependencies**:
  - None — this is the first step

### Task 1.2: Run full integration and e2e suites to validate loop scope change

Run `scripts/run-integration-tests.sh` and `scripts/run-e2e-tests.sh` to confirm no regressions in fixture teardown, DB connection pool behaviour, or SQLAlchemy async session lifecycle. This is a hard prerequisite: nothing else can proceed until both suites pass clean.

- **Files**: No code changes — validation only
- **Success**:
  - All integration tests pass
  - All e2e tests pass
  - No `RuntimeError: Future attached to a different loop` or connection pool teardown errors
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 130-165) — risk analysis for session loop scope
- **Dependencies**:
  - Task 1.1 completion

## Phase 2: Decouple Secure Cookie Flag from ENVIRONMENT

### Task 2.1: Add use_secure_cookies to ApiConfig

Add `self.use_secure_cookies = os.getenv("USE_SECURE_COOKIES", "false").lower() == "true"` to `ApiConfig.__init__` in `services/api/config.py`. This decouples the `Secure` cookie flag from `ENVIRONMENT`, allowing `Secure=True` in e2e without setting `ENVIRONMENT=production`.

- **Files**:
  - `services/api/config.py` — add `use_secure_cookies` attribute to `ApiConfig.__init__`
- **Success**:
  - `ApiConfig` has a `use_secure_cookies: bool` attribute defaulting to `False`
  - Unit tests for `ApiConfig` pass
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 106-128) — secure cookie flag API change with exact code
- **Dependencies**:
  - Phase 1 completion

### Task 2.2: Replace is_production with config.use_secure_cookies in auth.py

In `services/api/routes/auth.py`, replace the `is_production = config.environment == "production"` local variable with direct use of `config.use_secure_cookies` in the `set_cookie` call.

- **Files**:
  - `services/api/routes/auth.py` — replace `is_production` with `config.use_secure_cookies`
- **Success**:
  - No `is_production` variable remains in `auth.py`
  - Unit tests for auth routes pass
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 106-128) — secure cookie decoupling rationale and pattern
- **Dependencies**:
  - Task 2.1 completion

### Task 2.3: Set USE_SECURE_COOKIES=true in env files

Add `USE_SECURE_COOKIES=true` to `config/env.e2e`, `config/env.staging`, and `config/env.prod`. Leave `config/env.dev` unchanged so local HTTP development is unaffected.

- **Files**:
  - `config/env.e2e` — add `USE_SECURE_COOKIES=true`
  - `config/env.staging` — add `USE_SECURE_COOKIES=true`
  - `config/env.prod` — add `USE_SECURE_COOKIES=true`
- **Success**:
  - e2e, staging, and prod environments set the `Secure` cookie flag; dev does not
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 106-128) — env file configuration guidance
- **Dependencies**:
  - Task 2.1 completion

## Phase 3: Install Playwright Dependencies

### Task 3.1: Add playwright and pytest-playwright-asyncio to pyproject.toml

Add `playwright==1.58.0` and `pytest-playwright-asyncio==0.7.2` to the dev dependencies group in `pyproject.toml`. Verify the existing `pytest-asyncio` constraint satisfies `>=0.26.0` as required by `pytest-playwright-asyncio 0.7.2`.

- **Files**:
  - `pyproject.toml` — add `playwright==1.58.0` and `pytest-playwright-asyncio==0.7.2` to dev group
- **Success**:
  - `uv sync` completes without version conflicts
  - `python -c "import playwright; import pytest_playwright_asyncio"` succeeds in the venv
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 73-94) — version recommendations and sources
- **Dependencies**:
  - Phase 1 completion

### Task 3.2: Add browser pytest marker to pyproject.toml

Add `browser: marks tests as browser-driven` to the `markers` list in `[tool.pytest.ini_options]` in `pyproject.toml`. This allows running browser tests in isolation with `-m browser` and excluding them with `-m "not browser"`.

- **Files**:
  - `pyproject.toml` — add `browser` to markers list
- **Success**:
  - `pytest --markers` shows the `browser` marker
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 188-200) — technical requirements list
- **Dependencies**:
  - None

### Task 3.3: Update test.Dockerfile to install Playwright and Chromium

Add the following two lines to `docker/test.Dockerfile` after the `uv pip install` step:

```dockerfile
RUN uv pip install --system playwright==1.58.0 pytest-playwright-asyncio==0.7.2
RUN playwright install --with-deps chromium
```

Chromium runs headless with sandbox disabled inside Docker under root, which is acceptable per Playwright docs for trusted CI environments.

- **Files**:
  - `docker/test.Dockerfile` — add two `RUN` lines for playwright install after existing pip install step
- **Success**:
  - Docker image builds without errors
  - `playwright --version` succeeds inside the built container
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 168-185) — Docker build options and patterns
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Configure Docker Compose and Environment

### Task 4.1: Add ipc: host to e2e-tests service in compose.e2e.yaml

Add `ipc: host` to the `e2e-tests` service definition in `compose.e2e.yaml`. This is required for Chromium shared memory in Docker; without it, Chromium may crash or produce flaky behaviour.

- **Files**:
  - `compose.e2e.yaml` — add `ipc: host` under the `e2e-tests` service
- **Success**:
  - `compose.e2e.yaml` `e2e-tests` service contains `ipc: host`
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 168-185) — `--ipc=host` requirement for Chromium in Docker
- **Dependencies**:
  - None

### Task 4.2: Set FRONTEND_URL in config/env.e2e

Set `FRONTEND_URL=https://game-scheduler-e2e.boneheads.us` in `config/env.e2e` (uncomment or add the line). Browser tests navigate via the cloudflared HTTPS URL so the `.boneheads.us` cookie domain and `Secure` flag work correctly and tests reflect real-world behaviour.

- **Files**:
  - `config/env.e2e` — set `FRONTEND_URL=https://game-scheduler-e2e.boneheads.us`
- **Success**:
  - `config/env.e2e` has `FRONTEND_URL=https://game-scheduler-e2e.boneheads.us` (uncommented)
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 185-213) — URL routing and cookie domain alignment rationale
- **Dependencies**:
  - Task 2.3 completion

## Phase 5: Add Browser Authentication Fixture

### Task 5.1: Add authenticated_browser_context fixture to tests/e2e/conftest.py

Add an `authenticated_browser_context` async fixture to `tests/e2e/conftest.py`. The fixture mints a session token using the existing `create_test_session` helper, injects it into a new Playwright `BrowserContext` via `add_cookies`, and cleans up via `cleanup_test_session` in the finalizer.

Cookie parameters match the `set_cookie` call in `auth.py` and the domain returned by `_get_cookie_domain` for e2e URLs:

```python
@pytest_asyncio.fixture
async def authenticated_browser_context(browser, admin_discord_token, bot_discord_id):
    session_token, _ = await create_test_session(admin_discord_token, bot_discord_id)
    context = await browser.new_context(base_url="https://game-scheduler-e2e.boneheads.us")
    await context.add_cookies([{
        "name": "session_token",
        "value": session_token,
        "domain": ".boneheads.us",
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "sameSite": "Lax",
    }])
    yield context
    await context.close()
    await cleanup_test_session(session_token)
```

- **Files**:
  - `tests/e2e/conftest.py` — add `authenticated_browser_context` fixture
- **Success**:
  - Fixture provides a Playwright `BrowserContext` with a valid session cookie injected
  - Session token is cleaned up from Redis after each test
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 95-115) — auth injection pattern and cookie parameters
- **Dependencies**:
  - Phase 2 completion (USE_SECURE_COOKIES and config.use_secure_cookies)
  - Phase 3 completion (playwright installed in venv)

## Phase 6: Port Tier 1 Test — test_game_announcement

### Task 6.1: Implement browser-driven test_game_announcement_browser

Create `tests/e2e/test_game_announcement_browser.py`. The test uses `authenticated_browser_context` to navigate to `/create` on `https://game-scheduler-e2e.boneheads.us`, fills the `CreateGame` form fields, submits the form, and asserts that the Discord bot announces the game. Discord verification reuses the same assertion pattern as the existing `test_game_announcement` test.

Mark the test with `@pytest.mark.e2e` and `@pytest.mark.browser`.

- **Files**:
  - `tests/e2e/test_game_announcement_browser.py` — new test file
- **Success**:
  - Test navigates to the `CreateGame` page and fills the form via Playwright
  - Form submission triggers a Discord announcement verified by `discord_helper`
  - Test passes end-to-end in the Docker e2e environment
  - `pytest -m browser` selects the test; `pytest -m "not browser"` excludes it
- **Research References**:
  - #file:../research/20260402-01-playwright-browser-e2e-research.md (Lines 215-245) — Tier 1 migration candidates and `CreateGame` page mapping
- **Dependencies**:
  - All previous phases complete

## Dependencies

- `playwright==1.58.0`
- `pytest-playwright-asyncio==0.7.2`
- `pytest-asyncio>=0.26.0` (verify existing constraint satisfies this)
- Docker test image with Chromium installed
- Cloudflare tunnel active for e2e environment

## Success Criteria

- `test_game_announcement_browser` passes via `CreateGame` UI form submission
- Existing non-browser e2e and integration tests are unaffected
- `ENVIRONMENT` remains `"development"` in e2e with no side-effects
- Cookie is `Secure` in e2e (verified via `context.cookies()`)

---
applyTo: '.copilot-tracking/changes/20260402-01-playwright-browser-e2e-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Browser-Driven E2E Tests with pytest-playwright

## Overview

Integrate `pytest-playwright-asyncio` into the existing e2e suite and port the first Tier 1 test (`test_game_announcement`) to drive the frontend UI via Chromium.

## Objectives

- Resolve the asyncio loop scope incompatibility between `pytest-asyncio` and `pytest-playwright-asyncio`
- Decouple the `Secure` cookie flag from `ENVIRONMENT` to support HTTPS session cookies in e2e
- Install Playwright and Chromium in the test Docker image
- Add an `authenticated_browser_context` fixture that reuses the existing `create_test_session` auth helper
- Implement a browser-driven `test_game_announcement_browser` as the first migrated Tier 1 test

## Research Summary

### Project Files

- `pyproject.toml` — pytest config, dependency groups
- `services/api/config.py` — `ApiConfig`, `_get_cookie_domain`
- `services/api/routes/auth.py` — `set_cookie` with `is_production` flag
- `config/env.e2e`, `config/env.staging`, `config/env.prod` — environment configuration
- `compose.e2e.yaml` — `e2e-tests` Docker service definition
- `docker/test.Dockerfile` — test container build
- `tests/e2e/conftest.py` — shared e2e fixtures
- `tests/shared/auth_helpers.py` — `create_test_session`, `cleanup_test_session`
- `frontend/src/pages/CreateGame.tsx` — UI page targeted by Tier 1 test

### External References

- #file:../research/20260402-01-playwright-browser-e2e-research.md — comprehensive research: versions, loop scope options, Docker patterns, auth injection, Tier 1 candidates

### Standards References

- #file:../../.github/instructions/python.instructions.md — Python conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md — Docker best practices
- #file:../../.github/instructions/integration-tests.instructions.md — e2e test conventions
- #file:../../.github/instructions/test-driven-development.instructions.md — TDD methodology

## Implementation Checklist

### [ ] Phase 1: Resolve asyncio Loop Scope

- [ ] Task 1.1: Add `asyncio_default_test_loop_scope = "session"` to `pyproject.toml`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 11-23)

- [ ] Task 1.2: Run full integration and e2e suites to validate no regressions
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 24-36)

### [ ] Phase 2: Decouple Secure Cookie Flag from ENVIRONMENT

- [ ] Task 2.1: Add `use_secure_cookies` to `ApiConfig` in `services/api/config.py`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 40-53)

- [ ] Task 2.2: Replace `is_production` with `config.use_secure_cookies` in `auth.py`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 54-67)

- [ ] Task 2.3: Set `USE_SECURE_COOKIES=true` in `config/env.e2e`, `config/env.staging`, `config/env.prod`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 68-82)

### [ ] Phase 3: Install Playwright Dependencies

- [ ] Task 3.1: Add `playwright==1.58.0` and `pytest-playwright-asyncio==0.7.2` to `pyproject.toml` dev group
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 85-98)

- [ ] Task 3.2: Add `browser` pytest marker to `pyproject.toml`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 99-111)

- [ ] Task 3.3: Update `docker/test.Dockerfile` to install Playwright and Chromium
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 112-132)

### [ ] Phase 4: Configure Docker Compose and Environment

- [ ] Task 4.1: Add `ipc: host` to `e2e-tests` service in `compose.e2e.yaml`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 135-147)

- [ ] Task 4.2: Set `FRONTEND_URL=https://game-scheduler-e2e.boneheads.us` in `config/env.e2e`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 148-160)

### [ ] Phase 5: Add Browser Authentication Fixture

- [ ] Task 5.1: Add `authenticated_browser_context` fixture to `tests/e2e/conftest.py`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 163-198)

### [ ] Phase 6: Port Tier 1 Test — test_game_announcement

- [ ] Task 6.1: Implement `test_game_announcement_browser` in `tests/e2e/test_game_announcement_browser.py`
  - Details: .copilot-tracking/planning/details/20260402-01-playwright-browser-e2e-details.md (Lines 201-218)

## Dependencies

- `playwright==1.58.0`
- `pytest-playwright-asyncio==0.7.2`
- `pytest-asyncio>=0.26.0` (verify existing constraint satisfies this)
- Docker test image with Chromium installed
- Cloudflare tunnel active for e2e environment

## Success Criteria

- `test_game_announcement_browser` passes via `CreateGame` UI form submission end-to-end
- Existing non-browser e2e and integration tests are unaffected
- `ENVIRONMENT` remains `"development"` in e2e with no side-effects
- Cookie is `Secure` in e2e (verified via `context.cookies()`)

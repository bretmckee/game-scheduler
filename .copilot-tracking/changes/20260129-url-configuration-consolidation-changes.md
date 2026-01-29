<!-- markdownlint-disable-file -->

# Release Changes: URL Configuration Consolidation and Naming Clarification

**Implementation Date**: 2026-01-29

## Summary

Consolidated redundant API_BASE_URL and API_URL environment variables into a single BACKEND_URL variable, corrected misleading configuration comments, and fixed incorrect staging environment URLs. This improves configuration clarity by establishing symmetric naming (FRONTEND_URL / BACKEND_URL) and eliminating the confusing "relative URL" pattern.

## Changes

### Modified

**Configuration Files:**
- config/env.dev - Consolidated API_BASE_URL and API_URL into single BACKEND_URL variable, updated comments to accurately describe usage (FRONTEND_URL for CORS/bot links, BACKEND_URL for all backend API access)
- config/env.prod - Consolidated API_BASE_URL and API_URL into single BACKEND_URL variable, updated comments
- config/env.staging - Fixed incorrect FRONTEND_URL (removed port :3000, changed to https://staging.mydomain.com), consolidated API_BASE_URL and API_URL into single BACKEND_URL, updated comments
- config/env.e2e - Consolidated API_BASE_URL and API_URL into single BACKEND_URL variable, updated comments
- config/env.int - Consolidated API_BASE_URL and API_URL into single BACKEND_URL variable, updated comments
- config.template/env.template - Consolidated API_BASE_URL and API_URL into single BACKEND_URL variable with clear documentation stating "always use full URL - no relative URL pattern"

**Code:**
- services/bot/config.py - Renamed api_base_url field to backend_url in BotConfig
- services/bot/formatters/game_message.py - Updated to use config.backend_url for Discord embed image URLs
- services/api/config.py - Removed unused api_url field from APIConfig (was stored but never used)
- frontend/src/api/client.ts - Updated to use BACKEND_URL instead of API_URL in runtime config, updated comments to reflect that BACKEND_URL is always required
- frontend/src/vite-env.d.ts - Updated TypeScript interface from VITE_API_URL to VITE_BACKEND_URL

**Docker & Compose:**
- compose.yaml - Updated bot service to use BACKEND_URL environment variable instead of API_BASE_URL, updated frontend build args from VITE_API_URL to VITE_BACKEND_URL, updated frontend runtime environment from API_URL to BACKEND_URL, removed unused API_URL from API service
- compose.override.yaml - Updated development build args and environment from VITE_API_URL to VITE_BACKEND_URL
- compose.e2e.yaml - Updated e2e test environment from API_BASE_URL to BACKEND_URL
- docker/frontend-entrypoint.sh - Updated to substitute BACKEND_URL instead of API_URL in config template, updated echo message
- docker/frontend-config.template.js - Updated runtime config template to use BACKEND_URL instead of API_URL

**Tests:**
- tests/conftest.py - Updated api_base_url fixture to read from BACKEND_URL environment variable instead of API_URL
- tests/e2e/test_00_environment.py - Updated environment variable check from API_BASE_URL to BACKEND_URL
- tests/services/bot/formatters/test_game_message.py - Updated test to patch BACKEND_URL instead of API_BASE_URL
- tests/services/api/test_config.py - Removed api_url from test environment variables and assertions (field no longer exists)

**Documentation:**
- DEPLOYMENT_QUICKSTART.md - Updated all references from API_URL to BACKEND_URL, updated configuration examples to show FRONTEND_URL=https://example.com and BACKEND_URL=https://example.com pattern, removed confusing "leave API_URL empty" pattern
- TESTING_OAUTH.md - Updated environment configuration example from API_URL to BACKEND_URL
- RUNTIME_CONFIG.md - Updated all references from API_URL to BACKEND_URL, updated proxy mode documentation to reflect that BACKEND_URL must always be set (no empty value pattern), updated configuration examples

### Removed

- Dual API_BASE_URL/API_URL configuration pattern - Now uses single BACKEND_URL variable throughout
- "Relative URL" configuration pattern - All configurations now use explicit full URLs
- Misleading comments about FRONTEND_URL being "used by API to construct redirect URLs after authentication" (OAuth redirects actually come from window.location.origin)
- Misleading comments about API_BASE_URL being used for "OAuth redirects" (never actually used for that purpose)

### Added

None

## Issues Fixed

### Discord Calendar Download Link Issues

**Problem**: Calendar download links in Discord messages were going to wrong URL and wrong port
- FRONTEND_URL was set to `https://game-scheduler.boneheads.us:3000` (incorrect port, should be standard HTTPS port 443)
- Calendar links pointed to `https://game-scheduler.boneheads.us:3000/download-calendar/{game_id}` (incorrect)
- Correct URL should be `https://game-scheduler.boneheads.us/download-calendar/{game_id}` (no port)

**Root Cause**: Staging configuration had incorrect FRONTEND_URL with explicit port when frontend is served through reverse proxy on standard HTTPS port

**Fix**: Updated config/env.staging FRONTEND_URL from `https://game-scheduler.boneheads.us:3000` to `https://staging.mydomain.com` (no port)

### Configuration Comment Accuracy

**Problem**: Configuration file comments were misleading and didn't reflect actual code behavior
- FRONTEND_URL comment said "Used by API to construct redirect URLs after authentication" but OAuth redirects actually come from frontend's window.location.origin
- API_BASE_URL comment said "Used by bot for constructing callback URLs and links" but bot never uses it for OAuth callbacks
- API_URL comment was accurate but the "leave empty for relative URLs" pattern was unnecessarily complex

**Fix**: Updated all configuration comments to accurately describe actual usage:
- FRONTEND_URL: "Frontend URL for CORS allowlist and bot calendar download links"
- BACKEND_URL: "Backend API URL for all services (bot image embeds, frontend API calls)"

### Redundant Configuration Variables

**Problem**: Two variables (API_BASE_URL and API_URL) both pointed to the backend API, creating confusion
- API_BASE_URL used by bot for Discord embed image URLs
- API_URL used by frontend for API calls
- In practice, both always had (or should have had) the same value
- The API service stored API_URL but never actually used it

**Fix**: Consolidated into single BACKEND_URL variable used consistently by bot, frontend, and all services

## Configuration Pattern Changes

### Before (Confusing):
```bash
# Frontend URL for bot redirects and OAuth callbacks
# Used by API to construct redirect URLs after authentication
FRONTEND_URL=https://example.com:3000

# External API base URL for Discord embeds and OAuth redirects
# Used by bot for constructing callback URLs and links
API_BASE_URL=https://example.com:5000

# API endpoint URL for frontend to call
# Leave empty to use relative URLs (nginx proxy configuration)
# For separate API host, specify full URL
API_URL=
```

### After (Clear):
```bash
# Frontend URL for CORS allowlist and bot calendar download links
FRONTEND_URL=https://example.com

# Backend API URL for all services (bot image embeds, frontend API calls)
# Always use full URL - no relative URL pattern
BACKEND_URL=https://example.com
```

## Benefits

1. **Clearer naming**: FRONTEND_URL / BACKEND_URL is symmetric and intuitive
2. **Single source of truth**: One variable for backend URL instead of two
3. **Accurate documentation**: Comments now match actual code behavior
4. **Simpler configuration**: No special cases, no "leave empty" patterns
5. **Explicit URLs**: Always use full URLs for clarity and debugging
6. **Fixed production bugs**: Staging calendar links now work correctly

## Verification

- All configuration files updated consistently
- All code references updated (bot, frontend, API)
- All Docker compose files updated
- All test fixtures updated
- All documentation updated
- No remaining references to API_URL or API_BASE_URL in active code

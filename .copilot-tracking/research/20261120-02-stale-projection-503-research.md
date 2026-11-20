<!-- markdownlint-disable-file -->

# Task Research Notes: Return 503 (not 404 / empty results) When the Bot Projection Is Stale

## Research Executed

### Problem Statement

When the bot's Redis guild projection is not fresh (no bot heartbeat within `_BOT_FRESHNESS_SECONDS = 120`, shared/cache/projection.py line 34, lines 105-123 `is_bot_fresh`), the API currently answers inconsistently:

- Some paths return **503 "Bot is temporarily unavailable; please try again"**.
- Others return **404 "Game not found" / "Template not found"**, **403**, or a **silently empty list**.

Users are told their game doesn't exist during a bot outage. The goal is a single, simple rule: **while the projection is stale, every authenticated guild-scoped request fails with 503, before any resource is loaded.** This also guarantees no information disclosure, since existing and non-existent IDs get the same answer.

Decisions already made (user, 2026-11-20):

- The problem is rare (never observed in production), so keep it simple: no partial lists, no "results may be incomplete" flags, and no frontend retry or backoff.
- Freshness is checked first, so everyone gets 503 regardless of membership or whether the resource exists.
- Authentication still runs first: logged-out users get the normal 401 / login redirect.

### File Analysis

- shared/database.py
  - Lines 122-175 `get_db_with_user_guilds()`: the per-request DB dependency.
    - It depends on `auth.get_current_user`, then reads `member_projection.get_user_guilds(...) or []` (line ~152) and sets up RLS (line ~157) before yielding the session.
    - It runs **before every handler body** on the games, templates, guilds and export routes.
    - When stale it never checks freshness. An absent or empty guild list gives empty RLS, so later loads look like "not found".
- services/api/database/queries.py lines 121-160 `require_guild_by_id`: the same `get_user_guilds(...) or []` + RLS setup when the context isn't already set, then 404 `not_found_detail`.
- services/api/dependencies/permissions.py
  - Lines 55-85 `_check_guild_membership`: **returns False when stale** (lines 74-80). Callers turn that into 404.
  - Lines 88-150 `verify_guild_membership`: **raises 503 when stale** (lines 117-126). This is the desired behaviour and message.
  - Lines 152-200 `verify_template_access` → `_check_guild_membership` (line 188) → 404 "Template not found".
  - Lines 202-275 `verify_game_access` → `_check_guild_membership` (line 242) → 404 "Game not found".
  - Lines 453-500 `get_guild_name`: raises 503 when stale (line 477).
  - Lines 633-676 `can_manage_game` and 677-729 `can_export_game` call `verify_guild_membership`, so they already 503.
- services/api/routes/games.py
  - Lines 640-660 `get_game`: loads the game **first** (404 if missing), then `verify_game_access`. Raising 503 inside `verify_game_access` alone would distinguish existing IDs (503) from missing ones (404), so the check must come before the load.
  - Lines ~575-610 list games: loops `verify_game_access` with `except HTTPException: continue`. **When stale every game is skipped, giving a silently empty list.** A 503 raised inside the loop would also be swallowed.
  - Other `verify_game_access` / `can_manage_game` sites: lines 154, 520, 655, 663, 722, 730, 882, 1043, 1081.
- services/api/routes/guilds.py line 76: list guilds uses `get_user_guilds(...) or []`, so a stale projection gives an empty guild list. Lines 113, 214, 270 and 316 call `verify_guild_membership` (already 503).
- services/api/routes/channels.py line 88: `verify_guild_membership` (already 503).
- services/api/routes/templates.py lines 104, 190, 210: `require_guild_by_id` / `verify_template_access` (404 when stale).
- services/api/routes/export.py lines 126, 204: `can_export_game` (already 503).
- services/api/services/games.py lines 952, 2164, 2287: `can_manage_game` (already 503).
- services/api/auth/roles.py lines 82, 165: `get_user_roles` from the projection (stale → no roles → possible 403). These are covered once the request has already failed with 503 upstream.
- services/api/services/sse_bridge.py lines 140-185: background SSE event filtering via `get_user_guilds`. There is no HTTP response to change. **Out of scope** (stale → events withheld, which is safe).
- services/api/routes/public.py (public images / calendar), auth.py, maintainers.py, sse.py: they don't use `get_db_with_user_guilds` or the membership helpers, so they are unaffected.
- frontend/src/api/client.ts lines 63-101: the only status-specific handling is the 401 refresh/redirect. frontend/src/pages/GameDetails.tsx line 108 (and other pages) shows `err.response?.data?.detail`. **No frontend change is needed**: the 503 detail text is displayed as-is.

### Code Search Results

- `is_bot_fresh` in services/api: permissions.py lines 74, 117, 477 only.
- `get_user_guilds` in services/api + shared: database.py 152, queries.py 148, permissions.py 82/128, guilds.py 76, sse_bridge.py 151.
- `get_db_with_user_guilds` used by routes: games.py, export.py, templates.py, guilds.py.

### External Research

- Source: https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/ — an exception raised in a dependency before `yield` aborts the request with that `HTTPException` response, and the endpoint body never runs.
- Source: RFC 9110 §15.6.4 (https://www.rfc-editor.org/rfc/rfc9110#name-503-service-unavailable) — 503 means the server is temporarily unable to handle the request. This is the correct semantic for a stale upstream projection, and 404 is not.

### Project Conventions

- Standards referenced: .github/instructions/python.instructions.md, test-driven-development.instructions.md, unit-tests.instructions.md, integration-tests.instructions.md, fastapi-transaction-patterns.instructions.md, api-authorization.instructions.md.

## Key Discoveries

### Current Behaviour When Stale

| Path                                                                              | Today                         | Desired                  |
| --------------------------------------------------------------------------------- | ----------------------------- | ------------------------ |
| GET/PUT game, game actions via `verify_game_access`                               | 404 "Game not found"          | 503                      |
| List games                                                                        | 200 `[]` (every game skipped) | 503                      |
| Template access via `verify_template_access` / `require_guild_by_id`              | 404                           | 503                      |
| List guilds (guilds.py 76)                                                        | 200 `[]`                      | 503                      |
| `verify_guild_membership`, `get_guild_name`, `can_manage_game`, `can_export_game` | 503                           | 503 (unchanged)          |
| SSE event filtering                                                               | events withheld               | unchanged (out of scope) |

### Why the Check Must Run Before Loading

`get_game` returns 404 for a missing ID before any membership check. Raising 503 only inside the access helpers would make an existing game (503) distinguishable from a missing one (404). A single check in the request dependency, before RLS setup and before any load, gives an identical 503 for every ID and every user.

## Recommended Approach

1. **One gate in the request dependency.** In `get_db_with_user_guilds` (shared/database.py 122-175), after `current_user` is resolved and **before** `get_user_guilds` / RLS setup, call `member_projection.is_bot_fresh(redis=redis)`. If it's False, raise `HTTPException(503, "Bot is temporarily unavailable; please try again")`. Reuse the exact detail string from permissions.py 117-126; extract a shared constant or helper (e.g. `raise_if_projection_stale(redis)`) used by both places.
2. **Make the helpers consistent (defence in depth).** Change `_check_guild_membership` (permissions.py 74-80) to raise the same 503 instead of returning False, so any path that bypasses the DB dependency still gets 503, not 404. Make the same change in `require_guild_by_id` (queries.py 145-150) before its RLS setup.
3. **Don't swallow 503 in the list loop.** In routes/games.py ~575-610, re-raise an `HTTPException` whose status is 503 instead of `continue`. This only matters if step 1 is ever bypassed.
4. **No frontend change**: the existing `detail` display shows the 503 message.
5. **Out of scope**: SSE bridge filtering; the public calendar and image routes.

### Testing Strategy

| Level       | Existing tests affected                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | New tests needed                                                                                                                                                                                                                                                         | What only this level proves                                                                     |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Unit        | tests/unit/services/api/dependencies/test_api_permissions.py 646-700 (`test_check_guild_membership_bot_not_fresh` expects False → must expect 503), 704-720; tests/unit/services/api/test_negative_authorization.py 114-164, 371, 468, 614 (stale → 404 expectations); tests/unit/services/api/test_database_dependencies.py (`get_db_with_user_guilds`); tests/unit/services/api/conftest.py 54 (patches `is_bot_fresh` for the permissions module only; the new gate in shared/database.py needs its own patch target) | `get_db_with_user_guilds` raises 503 when stale and does not call `get_user_guilds`; `_check_guild_membership` and `require_guild_by_id` raise 503 when stale; list-games loop re-raises 503; the shared helper uses the same detail string                              | Each gate fails closed with the right status and message                                        |
| Integration | tests/integration/conftest.py ~89 (fixture forces fresh, which stays the default)                                                                                                                                                                                                                                                                                                                                                                                                                                        | Stale (bot:last_seen absent or older than 120s) with real Redis + DB: GET existing game → 503, GET non-existent game → 503 (identical body), list games → 503, template GET → 503, list guilds → 503, unauthenticated → 401 (not 503); then fresh again → normal 200/404 | Real dependency ordering: auth before freshness before RLS/load, with no information disclosure |
| E2E         | none                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | None: the e2e environment runs a live bot that keeps the projection fresh; forcing staleness would need to stop the bot mid-suite and isn't worth the cost for a rare condition. Integration covers the HTTP contract                                                    | n/a                                                                                             |

## Implementation Guidance

- **Objectives**: any stale-projection request to a guild-scoped authenticated route returns 503 with the standard message; existing vs non-existent resources are indistinguishable; no endpoint silently returns empty results because of staleness.
- **Key Tasks**: shared stale-check helper; gate in `get_db_with_user_guilds`; convert `_check_guild_membership` and `require_guild_by_id` to raise; re-raise 503 in the list-games loop; update stale-path unit tests; add the integration matrix.
- **Dependencies**: `member_projection.is_bot_fresh`; Redis client from `cache_client.get_redis_client()` (already obtained in `get_db_with_user_guilds`).
- **Phase-isolation note**: steps 1-3 change expectations in existing unit tests (stale → 404 / False). Update those tests in the same phase as the behaviour change.
- **Success Criteria**: integration matrix passes; no test still expects 404 or an empty list for a stale projection; all unit, mypy and integration gates pass.

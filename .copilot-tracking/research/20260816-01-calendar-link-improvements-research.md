<!-- markdownlint-disable-file -->

# Task Research Notes: Discord embed calendar link improvements

## Research Executed

### File Analysis

- `services/bot/formatters/game_message.py`
  - `_prepare_description_and_urls` (L73-98) builds the single `calendar_url` from `config.frontend_url` + `/download-calendar/{game_id}` (L94-96). Returns it alongside the (currently pass-through, not actually truncated despite the name) `truncated_description`.
  - `_add_game_time_fields` (L125-181) renders the `Links` field (L171-175): `links_value = f"📅 [Add to Calendar]({calendar_url})"`, added as an inline field sharing a row with Host and Run Time (or blank spacers, L157-175). This is the only place a second "Add to Google Calendar" link would need to be appended (e.g. `links_value += f"\n📅 [Google Calendar]({google_url})"` or a similar second line within the same field, since Host/Run Time/Links already share one row and Discord fields don't nest).
  - `create_game_embed` (L320-414) already receives `game_title`, `description`, `scheduled_at`, `expected_duration_minutes`, `where` as parameters — every field needed to build a Google Calendar quick-add link is already present in this method; no new data threading from the database/bot event handler is required.
  - `format_game_announcement` (L477-600) is the only public entry point bots use; it forwards `description`, `scheduled_at`, `expected_duration_minutes`, `where`, `game_title`, `game_id` straight into `create_game_embed`. Confirmed single caller: `services/bot/events/handlers.py:1375` (`_create_game_announcement`, L1351-1399), which sources all of these directly off the `GameSession` ORM object (`game.description`, `game.scheduled_at`, `game.expected_duration_minutes`, `game.where`, `game.title`) — no additional query or join needed.
  - No existing `urllib.parse`/`quote`/`urlencode` usage anywhere under `services/bot/` or `services/api/` (only `services/api/config.py` imports `urlparse` for cookie-domain derivation) — a new Google-link builder will be the first URL-query-encoding code in the bot.

- `shared/models/game.py`
  - `title: Mapped[str] = mapped_column(String(200))` (L58) — bounded.
  - `description: Mapped[str | None] = mapped_column(Text, nullable=True)` (L59) — unbounded, nullable.
  - `where: Mapped[str | None] = mapped_column(Text, nullable=True)` (L62) — unbounded, nullable.
  - `expected_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)` (L81) — nullable.
  - Confirms all three optional fields (`description`, `where`, `expected_duration_minutes`) can legitimately be `None`/empty and the Google-link builder must handle each gracefully.

- `shared/utils/limits.py`
  - `DISCORD_EMBED_TOTAL_SAFE_LIMIT = 5900` (L32, of a hard `6000` L31) — whole-embed character budget already enforced by `_trim_embed_if_needed` (game_message.py L417-422), which only trims the _description_, not fields. Discord additionally hard-caps each field `value` at 1024 characters and `name` at 256 (API-level constant, not defined anywhere in this repo) — relevant because a second calendar link appended to `Links` adds to that field's 1024-char budget.
  - `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH = 100` (L38) — existing truncation constant, currently only used by `export.py`'s `generate_calendar_filename` (see below) for filename-safe truncation, not for embed text. Reusable as a sensible cap for how much of `description`/`where` to fold into the Google-link's `details`/`location` params, to bound URL length and the `Links` field's 1024-char budget.

- `services/api/auth/tokens.py` (read in full)
  - `store_user_tokens` (L89-135): the canonical "mint an opaque token, store payload in Redis with TTL" pattern to mirror. Generates `session_token = str(uuid.uuid4())` (L114), builds a `session_data` dict, computes `session_key = f"api:session:{session_token}"` (L131) via a literal f-string (not `CacheKeys`, even though `shared/cache/keys.py` has a `CacheKeys.session()` for the identical pattern — an existing minor inconsistency, not something to fix here but worth noting when choosing whether the new calendar-token key should go through `CacheKeys` or an inline f-string), then `await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)` (L132).
  - `get_user_tokens` (L138-173): reads via the metrics-instrumented `cache_get(key, CacheOperation.SESSION_LOOKUP)` helper (not raw `redis.get_json`), returns `None` on miss with a `logger.warning`.
  - `delete_user_tokens` (L212-224): `redis = await cache_client.get_redis_client()` then `await redis.delete(session_key)` — the single-use "delete on read" pattern would look identical: fetch via `RedisClient.get_json`/`cache_get`, then unconditionally `redis.delete(key)` regardless of hit/miss (or only on hit — see Open Questions).
  - No existing token type in this module encrypts non-OAuth payloads — `encrypt_token`/`decrypt_token` (L59-86) are Fernet-based and used only for OAuth access/refresh tokens. A calendar-mint token storing just `{"game_id": ...}` does not need encryption (low-sensitivity, per task background) and should **not** reuse `encrypt_token`.

- `shared/cache/client.py` (read in full)
  - `RedisClient.set_json(key, value, ttl=None)` (L314-336) / `get_json(key)` (L294-312) / `delete(key)` (L338-356) / `exists(key)` (L358-376) are the plain building blocks — JSON-serialize/deserialize over `SETEX`/`GET`/`DEL`. `set` uses `setex(key, ttl, value)` when `ttl` is truthy (L285-288), so `ttl=0` would silently NOT set an expiry — must pass a real positive second count.
  - `get_redis_client()` (L541-554) returns a lazily-connected singleton `RedisClient` — this is what `store_user_tokens` etc. call directly (not through `shared.database` or a service-locator).
  - No per-namespace TTL override mechanism beyond passing `ttl=` explicitly at each call site (`CacheTTL` in `shared/cache/ttl.py` is just a plain class of `int` constants, no dynamic/env-driven values).

- `shared/cache/ttl.py` (read in full)
  - `CacheTTL` class (L28-46) has one field per cache "kind" (`SESSION=86400`, `GAME_DETAILS=60`, `DISPLAY_NAME=300`, etc.) — all hardcoded ints in seconds, no env-var overrides. A new `CacheTTL.CALENDAR_EXPORT_TOKEN = 300` (5 minutes) constant is the established way to add a new TTL; no config-file/env-var plumbing needed or expected.

- `shared/cache/operations.py` (read in full)
  - `CacheOperation` `StrEnum` (L53-68) — symbolic names for every cache _read_ site, used purely as an OTel metric label in `cache_get` (L71-91: records `cache.hits`/`cache.misses` counters and a duration histogram per `operation` label). A new calendar-token lookup should add a new member here (e.g. `CALENDAR_EXPORT_TOKEN_LOOKUP`) and go through `cache_get(key, CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP)` rather than calling `redis.get_json` directly, to stay consistent with `get_user_tokens`'s pattern and keep the hit/miss metric coverage complete.
  - `read_projection_key` (L94-123) is unrelated (projection-generation-rotation retry logic) — not applicable to a single flat token key.

- `shared/cache/keys.py` (read in full)
  - `CacheKeys` is a plain `@staticmethod` collection of key-format functions, one per namespace (`session`, `oauth_state`, `game_details`, `channel_config`, etc.), all simple f-strings like `f"api:session:{session_id}"` (L39-41) or `f"api:oauth:{state}"` (L54-56). `tokens.py` itself does _not_ use `CacheKeys.session()` even though it exists — it inlines the same f-string. A new `CacheKeys.calendar_export_token(token: str) -> str` staticmethod (e.g. `f"api:calendar_export:{token}"`) would match the class's existing convention even though `tokens.py`'s own session key doesn't currently route through it.

- `services/api/routes/public.py` (read in full)
  - Router: `APIRouter(prefix="/api/v1/public/images", tags=["public"])` (L40) — a new calendar-export public route would need its own prefix, e.g. `/api/v1/public/calendar` (or extend this file with a differently-prefixed router — FastAPI routers support one prefix per `APIRouter` instance, so either a second `APIRouter` in this file or a new sibling module, e.g. `services/api/routes/public_calendar.py`, both are viable; existing convention is one file per resource type, e.g. `export.py`, `public.py` for images).
  - Rate limiting: module-level `limiter = Limiter(key_func=get_remote_address)` (L43) plus `_rate_limits = get_rate_limits()` (L44, from `services.api.config.get_rate_limits()` — the same _global_ two-tier rate limit list used everywhere, no per-route override) and a `_apply_rate_limits` decorator (L52-56) that stacks all configured limits via `limiter.limit(rate_limit)` in reverse order. `get_limiter(request)` (L47-49) is defined but unused in this file (dead helper — `_apply_rate_limits` reads the module-level `limiter` closure directly, not `request.app.state.limiter`).
  - No authentication dependency anywhere in this file — confirms this is the correct template for a new unauthenticated route.
  - Both `get_image`/`head_image` fetch straight from `Depends(get_db)` (a plain, non-guild-scoped session — `shared.database.get_db`, not `get_db_with_user_guilds()`), consistent with "no RLS policies" on the underlying table (image comment L73). A calendar-token lookup route would use Redis, not the DB, for its primary lookup, but would still need `Depends(get_db)` to re-fetch the `GameSession` and call `CalendarExportService.export_game` (mirroring `export.py`'s DB flow) once the token resolves to a `game_id`.
  - Error handling shape: explicit `try/except HTTPException: raise` / `except ValueError: raise HTTPException(404, ...) from None` / `except Exception: logger.exception(...); raise` (L86-118) — re-raises unexpected exceptions after logging rather than swallowing them.
  - `image_id_with_ext.split(".")[0]` (L87, L147) — pattern for accepting an optional file-extension suffix on a path parameter; not obviously needed for an `.ics` token route (calendar apps identify by `Content-Type`, not URL extension) but worth considering for direct-open compatibility in some mail/calendar clients that sniff extensions.

- `services/api/routes/export.py` (read in full)
  - `export_game` (L92-162): the existing **authenticated** export flow. Fetches `GameSession` with `selectinload(guild, host, participants→user)` (L106-114), calls `permissions_deps.can_export_game(...)` (L124-133) — note: the route pre-checks with a `selectinload`'d game (loading `guild`/`host`/`participants`) _then_ passes the already-computed boolean `can_export` into `CalendarExportService.export_game(game_id, user.user.id, user.user.discord_id, can_export)` (L138-140), which re-queries the game a second time with a different, wider `selectinload` set (including `channel→guild`, for the `.ics` `LOCATION` field) inside `calendar_export.py`. This double-fetch (once in the route for the permission check, once in the service for full data) is the existing pattern to replicate for "mint token" (permission check) vs. "generate ics" (full data) being two separate code paths under the new design.
  - Response building (L155-162): `Response(content=ical_data, media_type="text/calendar", headers={"Content-Disposition": f"attachment; filename={filename}", "Cache-Control": "no-cache"})` — the **only** thing the new public route changes structurally is `attachment` → `inline` (still needs `filename=` for clients that use it as a display hint even when inline) and dropping the `no-cache` (or keeping it — a single-use token means the content is only ever fetched once successfully, so caching is moot; but see Open Questions about single-use vs multi-fetch during the TTL window).
  - `generate_calendar_filename` (L54-84) — pure function, directly reusable by the new public route for the `Content-Disposition` filename; already unit-tested in `tests/unit/services/api/routes/test_export.py` (L331-372) including special-character/unicode/emoji/length-truncation cases, all built on `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH`.

- `services/api/services/calendar_export.py` (read in full)
  - `CalendarExportService.__init__(self, db)` (L49-53) / `export_game(self, game_id, _user_id, _discord_id, can_export)` (L55-104): re-queries the game with `selectinload(guild, channel→guild, host, participants→user)` (L78-87), raises `ValueError` if not found (L92-94) or `PermissionError` if `not can_export` (L96-102) — **`can_export` is trusted as pre-computed by the caller**, the service does not re-derive permissions itself. This means a public route that already validated `can_export_game` at _mint_ time and stored only `game_id` in Redis can safely call `CalendarExportService(db).export_game(game_id, "", "", can_export=True)` at _serve_ time without re-authenticating, since the permission check happened once, at mint time, before the token existed. `_user_id`/`_discord_id` params are unused (prefixed `_`, only there for the docstring / possible future re-derivation) — passing empty strings for a public unauthenticated caller is safe and matches existing conventions for intentionally-unused params.
  - `_generate_calendar` (L106-129) / `_create_event` (L141-218): builds one `.ics` `VEVENT` per game — `dtstart`/`dtend` (duration default 120 min if `expected_duration_minutes` is `None`, L165-167 — **same default-duration behavior the new Google-link builder should mirror** for consistency between the two calendar surfaces), `description` assembled from Host/Location/blank-line/`game.description`/`signup_instructions` (L169-189), `location` from Discord guild+channel names (L191-195, requires a live Discord API/cache lookup via `fetch_guild_name_safe`/`fetch_channel_name_safe` — **not** available to the bot-side Google-link builder without extra round trips, so the Google link's `location` param should use the raw `game.where` field instead, which is exactly what's already passed into `create_game_embed`).
  - `_resolve_host_display` (L131-139): resolves host nickname via `member_projection.get_member(...)`, an additional Redis-projection read — again, plumbing the _bot_ already has cheaper access to via `host_display_name` (already computed in `handlers.py` L1369-1371 and passed into `create_game_embed`) — reinforces that the Google-link builder in `game_message.py` should build `details`/`location` purely from parameters already flowing into `create_game_embed`, not attempt to replicate `calendar_export.py`'s DB/Discord-API-backed enrichment.

- `services/api/dependencies/permissions.py`
  - `can_export_game(game_host_id, game_participants, guild_id, user_id, discord_id, role_service, db, current_user=None)` (L677-727): calls `verify_guild_membership(guild_id, current_user, db)` first when `current_user` is provided (raises 404 if not a guild member, L714-716), then returns `True` if `game_host_id == user_id` (host, L718-720), else `True` if the caller is a listed, resolved participant (`p.user_id == discord_id and p.user is not None`, L722-724), else defers to `role_service.check_bot_manager_permission(discord_id, guild_id, db)` (L726-727, covers bot-manager-role and Discord-administrator-permission checks internally). This exact call — unmodified — is what the new "mint calendar token" route must perform before writing `game_id` to Redis; it needs the same `selectinload`'d `GameSession` (`guild`, `host`, `participants→user`) as `export.py`'s route currently loads, and the same `role_service: RoleVerificationService = Depends(get_role_service)`.

- `frontend/src/pages/DownloadCalendar.tsx` (read in full)
  - Current flow: on mount (guarded by `hasDownloaded` ref against React StrictMode double-invoke, L34, L77-86), calls `downloadCalendar()` (L36-75): `fetch('/api/v1/export/game/${gameId}', { credentials: 'include' })` (L39-41) → on non-OK, sets a status-coded error message (L43-51) → on OK, reads `Content-Disposition` for filename (L54-56), converts to `Blob`, creates an `<a download>` and clicks it programmatically (L58-66), then `setTimeout(() => navigate('/my-games'), 1000ms)` (L68). Renders a spinner while `authLoading || downloading` (L88-106) and an MUI `Alert` on error (L108-124), otherwise renders `null` (L126).
  - **No existing "mint token then navigate" pattern anywhere in the frontend** — confirmed via `grep -rn "window.location" frontend/src` (only `api/client.ts`'s 401-redirect-to-login and `LoginPage.tsx`'s OAuth-authorize redirect use `window.location.href =`) and `grep -rn "credentials: 'include'"` (only `AuthCallback.tsx` and `DownloadCalendar.tsx` — no other raw `fetch` + real-navigation combo exists). The new flow (POST to mint → `window.location.href = publicUrl`) will be the first of its kind in this codebase and should follow the `window.location.href = '...'` idiom already used in `api/client.ts`/`LoginPage.tsx` rather than `navigate()` from `react-router` (a SPA route change wouldn't trigger a real browser navigation/OS hand-off to the public backend URL, which is the entire point of the fix).
  - `useAuth()` (`frontend/src/hooks/useAuth.ts`, L23-30) is a 9-line context-consumer wrapper around `AuthContext` — `user`/`loading` are the only fields `DownloadCalendar.tsx` uses; no changes needed to the hook itself.
  - `apiClient` (`frontend/src/api/client.ts`, read in full) is the project's axios wrapper (`withCredentials: true`, automatic 401→refresh→retry→redirect-to-login interceptor, L63-101) used elsewhere (e.g. `ExportButton.tsx`, `GameDetails.tsx` use raw `axios.get(..., { withCredentials: true })` rather than `apiClient`, so there's some inconsistency already in whether components use the shared `apiClient` instance vs. raw `axios`). Minting a token is a natural fit for `apiClient.post('/api/v1/export/game/:gameId/mint-token')` (or similar), returning `{ token: string }`, then `window.location.href = `${backendBaseUrl}/api/v1/public/calendar/${token}.ics`` (or whatever path the new public route uses) — needs the backend's public base URL, which the frontend does not currently read from `window.__RUNTIME_CONFIG__` anywhere except inside `client.ts`'s own `API_BASE_URL` (L35-36) — that constant is not exported, so the new mint-then-navigate code will need to import `API_BASE_URL` (exporting it) or reconstruct the base URL, or (simpler) have the new public endpoint be same-origin-relative if frontend and backend share an origin/proxy in production the way `/api/v1/export/game/...` already works as a relative path today. **Open question**: is `/api/v1/public/...` always same-origin with the frontend in every deployment (local dev, staging, prod), or does it need an absolute `BACKEND_URL`? `frontend/src/pages/GameDetails.tsx` L438/L457 already uses bare relative `src={`/api/v1/public/images/${game.thumbnail_id}`}` in `<img>` tags, which only works if frontend and backend are same-origin or proxied together — this is the existing precedent to follow (relative URL), avoiding the need to plumb a new absolute backend URL into the frontend at all.
  - Three separate frontend call sites hit `/api/v1/export/game/{gameId}` today, not just this page: `DownloadCalendar.tsx` (L39, used by the Discord-embed link), `frontend/src/components/ExportButton.tsx` (L38, an in-app button using `axios.get(..., { responseType: 'blob' })` + Blob-download), and `frontend/src/pages/GameDetails.tsx` (`handleDownloadCalendar`, L205, identical Blob-download pattern). **The task as scoped only asks for the Discord-embed-linked page (`DownloadCalendar.tsx`) to change** — `ExportButton.tsx` and `GameDetails.tsx`'s in-app buttons are separate, already-in-app-browser-context download buttons where the mobile-OS-hand-off problem doesn't apply the same way (user is already inside the web app, clicking a button, not tapping a link from Discord on their phone). Flagged as an explicit **open question** for the planner: leave those two untouched, or migrate them too for consistency?

- `frontend/src/pages/__tests__/DownloadCalendar.test.tsx` (read in full)
  - 8 tests covering: loading-state render, successful-download-triggers-`createObjectURL`, missing-`Content-Disposition`-fallback-filename, 403→permission-denied message, 404→not-found message, other-status→generic error, fetch-throws→generic error + `console.error` call verification, and error-alert-close→`navigate('/my-games')`. All mock `globalThis.fetch` directly (not `apiClient`/axios) and assert on rendered text (`screen.getByText`) plus `URL.createObjectURL`/`revokeObjectURL` calls. A rewritten test suite for the mint-then-navigate flow would need to mock a POST-mint call (whatever client is used) and assert `window.location.href` (or `assign`) was set to the expected public-token URL, plus keep the existing 403/404/error-message tests (which map naturally onto the _mint_ call's failure modes, not the final navigation, since navigation itself has no observable failure from the SPA's perspective).

### Code Search Results

- `grep -rn "download-calendar\|api/v1/export\|api/v1/public" frontend/src` (excluding tests)
  - `App.tsx:53` — route registration `<Route path="/download-calendar/:gameId" element={<DownloadCalendar />} />`.
  - `DownloadCalendar.tsx:39`, `ExportButton.tsx:38`, `GameDetails.tsx:205` — the three `/api/v1/export/game/{gameId}` consumers noted above.
  - `GameDetails.tsx:438,457` — `/api/v1/public/images/{id}` used as bare relative `<img src>`, confirming the public-images route is consumed same-origin/relative today, the precedent for how a new public calendar route would be linked to from the frontend.

- `grep -rn "CacheTTL\." shared/ services/` (excluded tests/pyc)
  - Every `CacheTTL` member (`SESSION`, `GUILD_CONFIG`, `CHANNEL_CONFIG`, `GAME_DETAILS`, `USER_GUILDS`, `DISPLAY_NAME`, `USER_ROLES`, `APP_INFO`, the `DISCORD_*` no-expiry ones) is referenced from exactly one call site each across `services/api/auth/tokens.py`, `shared/cache/*`, and related service modules — confirms the class is a flat, append-only list of one-constant-per-cache-kind, safe to extend with a new `CALENDAR_EXPORT_TOKEN` member without touching any other constant.

- `grep -rn "include_router\|app.state.limiter" services/api/app.py`
  - `app.state.limiter = limiter` (L137) + `app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)` (L138) + `app.add_middleware(SlowAPIMiddleware)` (L139) are configured once, globally, before any router is included (L144-152) — `export.router` and `public.router` are both already registered (L149, L151); a new route added to `public.py` (or a new sibling module) needs no additional app-level wiring beyond `app.include_router(...)` if a new module is created.

- `grep -rn "get_rate_limits\|RATE_LIMIT_" services/api/config.py`
  - `get_rate_limits()` (L85-108) reads `RATE_LIMIT_COUNT` (default `2`) then, per rule `N`, `RATE_LIMIT_{N}_COUNT`/`RATE_LIMIT_{N}_TIME` (defaults: rule 1 → `60/60seconds`, rule 2 → `100/300seconds`) — this is a **single global rate-limit tier** applied uniformly to every `@_apply_rate_limits`-decorated route in `public.py` (images) and would apply identically to a new calendar-token-serving route with zero code changes if it reuses `_apply_rate_limits`. There is no existing per-route-tier override mechanism in this codebase — any "should the new route have a stricter/looser tier" decision would require new config plumbing (new env vars + a new `get_rate_limits()`-like function, or a second `Limiter` instance), which does not exist today.

- `grep -rn "frontend_url\|backend_url" services/bot/config.py services/api/config.py`
  - Bot: `frontend_url` (`services/bot/config.py` L76-79, default `http://localhost:5173`) is what constructs today's single `calendar_url` in `game_message.py` L96; `backend_url` (L81-84) is what constructs the public-image URLs (`game_message.py` L543,L547) — i.e., **the bot already has both URLs available** and could construct a Google-Calendar link (frontend-independent, no backend call at all) or reference the new public `.ics` route (`backend_url`-based) with zero new config.
  - API: `frontend_url`/`backend_url` (`services/api/config.py` L141-142) — used for cookie-domain derivation (`_get_cookie_domain`, L33-82) and nowhere else in this file; no rate-limit-tier or calendar-specific settings exist yet.

- `grep -rn "reminder_minutes\|expected_duration_minutes" services/bot/formatters/game_message.py services/bot/events/handlers.py`
  - Confirms `expected_duration_minutes` is already an optional int flowing end-to-end from `GameSession.expected_duration_minutes` → `handlers.py` L1388 → `format_game_announcement` → `create_game_embed` → (currently) only used for the human-readable "Run Time" field (`format_duration`, `_add_game_time_fields` L165-169) — reusable unchanged as the Google-link's duration source.

### External Research

- Source: [InteractionDesignFoundation/add-event-to-calendar-docs — google.md](https://github.com/InteractionDesignFoundation/add-event-to-calendar-docs/blob/main/services/google.md)
  - Base URL: `https://calendar.google.com/calendar/render?action=TEMPLATE` (an alternate `/calendar/r/eventedit` form exists and doesn't need `action=TEMPLATE`, but `render?action=TEMPLATE` is the documented, widely-used quick-add form and matches the URL given in the task background).
  - Required-in-practice params: `text` (event title), `dates` (see below).
  - Optional params relevant to this project: `details` (description), `location` (Google-Maps-style address string, but any free text is accepted and just won't geocode), `ctz` (IANA timezone name, e.g. `America/New_York` — only needed if the `dates` timestamps are _not_ UTC/`Z`-suffixed; since this project stores everything as naive-UTC-then-`Z`-suffixed (see `calendar_export.py` L161 `game.scheduled_at.replace(tzinfo=UTC)`), `ctz` can be omitted entirely and Google will interpret the `Z`-suffixed UTC timestamps correctly for any viewer's local timezone), `recur` (RFC-5545 `RRULE:` string — not applicable, this project has no recurring-Google-event use case for the embed link; `clone_game_for_recurrence` creates independent `GameSession` rows, each gets its own embed/link).
  - **Date format** (the critical piece per the task): `dates=<start>/<end>` where each timestamp is `YYYYMMDDTHHmmSSZ` for timed events (e.g. `20201231T193000Z/20201231T223000Z`), or `YYYYMMDD/YYYYMMDD` (no `T`/time, next-day-exclusive end) for all-day events. Python's `datetime.strftime("%Y%m%dT%H%M%SZ")` on a UTC-aware `datetime` produces exactly this format (no `strftime` `%Z`/library dependency needed beyond stdlib `datetime`).
  - Both start **and** end are required for timed events — Google's quick-add UI does not infer a default duration from a missing end timestamp; if `expected_duration_minutes` is `None`, the link builder must synthesize an end time itself (mirroring `calendar_export.py` L165-167's `duration_minutes = game.expected_duration_minutes or 120` default) rather than omitting `dates`' second half or the link will not open correctly with the event pre-filled.
  - The doc's "when dates omitted entirely" case is unspecified/undocumented upstream — not a scenario this project should hit anyway, since `scheduled_at` is a required non-nullable field on `GameSession` (unlike `description`/`where`/`expected_duration_minutes`).

- Source: [Formsite — Google Calendar: Create Links to Schedule Events](https://www.formsite.com/blog/google-calendar-links/) and [maxkohler.com — Add-to-calendar links](https://www.maxkohler.com/posts/calendar-links/) (cross-referenced during search, same param set/date format as above; used to corroborate rather than as a primary citation for anything not already covered by the IDF doc above).

- Encoding rules (general web-platform knowledge, applicable regardless of source): every param value must be percent-encoded as a URL query-string component. Python's `urllib.parse.urlencode({...})` (stdlib, already used for `urlparse` elsewhere in this codebase, see `services/api/config.py:30`) percent-encodes spaces as `+` by default (`quote_via=quote_plus`) which Google's endpoint accepts equally to `%20`; no special-casing needed for the newlines that could appear in a folded multi-line `details` string (`urlencode` percent-encodes `\n` as `%0A` automatically). No manual `quote()`/`quote_plus()` calls are needed — a single `urlencode(...)` call over a params dict (omitting keys whose value is falsy/`None`, mirroring how `event.add(...)` is conditionally skipped in `calendar_export.py`'s `_create_event`, e.g. `if game.where: description_parts.append(...)`) is sufficient and idiomatic for this codebase.

### Project Conventions

- Standards referenced: `.github/instructions/api-authorization.instructions.md` — governs the new "mint calendar token" route (must use `can_export_game` unmodified, per the "no inline authorization code" and "404 for non-members / 403 for members-without-permission" rules) and confirms `services/api/routes/public.py` (the new public `.ics`-serving route's template) is explicitly named in that instruction file's own worked example (`can_export_game` docstring example at L188-203 shows a plain `/export/game/{game_id}` route, not a token-mint variant — the mint route is new territory but must still follow the same three-tier model up through the permission check).
- Standards referenced: `.github/instructions/fastapi-transaction-patterns.instructions.md` — governs both the "mint" route (a normal `Depends(get_db)`/`Depends(get_current_user)` read-only permission check, no DB writes, so no transaction-boundary concerns beyond the existing pattern) and confirms that the new public `.ics`-serving route (looking up a Redis token then calling `CalendarExportService(db).export_game(...)`, which itself performs no writes) also has no commit/flush obligations — it's a pure-read GET, matching `services/api/routes/public.py`'s existing `get_image`/`head_image` (no `db.commit()` calls anywhere in that file).
- Standards referenced: `.github/instructions/python.instructions.md` — full type hints (Python 3.13+), Ruff's `G004` (lazy `%s` logging, not f-strings — relevant since `services/api/auth/tokens.py` already follows this throughout and any new token-helper module must too), `ANN` (complete annotations), `S105/S106` (no hardcoded secrets — irrelevant here, tokens are `uuid4()`-random, not secrets), and PEP257 docstrings for any new public function (`mint_calendar_export_token`, `get_calendar_export_token`, `delete_calendar_export_token`, or similar).
- Standards referenced: `.github/instructions/test-driven-development.instructions.md` — since both improvements are **new** production code paths (a new Google-link builder function, a new token-mint helper module, a new public FastAPI route, new frontend mint-then-navigate logic), full RED→GREEN→REFACTOR with `NotImplementedError` stubs and `@pytest.mark.xfail(strict=True)` (Python) / `test.failing` (TypeScript/Vitest) applies to all of it — none of this qualifies for the "writing tests for already-correct code" exception in that instruction file.
- Standards referenced: `.github/instructions/unit-tests.instructions.md` — new tests must assert concrete outcomes (e.g., the exact constructed Google-Calendar URL string / exact percent-encoded query params, not just "a link was added"; `mock_redis.set_json.assert_called_once_with(expected_key, {"game_id": ...}, ttl=300)` style verifications, not just `assert_called_once()`).
- Standards referenced: `.github/instructions/integration-tests.instructions.md` — any new integration test for the public `.ics` route belongs under `tests/integration/services/api/routes/` (mirroring `test_public_images.py`/`test_public_images_rate_limit.py`, the closest existing precedent for an unauthenticated, rate-limited public route) and must run via `scripts/run-integration-tests.sh` with output piped through `tee`, not invoked directly with bare `pytest`.

## Key Discoveries

### Project Structure

Two independent, additive changes to `services/bot/formatters/game_message.py`'s embed-building code path plus (for improvement 2) a new Redis-token helper module, a new public FastAPI route, and a rewritten frontend page — none of which require new database columns, new `GameSession` fields, or new data threaded from `services/bot/events/handlers.py` into the formatter (all needed game data is already parameters of `create_game_embed`/`format_game_announcement`).

### Implementation Patterns

**Improvement 1 — Google Calendar quick-add link (self-contained, no backend involvement):**

Build entirely inside `services/bot/formatters/game_message.py` (or a new small helper in `services/bot/utils/discord_format.py`, alongside `format_duration`/`format_discord_timestamp`) from data already passed into `create_game_embed`:

```python
from urllib.parse import urlencode

_GOOGLE_CALENDAR_BASE_URL = "https://calendar.google.com/calendar/render"
_DEFAULT_EVENT_DURATION_MINUTES = 120  # matches calendar_export.py's default

def _build_google_calendar_url(
    game_title: str,
    description: str | None,
    scheduled_at: datetime,
    expected_duration_minutes: int | None,
    where: str | None,
) -> str:
    start = scheduled_at.strftime("%Y%m%dT%H%M%SZ")
    duration = expected_duration_minutes or _DEFAULT_EVENT_DURATION_MINUTES
    end = (scheduled_at + timedelta(minutes=duration)).strftime("%Y%m%dT%H%M%SZ")

    params = {"action": "TEMPLATE", "text": game_title, "dates": f"{start}/{end}"}
    if description:
        params["details"] = description[:GAME_LIST_DESCRIPTION_SNIPPET_LENGTH]
    if where:
        params["location"] = where

    return f"{_GOOGLE_CALENDAR_BASE_URL}?{urlencode(params)}"
```

Note `scheduled_at` must be UTC-aware (or treated as naive-UTC, matching `calendar_export.py` L161's `.replace(tzinfo=UTC)` convention) before `strftime` — the bot's `scheduled_at` values flow from the same `GameSession.scheduled_at` naive-UTC column, so the formatter should apply the same "treat as UTC" assumption `calendar_export.py` already documents.

Wire into `_add_game_time_fields`'s `Links` field (game_message.py L171-175) as a second line:

```python
if calendar_url:
    links_value = f"📅 [Add to Calendar]({calendar_url})"
    if google_calendar_url:
        links_value += f"\n📅 [Google Calendar]({google_calendar_url})"
    embed.add_field(name="Links", value=links_value, inline=True)
```

**Improvement 2 — public `.ics` route via short-lived opaque token:**

1. New Redis-backed helper **in `services/api/auth/tokens.py`** (decided — see Decisions below), mirroring `store_user_tokens`/`get_user_tokens` exactly but storing only `{"game_id": game_id}` (no encryption needed — low sensitivity, and no `delete_user_tokens` counterpart since lookup is TTL-only, not delete-on-read), with a new `CacheTTL.CALENDAR_EXPORT_TOKEN = 300` (5 minutes) and a new `CacheKeys.calendar_export_token(token)` key-format function and a new `CacheOperation.CALENDAR_EXPORT_TOKEN_LOOKUP` metric label.
2. New route on the existing authenticated `services/api/routes/export.py` router (not `public.py` — this one _is_ authenticated) e.g. `POST /api/v1/export/game/{game_id}/token`, doing exactly what `export_game` does today up through the `can_export_game(...)` call (L92-133, unchanged), then instead of calling `CalendarExportService`, mints a token via the new helper and returns `{"token": token}`.
3. New public route **in `services/api/routes/public.py`** (decided — see Decisions below), as a second `APIRouter(prefix="/api/v1/public/calendar", tags=["public"])` instance in the same file (the existing `router`'s prefix is hardcoded to `/api/v1/public/images`, so it can't be reused directly — a second router instance in the same module, registered separately in `app.py`, is the mechanical requirement), e.g. `GET /api/v1/public/calendar/{token}.ics`, modeled on `get_image` (L59-118): look up the token via the new helper, 404 if missing/expired (TTL-only expiry, no explicit delete), then `select(GameSession)...` + `CalendarExportService(db).export_game(game_id, "", "", can_export=True)` (permission already validated at mint time) + `generate_calendar_filename` (imported from `export.py`) + `Response(..., media_type="text/calendar", headers={"Content-Disposition": f'inline; filename="{filename}"'})` (filename kept — decided, see Decisions below) — same `_apply_rate_limits` decorator as the images route, reusing the existing global rate-limit tier (decided — no new tier).
4. Frontend `DownloadCalendar.tsx` rewritten: on mount, `POST` to the new mint endpoint (via `apiClient`, which already carries the session cookie), then `window.location.href = `/api/v1/public/calendar/${token}.ics`` (relative URL, matching the existing `/api/v1/public/images/...` precedent) — a real browser navigation, not `fetch`, so the browser/OS can hand the `text/calendar` response to a calendar app. Error states (403/404 from the mint call) render the same MUI `Alert` UI already present.
5. **`ExportButton.tsx` and `GameDetails.tsx`'s in-app "Export to Calendar" buttons also migrate** to the same mint-then-navigate flow, replacing their `axios.get(..., { responseType: 'blob' })` + Blob-download pattern (decided — see Decisions below): verified that no desktop browser regresses (Chrome/Edge/Firefox have no built-in `text/calendar` renderer, so `inline` still falls back to a normal download with the `filename=` hint intact — functionally identical to today's Blob download; macOS Safari can additionally hand off straight to Calendar.app), and mobile-web users of these buttons gain the same calendar-app hand-off as the Discord-embed link.

### Complete Examples

Current single-link construction, `services/bot/formatters/game_message.py` L88-98 (verbatim, current):

```python
calendar_url = None
if game_id:
    config = get_config()
    calendar_url = f"{config.frontend_url}/download-calendar/{game_id}"

return truncated_description, calendar_url, thumbnail_url, image_url
```

Current `Links` field rendering, `services/bot/formatters/game_message.py` L171-175 (verbatim, current):

```python
if calendar_url:
    links_value = f"📅 [Add to Calendar]({calendar_url})"
    embed.add_field(name="Links", value=links_value, inline=True)
else:
    embed.add_field(name="​", value="​", inline=True)
```

Existing Redis-token mint/read/delete pattern to mirror, `services/api/auth/tokens.py` L89-135 and L212-224 (verbatim, current — already quoted in full in File Analysis above; reproduced here as the direct template):

```python
async def store_user_tokens(
    user_id: str,
    access_token: str,
    refresh_token: str,
    expires_in: int,
    can_be_maintainer: bool = False,
    username: str = "",
    avatar: str | None = None,
) -> str:
    redis = await cache_client.get_redis_client()
    session_token = str(uuid.uuid4())
    ...
    session_key = f"api:session:{session_token}"
    await redis.set_json(session_key, session_data, ttl=cache_ttl.CacheTTL.SESSION)
    logger.info("Stored tokens for user %s", user_id)
    return session_token


async def delete_user_tokens(session_token: str) -> None:
    redis = await cache_client.get_redis_client()
    session_key = f"api:session:{session_token}"
    await redis.delete(session_key)
    logger.info("Deleted session %s", session_token)
```

Existing public, rate-limited, unauthenticated route template, `services/api/routes/public.py` L59-119 (verbatim, current — already quoted in full in File Analysis above).

Existing authenticated export route + `attachment` response headers to change to `inline`, `services/api/routes/export.py` L92-162 (verbatim, current — already quoted in full in File Analysis above).

### API and Schema Documentation

Google Calendar quick-add TEMPLATE URL (from External Research above):

```
https://calendar.google.com/calendar/render?action=TEMPLATE
  &text=<url-encoded event title>
  &dates=<YYYYMMDDTHHmmSSZ>/<YYYYMMDDTHHmmSSZ>   (timed)
       | <YYYYMMDD>/<YYYYMMDD>                    (all-day, end exclusive)
  &details=<url-encoded description, optional>
  &location=<url-encoded free-text location, optional>
  &ctz=<IANA timezone, optional — omit when dates are Z-suffixed UTC>
```

No official Google API-reference page exists for this undocumented-but-stable quick-add URL scheme (Google does not publish it as part of the Calendar API docs); the IDF community doc cited above is the standard reference used across the ecosystem (also cross-referenced by 3 independent blog posts found in the same search, all describing an identical param set).

### Configuration Examples

No new environment variables or config-file settings are strictly required:

- Bot: `services/bot/config.py`'s existing `frontend_url`/`backend_url` fields are sufficient — the Google-Calendar link needs neither (it's a static `calendar.google.com` URL built entirely from game data), and the `.ics` link change (improvement 2) doesn't touch the bot's `calendar_url` construction at all (the bot still just links to `{frontend_url}/download-calendar/{game_id}`, which is now a page that mints-then-redirects instead of fetch-then-Blob).
- API: `services/api/config.py` needs no new fields for the TTL (goes in `shared/cache/ttl.py`'s `CacheTTL` class as a plain hardcoded constant, matching every existing entry) or for the rate-limit tier (reuses the existing global `get_rate_limits()`/`_apply_rate_limits` — see Open Questions below for whether a dedicated tier is wanted).

Proposed new constant, `shared/cache/ttl.py`:

```python
class CacheTTL:
    ...
    CALENDAR_EXPORT_TOKEN: int = 300  # 5 minutes - TTL-only expiry, no delete-on-read (see Decisions)
```

### Technical Requirements

- The Google-Calendar link must be built purely from parameters already present in `create_game_embed`/`format_game_announcement` — no new query, no new field threaded from `services/bot/events/handlers.py`.
- `scheduled_at` must be treated as UTC (matching `calendar_export.py`'s existing `.replace(tzinfo=UTC)` convention) before formatting into `dates=`.
- Missing `expected_duration_minutes` must fall back to a default (120 minutes, matching `calendar_export.py` L165-167) rather than omitting the end timestamp, since Google's quick-add requires both halves of `dates=` for a timed event.
- `details`/`location` params must be explicitly length-guarded in the Google-link builder itself, and it is **not** sufficient to rely on `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` (100) alone: `title` is `String(200)` (double that), and `where` is an **unbounded** `Text` column ([shared/models/game.py:62](../../shared/models/game.py#L62)) — nothing today truncates it before rendering (it's dropped verbatim into the "Where" embed field at `game_message.py` L178). A long, untruncated `where` fed straight into the Google link's `location=` param, once percent-encoded (spaces → `+`/`%20`, unicode → multi-byte `%XX` sequences), can by itself approach or exceed Discord's 1024-char field cap — independent of `details`'s length. The builder needs its own explicit caps on `title` and `where` (not just `description`), sized conservatively to account for percent-encoding expansion, to keep the two-link `Links` field value safely under 1024 chars.
- The public `.ics`-serving route must NOT re-run `can_export_game` (permission was already checked once, at mint time, by the authenticated mint endpoint) — it only needs to resolve token→`game_id` and 404 on miss/expiry, exactly mirroring how `services/api/services/calendar_export.py::export_game` already trusts a pre-computed `can_export` boolean from its caller.
- Token storage needs no encryption (`{"game_id": ...}` is low-sensitivity, unlike OAuth tokens) — should NOT reuse `encrypt_token`/`decrypt_token` from `tokens.py`.
- Token lookup is **TTL-only expiry, no delete-on-read** (decided — see Decisions below): the mint-then-navigate flow never renders the token URL as a user-tappable link (it's set via `window.location.href` from a page the user never manually re-visits), so the only realistic re-fetch scenario is an ordinary network retry, which an unconditional delete-on-read would break with a confusing 404 for no real security benefit given the token is already low-sensitivity and short-TTL.
- New Redis key namespace, TTL constant, and `CacheOperation` label should be added following the exact existing conventions in `shared/cache/keys.py`, `shared/cache/ttl.py`, and `shared/cache/operations.py` respectively (one static method / one class constant / one enum member each).

## Recommended Approach

**Improvement 1 (Google Calendar link):** Add a small pure-function URL builder (either a new private static method on `GameMessageFormatter` in `game_message.py`, colocated with `_prepare_description_and_urls`, or a new function in `services/bot/utils/discord_format.py` alongside the other formatting helpers) that takes `game_title`, `description`, `scheduled_at`, `expected_duration_minutes`, `where` and returns a fully-encoded `https://calendar.google.com/calendar/render?action=TEMPLATE&...` URL using `urllib.parse.urlencode`. Wire its result into `_add_game_time_fields`'s existing `Links` field as a second markdown-link line. No new config, no new DB fields, no new data threading — purely additive to the existing formatter.

**Improvement 2 (public `.ics` hand-off via short-lived token):** Follow the task's already-agreed design exactly, using `services/api/auth/tokens.py`'s `store_user_tokens`/`get_user_tokens` pair as the direct implementation template (same `RedisClient`/`cache_get`/`CacheTTL`/`CacheKeys` building blocks, unencrypted payload, colocated in the same module, **TTL-only expiry with no delete-on-read**), `services/api/routes/export.py`'s existing `can_export_game`-based permission check reused unmodified at a new authenticated "mint" endpoint, and `services/api/routes/public.py`'s `get_image`/`head_image` as the direct template for a new unauthenticated, rate-limited, token-resolving `.ics`-serving route added to that same file as a second `APIRouter` instance (same `_apply_rate_limits` decorator reusing the existing global tier, same try/except shape, same `Depends(get_db)` for the post-token-resolution `GameSession`/`CalendarExportService` fetch, `Content-Disposition: inline` keeping `filename=`). Frontend `DownloadCalendar.tsx` changes from fetch+Blob to POST-mint+`window.location.href` real navigation, matching the `window.location.href = ...` idiom already used in `api/client.ts`/`LoginPage.tsx` for other real-navigation needs, and using a same-origin-relative public URL matching the existing `/api/v1/public/images/...` precedent in `GameDetails.tsx`. `ExportButton.tsx` and `GameDetails.tsx`'s in-app export buttons migrate to the identical flow for consistency — confirmed no desktop-browser regression.

## Implementation Guidance

- **Objectives**:
  1. Add a second, self-contained "Add to Google Calendar" link to the Discord embed's `Links` field, requiring no backend/auth changes.
  2. Replace the authenticated `.ics` Blob-download flow (behind the Discord-embed link) with a mint-token-then-real-navigate flow so mobile OSes can hand the response to a calendar app instead of force-downloading it.

- **Key Tasks**:
  1. TDD a Google-Calendar-URL-builder function in `services/bot/` (stub → xfail tests asserting exact encoded URLs for: full data, missing description, missing location, missing duration/defaulting to 120 min, long description needing truncation → implement → remove xfail).
  2. TDD wiring the new URL into `_add_game_time_fields`'s `Links` field (existing `tests/unit/services/bot/formatters/test_game_message.py` needs new cases for the two-link field value; must include a "long/unbounded `where` + near-max `title`" test case asserting the field's rendered length stays under Discord's 1024-char cap, per Decision 3 below).
  3. TDD new Redis-backed calendar-export-token functions added to `services/api/auth/tokens.py` (mint/get, unencrypted, TTL-only expiry, no delete, `CacheTTL.CALENDAR_EXPORT_TOKEN = 300`, new `CacheKeys`/`CacheOperation` entries) — stub → xfail tests mirroring that file's existing test suite's style (mock `RedisClient`, assert exact `set_json`/`get_json` call args) → implement.
  4. TDD a new authenticated "mint calendar token" route (reusing `can_export_game` unmodified) — tests modeled on `tests/unit/services/api/routes/test_export.py`'s dependency-override + `patch(...)` style.
  5. TDD a new public, rate-limited, unauthenticated `.ics`-serving route added to `services/api/routes/public.py` as a second `APIRouter` instance — tests modeled on `tests/unit/services/api/routes/test_public.py` (direct function calls with a mocked `Request`/`db`, plus a `TestClient`-based app-level test for the rate-limit-decorated path, matching `public_app` fixture style).
  6. TDD the frontend `DownloadCalendar.tsx` rewrite (Vitest `test.failing` → implement) — mock the mint POST call and assert `window.location.href` was set to the expected relative public URL; keep/adapt the existing 403/404/generic-error test cases against the mint call's failure responses.
  7. TDD migrating `ExportButton.tsx` and `GameDetails.tsx`'s export handlers to the same mint-then-navigate flow, replacing their `axios.get(..., { responseType: 'blob' })` pattern; update their existing test suites accordingly.
  8. Add integration test(s) for the new public `.ics` route under `tests/integration/services/api/routes/`, modeled on `test_public_images.py`/`test_public_images_rate_limit.py` (no existing integration test exists for `export.py` today — note this gap but it's out of scope to backfill unless requested).
  9. Update `services/api/app.py` to register the new second `APIRouter` from `public.py`, following the existing `app.include_router(...)` list.

- **Dependencies**: None blocking — both improvements are purely additive; improvement 2 doesn't remove `services/api/routes/export.py`'s existing authenticated endpoint or `services/api/services/calendar_export.py` (reused, not replaced), though task 7 means `ExportButton.tsx`/`GameDetails.tsx` stop calling it directly once migrated.

- **Success Criteria**: Discord embed's `Links` field shows both the existing frontend calendar-download link and a new, correctly-encoded Google Calendar quick-add link for games with and without optional fields, staying under Discord's 1024-char field cap even with a long `where`/near-max `title`; tapping the Discord-embed calendar link (or either in-app Export button) on a mobile device results in a real `text/calendar` navigation (verifiable via `Content-Disposition: inline` header and `media_type="text/calendar"` in a test/curl, not `attachment`) instead of a forced Blob download; the new public route 404s on missing/expired tokens; full unit + integration test suites green.

## Decisions

All open questions from the initial research pass were resolved in follow-up discussion; recorded here for the planner.

1. **TTL-only expiry, no delete-on-read.** The mint-then-navigate flow never exposes the token URL as a link the user manually taps (it's set programmatically via `window.location.href`), so there's no realistic double-fetch risk from e.g. iOS's long-press link-preview prefetch. The remaining risk is an ordinary network retry, and failing that with a confusing 404 outweighs the marginal security benefit given the token is already low-sensitivity and short-TTL (5 min). Implementation: a lookup function only, no delete counterpart — Redis's own `SETEX` expiry is sufficient.
2. **Rate-limit tier: reuse the existing global `get_rate_limits()` tier**, same as `public.py`'s images route — zero new code. Revisit with a dedicated tier only if it becomes a problem in practice; no per-route-tier plumbing exists today and none should be added speculatively.
3. **URL-length guard: needed, and broader than originally scoped.** `GAME_LIST_DESCRIPTION_SNIPPET_LENGTH` (100) alone is not sufficient: `title` is `String(200)` — double that — and `where` is an **unbounded** `Text` column with no existing truncation anywhere in `game_message.py` (confirmed by reading `shared/models/game.py` L58/62 and grepping `game_message.py` for `where` usage). The Google-link builder needs explicit, conservative caps on `title` and `where` specifically (not just reusing the description constant), sized to account for percent-encoding expansion (spaces/unicode multiply in length when URL-encoded), to keep the two-link `Links` embed field under Discord's 1024-char-per-field cap.
4. **`ExportButton.tsx`/`GameDetails.tsx` migrate too.** Verified there's no desktop-browser regression: Chrome/Edge/Firefox have no built-in `text/calendar` renderer, so navigating to an `inline` response still falls back to a normal file download with the `filename=` hint intact (same end result as today's Blob download); macOS Safari can do better and hand off straight to Calendar.app. Migrating removes a second, divergent Blob-download code path and gives mobile-web users of these buttons the same calendar-app hand-off benefit as the Discord-embed link, for one shared implementation instead of two.
5. **Token helper lives in `services/api/auth/tokens.py`**, alongside `store_user_tokens`/`get_user_tokens`, reusing the same `RedisClient`/`cache_get`/`CacheTTL`/`CacheKeys` building blocks directly rather than a new module.
6. **New public route lives in `services/api/routes/public.py`**, as a second `APIRouter(prefix="/api/v1/public/calendar", tags=["public"])` instance in the same file (the existing router's prefix is hardcoded to `/api/v1/public/images` and can't be shared directly) — no new sibling file. Registered separately in `services/api/app.py`.
7. **Keep `filename=` on `Content-Disposition: inline`.** Confirmed valid per RFC 6266 (`inline` and `filename` are independent parameters) — it's a hint honored by whatever ends up saving the file, inline hand-off or download fallback alike, and costs nothing to include (reuses `generate_calendar_filename`, already implemented and tested in `export.py`).

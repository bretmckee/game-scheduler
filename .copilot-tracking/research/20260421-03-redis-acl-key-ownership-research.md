<!-- markdownlint-disable-file -->

# Task Research Notes: Redis ACL Key Ownership

## Research Executed

### File Analysis

- `shared/cache/keys.py`
  - All key prefix definitions; source of truth for namespace layout
- `shared/cache/client.py`
  - `RedisClient` and `SyncRedisClient`; single `REDIS_URL` env var; no per-service auth today
- `shared/discord/client.py`
  - `get_guild_member()`: REST+Redis cache using `discord:member:{guild_id}:{user_id}`
  - `get_guilds()`: REST+Redis cache using `user_guilds:{user_id}`
  - `get_application_info()`: REST+Redis cache using `discord:app_info`
  - All three are API-only callers (bot uses projection after REST elimination plan)
- `services/api/auth/tokens.py`
  - Writes, reads, and deletes `session:{session_id}`
- `services/api/auth/oauth2.py`
  - Writes and deletes `oauth_state:{state}` (10-minute TTL)
- `services/api/auth/roles.py`
  - Reads `discord:guild_roles:{guild_id}` (bot-written gateway key)
  - Reads and writes `user_roles:{user_id}:{guild_id}` (currently shared-write with bot)
  - Deletes `user_roles:{user_id}:{guild_id}` on force refresh
- `services/api/services/display_names.py`
  - Reads `proj:member:*` (bot-written) and caches resolved string to `display:{guild_id}:{user_id}`
- `services/api/routes/maintainers.py`
  - Scans and deletes `session:*`
  - Deletes `discord:app_info`
- `services/bot/auth/cache.py` (`RoleCache`)
  - `get_user_roles` / `set_user_roles` / `invalidate_user_roles`: reads, writes, deletes `user_roles:{user_id}:{guild_id}`
  - `get_guild_roles` / `set_guild_roles`: reads and writes `guild_config:{guild_id}` — **appears to be legacy/dead code; no callers outside tests found in production bot path**
- `services/bot/auth/role_checker.py`
  - Reads `user_roles:*` via `RoleCache.get_user_roles`; writes via `RoleCache.set_user_roles` after reading `proj:member:*`
- `services/bot/bot.py` + `services/bot/guild_projection.py`
  - Writes all `proj:*`, `bot:last_seen`, `discord:guild:*`, `discord:guild_channels:*`, `discord:channel:*`, `discord:guild_roles:*`
  - Reads `discord:guild_channels:*` in `_refresh_guild_channels`
  - Deletes `discord:channel:{id}` on `on_guild_channel_delete`
- `services/bot/utils/discord_format.py`
  - Calls `discord_api.get_guild_member()` which reads/writes `discord:member:*` via REST cache
  - **Bot-only caller — the research note in the bot REST elimination research claiming this is also called from the API path was incorrect**

### Code Search Results

- `discord_api.` usages in `services/bot/**`
  - `fetch_channel` (1 site in `handlers.py`): removed by bot REST plan Phase 2
  - `fetch_user` (1 site in `handlers.py`): removed by bot REST plan Phase 3
  - `get_guild_member` in `discord_format.py` (1 site): bot-only; deferred by bot REST plan
- `CacheKeys.user_guilds` production callers
  - `shared/discord/client.py` only — API-side REST cache for OAuth guild list
- `CacheKeys.channel_config` and `CacheKeys.game_details`
  - Test-only references in `test_keys.py`; no production callers — dead key definitions
- `CacheKeys.guild_config` production callers
  - `services/bot/auth/cache.py` only — no cross-service usage; no bot production callers found
- `get_member_display_info` callers
  - `services/bot/events/handlers.py` only — confirmed bot-only function

### External Research

- #fetch:https://redis.io/docs/latest/operate/oss_and_stack/management/security/acl/
  - Redis 7.0+ supports `%R~<pattern>` (read-only) and `%W~<pattern>` (write-only) key permissions per user
  - `%RW~<pattern>` is equivalent to `~<pattern>` (full access)
  - Permissions are additive; multiple patterns can be combined on one user
  - ACL defined via `aclfile` directive or inline in `redis.conf`; `ACL LOAD` reloads without restart
  - Valkey 9.0.1 (image in `compose.yaml`) is Redis 7.x-compatible; full ACL support confirmed

### Project Conventions

- `compose.yaml` Redis service uses `REDIS_COMMAND` env var to pass startup flags — ACL file path injected via `--aclfile`
- `REDIS_URL` is a single connection URL used by all services; per-service credentials require `redis://user:password@redis:6379/0` format

## Key Discoveries

### Proposed ACL Topology

Two Redis users replace the current default (unauthenticated) user:

**`bot` user** — owns gateway data; full RWD on projection and gateway namespaces:

```
user bot on ><bot_password>
  %RW~proj:*
  %RW~bot:*
  %RW~discord:guild:*
  %RW~discord:guild_channels:*
  %RW~discord:channel:*
  %RW~discord:guild_roles:*
  %RW~user_roles:*
  +@all -@admin -@dangerous +scan +del
```

**`api` user** — reads gateway data; full RWD on API-owned `api:*` namespace:

```
user api on ><api_password>
  %R~proj:*
  %R~bot:*
  %R~discord:guild:*
  %R~discord:guild_channels:*
  %R~discord:channel:*
  %R~discord:guild_roles:*
  %RW~api:*
  +@all -@admin -@dangerous +scan
```

### Key Namespace Renames Required

All keys currently written by the API outside the `discord:` or `proj:` namespaces move to an `api:` prefix. Keys in `discord:` that are actually REST caches (not gateway data) also move to `api:`.

| Current key                           | Proposed key                          | API callers                                      |
| ------------------------------------- | ------------------------------------- | ------------------------------------------------ |
| `session:{id}`                        | `api:session:{id}`                    | `tokens.py`, `maintainers.py`                    |
| `oauth_state:{state}`                 | `api:oauth:{state}`                   | `oauth2.py`                                      |
| `display:{guild_id}:{user_id}`        | `api:display:{guild_id}:{user_id}`    | `display_names.py`                               |
| `user_guilds:{user_id}`               | `api:user_guilds:{user_id}`           | `shared/discord/client.py` (OAuth path)          |
| `discord:app_info`                    | `api:app_info`                        | `shared/discord/client.py`, `maintainers.py`     |
| `discord:member:{guild_id}:{user_id}` | `api:member:{guild_id}:{user_id}`     | `shared/discord/client.py` (after bot REST plan) |
| `user_roles:{user_id}:{guild_id}`     | `api:user_roles:{user_id}:{guild_id}` | `roles.py` — see note below                      |

### The `user_roles:*` Ownership Decision

Both services currently write `user_roles:*`:

- **Bot** (`role_checker.py`): reads `proj:member:*` → writes `user_roles:*` as a derived cache
- **API** (`roles.py`): reads `proj:member:*` → writes `user_roles:*` as a derived cache; also deletes on force refresh

Assigning ownership to the API requires removing the bot's write path. In `role_checker.py`, `get_user_role_ids` checks `RoleCache.get_user_roles` first, then falls back to `guild_projection.get_user_roles` and caches the result. With API ownership, the bot drops the cache check and always reads `proj:member:*` directly. Since the bot makes this call on every permission check during interactions — not on a hot loop — the extra projection read is negligible.

`RoleCache.get_guild_roles` / `set_guild_roles` use `guild_config:{guild_id}`. No production callers were found outside the class itself. Both methods and the `guild_config:*` key definition can be deleted.

### The `discord:app_info` and `discord:member:*` Split

These two keys live in `discord:` but are not gateway-written:

- `discord:app_info`: populated by REST call `GET /oauth2/applications/@me`, only used in the API maintainer elevation path. Rename to `api:app_info`.
- `discord:member:{guild_id}:{user_id}`: populated by REST call `GET /guilds/{id}/members/{uid}`. Currently also written by the bot via `discord_format.py`. After the bot REST plan migrates `discord_format.py` to read from `proj:member:*`, this becomes API-only. Rename to `api:member:{guild_id}:{user_id}`.

Renaming both cleanly separates gateway data from REST cache data, allowing a simple `%R~discord:*` rule on the API user with no carve-outs.

### Dependency on Bot REST Elimination Plan

**This work should not be implemented until the bot REST elimination plan is complete.**

The bot REST elimination plan (`.copilot-tracking/planning/plans/20260421-02-bot-rest-api-elimination.plan.md`) currently defers `discord_format.py` migration as "needs careful scoping." The access matrix for `discord:member:*` is indeterminate until that decision is made. After the bot REST plan is done:

1. Recheck whether `discord_format.py` was migrated to `proj:member:*`
2. If yes: `discord:member:*` is API-only; rename to `api:member:*` proceeds cleanly
3. If no: both users still write `discord:member:*`; the rename still happens but both users need `%RW~api:member:*` temporarily until the migration is completed

In either case, the key renames and bot role-cache removal can proceed as a prerequisite independent of the ACL wiring.

## Implementation Guidance

- **Objectives**: Enforce Redis key ownership at the server level as defense in depth; prevent accidental API writes to gateway data and accidental bot writes to API session/auth data
- **Key Tasks**:
  1. Complete bot REST elimination plan (prerequisite)
  2. Confirm whether `discord_format.py` was migrated; update `discord:member:*` ownership accordingly
  3. Rename seven API-owned keys to `api:*` prefix in `shared/cache/keys.py` and all callers
  4. Remove bot's `user_roles:*` write path from `role_checker.py` and `cache.py`
  5. Delete dead `guild_config:*` code in `services/bot/auth/cache.py`
  6. Add `config/redis/users.acl` with `bot` and `api` user definitions
  7. Update compose files to mount ACL file and pass `--aclfile` to Valkey; disable `default` user
  8. Update all `REDIS_URL` env vars in `config/env.*` and compose files to include credentials
  9. Update test fixtures to use a privileged connection (or provision both ACL users) for integration/e2e tests
- **Dependencies**: Bot REST elimination plan must complete before ACL wiring; key renames and bot cache cleanup can proceed independently
- **Success Criteria**:
  - `valkey-cli ACL LIST` shows exactly `bot` and `api` users; `default` user disabled
  - API `SET discord:guild:any` returns `NOPERM`
  - Bot `SET api:session:any` returns `NOPERM`
  - All integration and e2e test suites pass

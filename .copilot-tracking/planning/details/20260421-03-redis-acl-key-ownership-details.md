<!-- markdownlint-disable-file -->

# Task Details: Redis ACL Key Ownership

## Research Reference

**Source Research**: #file:../research/20260421-03-redis-acl-key-ownership-research.md

---

## Phase 1: Rename API-owned session/auth/display keys to `api:` prefix

### Task 1.1: Update `CacheKeys` constants in `shared/cache/keys.py`

Update five key prefix constants so they carry the `api:` namespace.

- **Files**:
  - `shared/cache/keys.py` — rename the following constants:
    - `SESSION_KEY` prefix: `session:` → `api:session:`
    - `OAUTH_STATE_KEY` prefix: `oauth_state:` → `api:oauth:`
    - `DISPLAY_NAME_KEY` prefix: `display:` → `api:display:`
    - `USER_GUILDS_KEY` prefix: `user_guilds:` → `api:user_guilds:`
    - `APP_INFO_KEY` value: `discord:app_info` → `api:app_info`
- **Success**:
  - `CacheKeys` constants reflect new prefixes
  - Unit tests in `test_keys.py` updated to assert new values
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 107-120) — key namespace renames table
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 7-43) — File Analysis: keys.py layout
- **Dependencies**:
  - None; this phase is independent of the bot REST plan

### Task 1.2: Update all callers of the renamed keys

Mechanically replace old key constants/strings in every API caller file.

- **Files**:
  - `services/api/auth/tokens.py` — uses `SESSION_KEY`; no string change needed if constant updated
  - `services/api/auth/oauth2.py` — uses `OAUTH_STATE_KEY`
  - `services/api/services/display_names.py` — uses `DISPLAY_NAME_KEY`
  - `services/api/routes/maintainers.py` — scans `session:*` pattern and deletes `discord:app_info`; update both literal patterns
  - `shared/discord/client.py` — uses `USER_GUILDS_KEY` and `APP_INFO_KEY`
- **Success**:
  - No production file references the old key strings
  - `grep -r 'session:{\|oauth_state:\|display:{\|user_guilds:\|discord:app_info' services/ shared/` returns no hits
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 7-43) — caller inventory per key
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 107-120) — callers listed in renames table
- **Dependencies**:
  - Task 1.1 complete

### Task 1.3: Update test fixtures and assertions referencing old key strings

Find all unit/integration test files that assert on old key strings and update them.

- **Files**:
  - Any `test_*.py` under `tests/` that construct or match `session:`, `oauth_state:`, `display:`, `user_guilds:`, or `discord:app_info` strings
- **Success**:
  - Full unit test suite passes with no failures related to key name mismatches
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 44-58) — Code Search Results confirms which files reference each key
- **Dependencies**:
  - Tasks 1.1 and 1.2 complete

---

## Phase 2: Transfer `user_roles:*` ownership to API; remove bot write path

### Task 2.1: Rename `user_roles` key to `api:user_roles` and update `roles.py`

Rename the key constant and update the one API caller.

- **Files**:
  - `shared/cache/keys.py` — rename `USER_ROLES_KEY` prefix: `user_roles:` → `api:user_roles:`
  - `services/api/auth/roles.py` — reads, writes, and deletes `user_roles:*`; no string changes needed if constant is used
- **Success**:
  - `roles.py` reads and writes the renamed key correctly
  - Unit tests for `roles.py` updated to reflect new key prefix
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 121-131) — user_roles ownership decision
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 107-120) — renames table entry for user_roles
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Remove bot's `user_roles:*` write path from `role_checker.py`

The bot currently checks the cache before reading the projection; remove that cache layer entirely so the bot always reads `proj:member:*` directly.

TDD applies: write a failing test first that asserts the bot reads from the projection without a cache write, mark it `xfail`, remove the cache path, confirm test passes, remove `xfail`.

- **Files**:
  - `services/bot/auth/role_checker.py` — in `get_user_role_ids`:
    - Remove `RoleCache.get_user_roles` check
    - Remove `RoleCache.set_user_roles` write after projection lookup
    - Always call `guild_projection.get_user_roles` (or equivalent projection read) directly
  - `tests/` — add/update test for `get_user_role_ids` to assert no cache write occurs
- **Success**:
  - `role_checker.py` contains no `set_user_roles` call
  - Test asserts projection is called on every invocation; no `user_roles:*` key is written
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 121-131) — rationale: projection read on every permission check is acceptable
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 7-43) — role_checker.py and cache.py File Analysis
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Delete dead `guild_config:*` code from `cache.py` and `keys.py`

No production callers exist for `RoleCache.get_guild_roles`, `RoleCache.set_guild_roles`, or `CacheKeys.guild_config`. Delete them.

- **Files**:
  - `services/bot/auth/cache.py` — delete `get_guild_roles` and `set_guild_roles` methods from `RoleCache`
  - `shared/cache/keys.py` — delete `GUILD_CONFIG_KEY` (or equivalent) constant
  - Any test that calls the deleted methods — delete those tests (they test dead code)
- **Success**:
  - `cache.py` contains no `guild_config` references
  - `keys.py` contains no `guild_config` constant
  - `grep -r 'guild_config' services/ shared/ tests/` returns no hits
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 44-58) — Code Search: `CacheKeys.guild_config` has no production callers
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 34-43) — File Analysis: RoleCache methods confirmed as dead
- **Dependencies**:
  - Task 2.2 complete (ensures bot write path already removed)

---

## Phase 3: Rename `discord:member:*` to `api:member:*`

**Prerequisite**: Bot REST elimination plan must be complete.

### Task 3.1: Verify `discord_format.py` has been migrated to `proj:member:*`

Before renaming, confirm the bot no longer writes `discord:member:*` via REST cache.

- **Files**:
  - `services/bot/utils/discord_format.py` — check whether `get_guild_member()` REST call is still present or has been replaced by a `proj:member:*` projection read
- **Success**:
  - If migrated: `discord_format.py` reads `proj:member:*`; `discord:member:*` is API-only → proceed to Task 3.2
  - If NOT migrated: document the gap; `discord:member:*` temporarily needs `%RW~api:member:*` on the bot ACL user; proceed anyway and note the caveat in the changes file
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 132-140) — discord:member ownership decision and both paths
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 141-152) — dependency on bot REST plan
- **Dependencies**:
  - Bot REST elimination plan complete

### Task 3.2: Rename `CacheKeys.member` and update `shared/discord/client.py`

Rename the constant and update the one caller.

- **Files**:
  - `shared/cache/keys.py` — rename member key prefix: `discord:member:` → `api:member:`
  - `shared/discord/client.py` — uses the member key in `get_guild_member()`
- **Success**:
  - `grep -r 'discord:member' services/ shared/` returns no hits (or only the bot caller if discord_format.py was not yet migrated, documented in Task 3.1)
  - Unit tests updated to assert new key prefix
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 107-120) — renames table entry for discord:member
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 132-140) — discord:app_info and discord:member split rationale
- **Dependencies**:
  - Task 3.1 complete

---

## Phase 4: ACL infrastructure wiring

**Prerequisite**: Bot REST elimination plan must be complete; Phases 1–3 complete.

### Task 4.1: Create `config/redis/users.acl` with `bot` and `api` user definitions

Write the ACL file using the topology from the research. Use environment variable substitution for passwords (resolved at container startup via `envsubst` or Valkey's `$REDIS_PASSWORD` syntax if supported, otherwise use a startup script).

- **Files**:
  - `config/redis/users.acl` (new) — exact content:
    ```
    user bot on ><BOT_REDIS_PASSWORD>
      %RW~proj:*
      %RW~bot:*
      %RW~discord:guild:*
      %RW~discord:guild_channels:*
      %RW~discord:channel:*
      %RW~discord:guild_roles:*
      %RW~api:user_roles:*
      +@all -@admin -@dangerous +scan +del
    user api on ><API_REDIS_PASSWORD>
      %R~proj:*
      %R~bot:*
      %R~discord:guild:*
      %R~discord:guild_channels:*
      %R~discord:channel:*
      %R~discord:guild_roles:*
      %RW~api:*
      +@all -@admin -@dangerous +scan
    user default off nopass nocommands
    ```
  - `config.template/env.template` — add `BOT_REDIS_PASSWORD` and `API_REDIS_PASSWORD` variables
- **Success**:
  - ACL file parses without error: `valkey-cli ACL LOAD` succeeds
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 75-106) — full ACL topology with both user blocks
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 59-67) — Redis 7.x ACL syntax confirmed
- **Dependencies**:
  - Phases 1–3 complete (all key renames done so ACL patterns are final)

### Task 4.2: Update compose files to mount ACL file and inject `--aclfile` flag

- **Files**:
  - `compose.yaml` — add volume mount for `config/redis/users.acl` into the Valkey service; set `REDIS_COMMAND` to include `--aclfile /etc/redis/users.acl`
  - `compose.int.yaml` — same mount/flag for integration test Redis service
  - `compose.e2e.yaml` — same mount/flag for e2e test Redis service
- **Success**:
  - `docker compose up redis` starts without error; `valkey-cli ACL LIST` shows three users
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 68-72) — Project Conventions: REDIS_COMMAND pattern
- **Dependencies**:
  - Task 4.1 complete

### Task 4.3: Update `REDIS_URL` env vars to include per-service credentials

- **Files**:
  - `config.template/env.template` — split `REDIS_URL` into `BOT_REDIS_URL` and `API_REDIS_URL` using `redis://bot:<BOT_REDIS_PASSWORD>@redis:6379/0` and `redis://api:<API_REDIS_PASSWORD>@redis:6379/0`
  - All compose files that pass `REDIS_URL` to service containers — update variable name per service
  - `shared/cache/client.py` — verify it reads the env var name used by each service; update if needed
- **Success**:
  - API container cannot authenticate with bot credentials and vice versa
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 68-72) — `REDIS_URL` single URL pattern; per-service credential format
- **Dependencies**:
  - Task 4.2 complete

### Task 4.4: Update test infrastructure to provision both ACL users

Integration and e2e test Redis must also enforce ACLs. Test fixtures that use a bare connection need a privileged or test-specific user.

- **Files**:
  - Test compose files (compose.int.yaml, compose.e2e.yaml) — pass both `BOT_REDIS_URL` and `API_REDIS_URL` to test containers
  - Shared test fixtures — update `redis_client` fixture to use appropriate URL per test domain; or add a superuser `test` entry to the ACL file used in test environments with access to all keys
- **Success**:
  - Integration and e2e suites pass with ACL enforcement active
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 153-171) — Key Tasks item 9 mentions test fixture update requirement
- **Dependencies**:
  - Tasks 4.2 and 4.3 complete

### Task 4.5: Verify ACL enforcement with integration test or manual check

- **Files**:
  - Ad-hoc verification (manual or one-off script): connect as `api` user and attempt `SET discord:guild:test`; expect `NOPERM`; connect as `bot` user and attempt `SET api:session:test`; expect `NOPERM`
- **Success**:
  - `SET discord:guild:any` as `api` user → `NOPERM`
  - `SET api:session:any` as `bot` user → `NOPERM`
  - All integration and e2e test suites pass
- **Research References**:
  - #file:../research/20260421-03-redis-acl-key-ownership-research.md (Lines 153-171) — Success Criteria section
- **Dependencies**:
  - Task 4.4 complete

---

## Dependencies

- Bot REST elimination plan complete (required before Phase 3 and Phase 4)
- Valkey 9.0.1 already in `compose.yaml` — Redis 7.x `%R~` / `%W~` ACL syntax supported

## Success Criteria

- All key constants and callers use `api:` prefix for API-owned data
- Bot `role_checker.py` has no `user_roles:*` write; reads projection directly
- `valkey-cli ACL LIST` shows `bot`, `api`, and disabled `default` users
- Cross-service write attempts return `NOPERM`
- All integration and e2e test suites pass

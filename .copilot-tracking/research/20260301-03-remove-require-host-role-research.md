<!-- markdownlint-disable-file -->

# Task Research Notes: Remove `require_host_role` Field

## Research Executed

### File Analysis

- `shared/models/guild.py`
  - `require_host_role: Mapped[bool]` column with `default=False`, `server_default="false"`
  - Part of `GuildConfiguration` ORM model

- `shared/schemas/guild.py`
  - Present in three schema classes: `GuildConfigCreateRequest` (field with default), `GuildConfigUpdateRequest` (optional field), `GuildConfigResponse` (required field)

- `services/api/routes/guilds.py`
  - Read in `_build_guild_config_response` (line 71) when constructing the API response
  - Written in `create_guild_config` route handler (line 187) via `request.require_host_role`
  - Written in `update_guild_config` via generic `model_dump(exclude_unset=True)` — no dedicated reference, but the field passes through

- `services/api/auth/roles.py`
  - Does NOT reference `require_host_role` — confirmed dead code relative to this flag
  - `check_game_host_permission` only gates on `allowed_host_role_ids` (per-template) and bot manager status

- `services/api/services/template_service.py`
  - Does NOT consult `require_host_role` — filtering is purely by per-template `allowed_host_role_ids`

- `services/api/services/guild_service.py`
  - `create_guild_config` raises `NotImplementedError` (stubbed for Phase 6 migration), so the API create route is non-functional anyway

- `services/bot/guild_sync.py`
  - `create_guild_config` is the real implementation; passes `**settings` to `GuildConfiguration(...)` — would accept `require_host_role` kwargs but none are passed by its caller

- `frontend/src/pages/GuildConfig.tsx`
  - Form state: `requireHostRole: false` initialized, loaded from API, sent in PUT body as `require_host_role`
  - Checkbox control: "Require host role to create games" label

- `alembic/versions/c2135ff3d5cd_initial_schema.py`
  - `require_host_role` defined in the initial schema migration — requires a new migration to drop the column

### Code Search Results

- `require_host_role` across `**/*.py`
  - 20 matches: model, schemas (3 classes), routes (2 references), alembic (1), tests
- `require_host_role` in frontend
  - `GuildConfig.tsx`: form state, load, save, checkbox render (5 locations)
  - `GuildConfig.test.tsx`: checkbox label assertion (2 locations)
- `check_game_host_permission` across `**/*.py`
  - 3 call sites: `template_service.py`, `games.py`, `dependencies/permissions.py` — none consult `require_host_role`
- `@everyone` in `services/api/auth/roles.py` line 85
  - `get_user_role_ids` explicitly adds the guild ID to every user's role list, matching Discord's `@everyone` snowflake convention
- `guilds.py` line 293: `@everyone` role is explicitly allowed through the role picker for templates

### Project Conventions

- Alembic migrations required for any schema change; must not modify existing migrations
- Tests must be updated alongside code; pre-commit hooks enforce passing tests

## Key Discoveries

### Why `require_host_role` Is Dead Code

The flag was intended to be a guild-level toggle to bypass per-template host role requirements. However, the `check_game_host_permission` function — which is the sole enforcement point — never received an implementation that consults this flag. The permission logic is entirely driven by `allowed_host_role_ids` on each `GameTemplate`. As a result:

- Checking the box changes nothing for users trying to create games
- Unchecking the box changes nothing for users trying to create games
- Users reported being blocked despite the box being unchecked

### Why `@everyone` as a Template Role Covers the Use Case

Discord's `@everyone` role has the same snowflake ID as the guild itself. `get_user_role_ids` in `roles.py` (line 85) explicitly adds the guild ID to every user's effective role set. `allowed_host_role_ids` is checked with a simple `any(role_id in allowed_host_role_ids ...)`, so adding the guild's snowflake as an allowed host role grants all members access. The guild roles endpoint already allows `@everyone` through the role picker.

### Behavioral Impact of Removal

No behavior changes for any existing server. Servers already using `@everyone` as a template host role work correctly today. Servers with the checkbox unchecked are broken today and will remain fixed only via the `@everyone` template approach after removal.

### Files Requiring Changes

| File                                                | Change                                                                         |
| --------------------------------------------------- | ------------------------------------------------------------------------------ |
| `shared/models/guild.py`                            | Remove `require_host_role` column mapping                                      |
| `shared/schemas/guild.py`                           | Remove from all three schema classes                                           |
| `services/api/routes/guilds.py`                     | Remove from `_build_guild_config_response` and `create_guild_config` handler   |
| `services/api/services/guild_service.py`            | No change needed (stubbed function; no reference)                              |
| `services/bot/guild_sync.py`                        | No change needed (passes `**settings`; no caller sends the field)              |
| `frontend/src/pages/GuildConfig.tsx`                | Remove form state, load, save, and checkbox UI                                 |
| `frontend/src/pages/__tests__/GuildConfig.test.tsx` | Remove checkbox assertions                                                     |
| `tests/services/api/routes/test_guilds.py`          | Remove all 10 `require_host_role` references                                   |
| `tests/services/bot/test_guild_sync.py`             | Remove references at lines 461, 480                                            |
| `alembic/versions/`                                 | New migration to `op.drop_column("guild_configurations", "require_host_role")` |

## Recommended Approach

Remove the `require_host_role` field entirely from the database, ORM model, schemas, API, frontend, and tests. Create a new Alembic migration to drop the column. No data migration is needed since the field had no effect.

After removal, update documentation (e.g., GUILD-ADMIN.md) to clarify that open hosting is configured by adding `@everyone` to a template's allowed host roles.

## Implementation Guidance

- **Objectives**: Eliminate the broken `require_host_role` feature entirely and surface correct guidance about `@everyone` template role
- **Key Tasks**:
  1. New Alembic migration: `drop_column("guild_configurations", "require_host_role")`
  2. Remove from `GuildConfiguration` ORM model
  3. Remove from all three Pydantic schema classes
  4. Remove from `_build_guild_config_response` and `create_guild_config` route
  5. Remove form state, fetch, save, and checkbox from `GuildConfig.tsx`
  6. Update all affected tests
- **Dependencies**: None; isolated to this field with no callers that actually use its value
- **Success Criteria**: Pre-commit passes; no remaining references to `require_host_role` in non-migration files; checkbox no longer appears in the server config UI

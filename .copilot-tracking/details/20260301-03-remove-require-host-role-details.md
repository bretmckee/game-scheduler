<!-- markdownlint-disable-file -->

# Task Details: Remove `require_host_role` Field

## Research Reference

**Source Research**: #file:../research/20260301-03-remove-require-host-role-research.md

---

## Phase 1: Database Migration

### Task 1.1: New Alembic Migration to Drop `require_host_role`

Create a new Alembic migration that drops the `require_host_role` column from the `guild_configurations` table. Do not modify the existing `c2135ff3d5cd_initial_schema.py`.

- **Command**: `uv run alembic revision --autogenerate -m "remove_require_host_role"`
- **Files**:
  - `alembic/versions/<generated_hash>_remove_require_host_role.py` — new migration file
- **Migration body must contain**:

  ```python
  def upgrade() -> None:
      op.drop_column("guild_configurations", "require_host_role")

  def downgrade() -> None:
      op.add_column(
          "guild_configurations",
          sa.Column("require_host_role", sa.Boolean(), server_default=sa.text("false"), nullable=False),
      )
  ```

- **Success**:
  - Migration file created with correct `upgrade` and `downgrade`
  - `uv run alembic upgrade head` completes without error (against a test DB if available)
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 43-45) — alembic conventions
- **Dependencies**: None

---

## Phase 2: Backend Removal

### Task 2.1: Remove ORM Column from `shared/models/guild.py`

Remove the `require_host_role` mapped column at line 50.

- **Files**:
  - `shared/models/guild.py` — remove `require_host_role: Mapped[bool] = mapped_column(...)` at line 50
- **Success**:
  - `grep "require_host_role" shared/models/guild.py` returns nothing
  - Module imports without error
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 6-8) — model definition
- **Dependencies**: Task 1.1 (migration must exist before removing model column)

### Task 2.2: Remove from All Three Schema Classes in `shared/schemas/guild.py`

Three fields to remove:

| Class                      | Line | Type                  |
| -------------------------- | ---- | --------------------- |
| `GuildConfigCreateRequest` | 31   | `bool = Field(…)`     |
| `GuildConfigUpdateRequest` | 41   | `bool \| None = None` |
| `GuildConfigResponse`      | 61   | `bool = Field(…)`     |

- **Files**:
  - `shared/schemas/guild.py` — remove field declaration from each class
- **Success**:
  - `grep "require_host_role" shared/schemas/guild.py` returns nothing
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 9-13) — schema classes
- **Dependencies**: Task 2.1

### Task 2.3: Remove from API Routes in `services/api/routes/guilds.py`

Two usage sites:

- **Line 71** (`_build_guild_config_response`): remove `require_host_role=guild_config.require_host_role,` kwarg
- **Line 187** (`create_guild_config`): remove `require_host_role=request.require_host_role,` kwarg

- **Files**:
  - `services/api/routes/guilds.py`
- **Success**:
  - `grep "require_host_role" services/api/routes/guilds.py` returns nothing
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 14-19) — routes references
- **Dependencies**: Task 2.2

---

## Phase 3: Backend Test Cleanup

### Task 3.1: Clean Up `tests/services/api/routes/test_guilds.py`

Ten occurrences to remove across multiple test functions. For each occurrence, remove the line that sets or asserts `require_host_role`. Where the attribute is set on a mock object (`mock_guild_config.require_host_role = ...`), simply delete that line — no replacement needed because the attribute no longer exists on the model.

| Line | Context                                       |
| ---- | --------------------------------------------- |
| 49   | `config.require_host_role = False`            |
| 229  | `new_config.require_host_role = False`        |
| 237  | `require_host_role=False,`                    |
| 295  | `updated_config.require_host_role = True`     |
| 302  | `require_host_role=True,`                     |
| 312  | `assert result.require_host_role is True`     |
| 432  | `mock_guild_config.require_host_role = True`  |
| 444  | `assert result.require_host_role is True`     |
| 458  | `mock_guild_config.require_host_role = False` |
| 468  | `assert result.require_host_role is False`    |

- **Files**:
  - `tests/services/api/routes/test_guilds.py`
- **Success**:
  - `grep "require_host_role" tests/services/api/routes/test_guilds.py` returns nothing
  - `uv run pytest tests/services/api/routes/test_guilds.py` passes
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 35-38) — test search results
- **Dependencies**: Task 2.3

### Task 3.2: Clean Up `tests/services/bot/test_guild_sync.py`

Two occurrences to remove:

| Line | Context                                           |
| ---- | ------------------------------------------------- |
| 461  | `existing_guild.require_host_role = True`         |
| 480  | `assert existing_guild.require_host_role is True` |

Both are in the same test; line 480 asserts the value is unchanged after a sync operation. Remove both lines.

- **Files**:
  - `tests/services/bot/test_guild_sync.py`
- **Success**:
  - `grep "require_host_role" tests/services/bot/test_guild_sync.py` returns nothing
  - `uv run pytest tests/services/bot/test_guild_sync.py` passes
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 38-39) — bot test references
- **Dependencies**: Task 2.1

---

## Phase 4: Frontend Removal

### Task 4.1: Remove from `frontend/src/pages/GuildConfig.tsx`

Five locations to update:

| Line    | Change                                                                                        |
| ------- | --------------------------------------------------------------------------------------------- |
| 57      | Remove `requireHostRole: false,` from initial form state object                               |
| 74      | Remove `requireHostRole: guildData.require_host_role,` from data-load block                   |
| 116     | Remove `require_host_role: formData.requireHostRole,` from PUT request body                   |
| 224-231 | Remove the entire `<FormControlLabel>` / `<Checkbox>` block for the "Require host role" field |

- **Files**:
  - `frontend/src/pages/GuildConfig.tsx`
- **Success**:
  - `grep -E "requireHostRole|require_host_role|Require host role" frontend/src/pages/GuildConfig.tsx` returns nothing
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 25-30) — frontend locations
- **Dependencies**: None (frontend is independent of Python backend)

### Task 4.2: Remove from `frontend/src/pages/__tests__/GuildConfig.test.tsx`

Three locations to address:

| Line    | Change                                                                                      |
| ------- | ------------------------------------------------------------------------------------------- |
| 124     | Remove comment `// require_host_role may be true or undefined depending on form state`      |
| 161-165 | Remove the block that locates and asserts the `requireHostRole` checkbox is in the document |

- **Files**:
  - `frontend/src/pages/__tests__/GuildConfig.test.tsx`
- **Success**:
  - `grep -E "requireHostRole|require_host_role|Require host role" frontend/src/pages/__tests__/GuildConfig.test.tsx` returns nothing
  - `cd frontend && npm test` passes
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 31-34) — frontend test references
- **Dependencies**: Task 4.1

---

## Phase 5: Documentation

### Task 5.1: Update `docs/GUILD-ADMIN.md`

Remove any mention of the "Require host role to create games" checkbox. Add a note explaining that open hosting (allowing all server members to create games) is achieved by adding the `@everyone` role to a template's allowed host roles.

- **Files**:
  - `docs/GUILD-ADMIN.md`
- **Success**:
  - `grep -i "require_host_role\|Require host role" docs/GUILD-ADMIN.md` returns nothing
  - Documentation accurately reflects current behavior
- **Research References**:
  - #file:../research/20260301-03-remove-require-host-role-research.md (Lines 70-80) — @everyone explanation and behavioral impact
- **Dependencies**: None

---

## Dependencies

- `uv` for running Python commands and Alembic migrations
- `npm` for running frontend tests

## Success Criteria

- `grep -r "require_host_role" services/ shared/ tests/ frontend/src/ docs/` returns no results
- `uv run pytest tests/` passes
- `cd frontend && npm test` passes
- `uv run alembic upgrade head` applies cleanly

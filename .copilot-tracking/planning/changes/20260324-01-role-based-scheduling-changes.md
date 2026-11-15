# Changes: Role-Based Scheduling Method

## Status

Phases 1–6 complete.

## Added

- `alembic/versions/b7c8d9e0f1a2_add_signup_priority_role_ids.py` — Alembic migration adds nullable JSON `signup_priority_role_ids` column to `game_templates`

## Modified

- `shared/models/participant.py` — Added `ROLE_MATCHED = 16000` to `ParticipantType` IntEnum between `HOST_ADDED` and `SELF_ADDED`
- `shared/models/signup_method.py` — Added `ROLE_BASED = "ROLE_BASED"` to `SignupMethod` StrEnum with display_name and description
- `shared/models/template.py` — Added `signup_priority_role_ids: Mapped[list[str] | None]` JSON column to `GameTemplate`
- `shared/schemas/template.py` — Added `signup_priority_role_ids` field with max-8 validator to `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, and `TemplateListItem`
- `shared/utils/participant_sorting.py` — Added `resolve_role_position(user_role_ids, priority_role_ids) -> tuple[int, int]` pure function
- `services/api/services/games.py` — Added `position_type` and `position` optional params to `join_game`; added `selectinload(GameSession.template)` to `get_game` eager load
- `services/api/routes/games.py` — Added `_resolve_role_position_for_user` helper; updated `join_game` route to resolve role priority and pass to service
- `services/bot/auth/role_checker.py` — Added `seed_user_roles` async method
- `services/bot/handlers/join_game.py` — Updated `_validate_join_game` to load template with `selectinload`; added `_resolve_bot_role_position` helper; updated participant creation to use resolved position
- `frontend/src/types/index.ts` — Added `ROLE_BASED` to `SignupMethod` enum, `ROLE_MATCHED = 16000` to `ParticipantType` enum, `ROLE_BASED` entry to `SIGNUP_METHOD_INFO`, and `signup_priority_role_ids?: string[] | null` to `GameTemplate` and `TemplateCreateRequest` interfaces
- `tests/unit/shared/utils/test_participant_sorting.py` — Added `TestResolveRolePosition` class with 5 tests; added `resolve_role_position` to imports; added `test_role_matched_participant_type_value`
- `tests/unit/shared/models/test_signup_method.py` — Added `test_role_based_signup_method`; updated `test_signup_method_members` count from 2 to 3; added `import pytest`
- `tests/unit/schemas/test_schemas_template_schema.py` — Added three tests for `signup_priority_role_ids` acceptance, max-8 enforcement, and `TemplateResponse` exposure; added `import pytest`
- `tests/unit/services/bot/auth/test_role_checker.py` — Added `test_seed_user_roles_writes_to_cache`
- `tests/e2e/test_role_based_signup.py` — New E2E test with 4 parametrized cases covering role at index 0, role at index 1, no matching role, and empty priority list; skipped (not failed) when `DISCORD_TEST_ROLE_A_ID`/`DISCORD_TEST_ROLE_B_ID` are absent
- `config/env.e2e` — Added `DISCORD_TEST_ROLE_A_ID` and `DISCORD_TEST_ROLE_B_ID` placeholder vars with comments
- `docs/developer/TESTING.md` — Added "Role-Based Signup E2E Test Roles" section (step 6) documenting required Guild A roles and env setup

## Removed

None.

## Divergences from Plan

None.

---

<!-- Merged from the former .copilot-tracking/changes/ copy of this log -->

# Changes: Role-Based Scheduling Method

## Summary

Implementing the `ROLE_BASED` signup method: resolves Discord role priority once at join
time and stores it in existing `position_type`/`position` DB columns, leaving all sort
and partition logic unchanged.

## Phase 1: Enum Updates (Python + TypeScript) — COMPLETE

- Added `ROLE_MATCHED = 16000` to `ParticipantType` in `shared/models/participant.py`
- Added `ROLE_BASED` to `SignupMethod` in `shared/models/signup_method.py`
- Added `ROLE_BASED` to `SignupMethod` enum in `frontend/src/types/index.ts`
- Added `ROLE_MATCHED = 16000` to `ParticipantType` enum in `frontend/src/types/index.ts`
- Added `SIGNUP_METHOD_INFO` entry for `ROLE_BASED` in `frontend/src/types/index.ts`
- Added `signup_priority_role_ids?: string[] | null` to `GameTemplate`,
  `TemplateCreateRequest`, `TemplateUpdateRequest` in `frontend/src/types/index.ts`

## Phase 2: Database Migration and Model/Schema Updates — COMPLETE

- Added Alembic migration `versions/20260324_01_add_signup_priority_role_ids.py`
- Added `signup_priority_role_ids` JSON column to `GameTemplate` SQLAlchemy model
  in `shared/models/template.py`
- Added `signup_priority_role_ids` field with max-8 validator to Pydantic schemas
  in `shared/schemas/template.py`
- Added `signup_priority_role_ids` to `TemplateResponse` in
  `services/api/routes/templates.py`

## Phase 3: Core Logic (TDD) — COMPLETE

- Added `resolve_role_position` pure function to `shared/utils/participant_sorting.py`
- Added tests for `resolve_role_position` in `tests/unit/test_participant_sorting.py`
- Added `seed_user_roles` method on `RoleChecker` in `services/bot/auth/role_checker.py`
- Added tests for `seed_user_roles` in `tests/unit/test_role_checker.py`
  - Task 3.1, 3.2 complete

## Phase 4: Join Path Updates — COMPLETE

- Updated `GameService.join_game` to accept optional `position_type`/`position` params
  in `services/api/services/games.py`
- Updated API `join_game` route to resolve role priority and pass to service
  in `services/api/routes/games.py`
- Updated bot `handle_join_game` to resolve role priority from interaction payload
  in `services/bot/handlers/join_game.py`

## Phase 5: Frontend Updates — COMPLETE

### Task 5.2: TemplateForm.tsx role priority section

- Added draggable role-priority list to `frontend/src/components/TemplateForm.tsx`
  in the locked settings section (after Allowed Host Roles)
- Uses HTML5 drag API (no third-party drag library needed)
- `UI.MAX_SIGNUP_PRIORITY_ROLES = 8` constant added to `frontend/src/constants/ui.ts`
- Add button disabled when 8 roles are already selected
- Serializes as `signup_priority_role_ids: string[] | null` in priority order
- Added 8 tests for role priority section in
  `frontend/src/components/__tests__/TemplateForm.test.tsx`
- Updated pre-existing test query from `/add/i` to `/^add$/i` to disambiguate
  from the new "Add Role" button

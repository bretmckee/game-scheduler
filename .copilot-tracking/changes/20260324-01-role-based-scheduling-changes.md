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

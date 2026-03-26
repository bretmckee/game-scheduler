# Changes: Role-Based Scheduling Method

## Status

Phases 1 and 2 complete. Phases 3–6 pending.

## Added

- `alembic/versions/b7c8d9e0f1a2_add_signup_priority_role_ids.py` — Alembic migration adds nullable JSON `signup_priority_role_ids` column to `game_templates`

## Modified

- `shared/models/participant.py` — Added `ROLE_MATCHED = 16000` to `ParticipantType` IntEnum between `HOST_ADDED` and `SELF_ADDED`
- `shared/models/signup_method.py` — Added `ROLE_BASED = "ROLE_BASED"` to `SignupMethod` StrEnum with display_name and description
- `shared/models/template.py` — Added `signup_priority_role_ids: Mapped[list[str] | None]` JSON column to `GameTemplate`
- `shared/schemas/template.py` — Added `signup_priority_role_ids` field with max-8 validator to `TemplateCreateRequest`, `TemplateUpdateRequest`, `TemplateResponse`, and `TemplateListItem`
- `frontend/src/types/index.ts` — Added `ROLE_BASED` to `SignupMethod` enum, `ROLE_MATCHED = 16000` to `ParticipantType` enum, `ROLE_BASED` entry to `SIGNUP_METHOD_INFO`, and `signup_priority_role_ids?: string[] | null` to `GameTemplate` and `TemplateCreateRequest` interfaces
- `tests/unit/shared/utils/test_participant_sorting.py` — Added `test_role_matched_participant_type_value`
- `tests/unit/shared/models/test_signup_method.py` — Added `test_role_based_signup_method`; updated `test_signup_method_members` count from 2 to 3; added `import pytest`
- `tests/unit/schemas/test_schemas_template_schema.py` — Added three tests for `signup_priority_role_ids` acceptance, max-8 enforcement, and `TemplateResponse` exposure; added `import pytest`

## Removed

None.

## Divergences from Plan

None.

---
applyTo: ".copilot-tracking/changes/20251218-bot-manager-host-field-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Bot Manager Host Field Override

## Overview

Add editable host field to game creation form for bot managers only, allowing them to specify any user as game host while maintaining current user as default host for regular users.

## Objectives

- Enable bot managers to specify game host via editable field during game creation
- Keep host field completely hidden for regular users (no UI changes for non-managers)
- Maintain backward compatibility (empty/missing host defaults to current user)
- Enforce authorization: only bot managers can override host
- Validate host mentions with disambiguation support
- Verify host has permissions for selected template

## Research Summary

### Project Files

- [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Game creation form component (currently no host field)
- [services/api/routes/games.py](services/api/routes/games.py#L70-L88) - Game creation endpoint (host set from current_user.user.id)
- [services/api/services/games.py](services/api/services/games.py#L130-L210) - Game service layer with host validation logic
- [shared/schemas/game.py](shared/schemas/game.py#L30-L68) - GameCreateRequest schema (currently no host field)

### External References

- #file:../research/20251218-host-field-visibility-research.md - Comprehensive analysis of current host behavior, permission system, and implementation patterns
- #file:../../.github/instructions/api-authorization.instructions.md - Authorization patterns for route protection and permission checks
- #file:../../.github/instructions/reactjs.instructions.md - React/TypeScript patterns for forms and conditional rendering

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript development standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Code commenting guidelines

## Implementation Checklist

### [x] Phase 1: Backend Schema and Permission Validation

- [x] Task 1.1: Update GameCreateRequest schema to accept optional host field
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 15-27)

- [x] Task 1.2: Add bot manager authorization check to GameService.create_game
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 29-44)

- [x] Task 1.3: Implement host mention resolution and validation
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 46-63)

- [x] Task 1.4: Add host permission validation (template allowed_host_role_ids)
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 65-77)

### [x] Phase 2: Frontend Bot Manager Detection and Conditional UI

- [x] Task 2.1: Add bot manager detection to GameForm component
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 81-96)

- [x] Task 2.2: Add conditional host field to GameForm (bot managers only)
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 98-115)

- [x] Task 2.3: Update form submission to include host only for bot managers
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 117-130)

- [x] Task 2.4: Handle host validation errors and disambiguation
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 132-145)

### [x] Phase 3: Testing and Validation

- [x] Task 3.1: Add backend unit tests for host validation logic
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 149-167)

- [x] Task 3.2: Add frontend tests for conditional rendering
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 169-183)

- [x] Task 3.3: Add integration tests for end-to-end workflows
  - Details: .copilot-tracking/details/20251218-bot-manager-host-field-details.md (Lines 185-201)
### [x] Phase 3: Testing and Validation
## Dependencies

- Existing ParticipantResolver for mention resolution (shared/discord/participant_resolver.py)
- Existing RoleService for bot manager permission checks (services/api/auth/roles.py)
- Existing ValidationError handling for disambiguation (shared/schemas/errors.py)
- React TextField component for form input (Material-UI)

## Success Criteria

- Bot managers see editable host field in game creation form
- Regular users see NO host field (form identical to current state)
- Empty/missing host defaults to current user (backward compatible)
- Bot managers can successfully create games hosted by other users
- Regular users attempting to specify host via API receive authorization error
- Invalid host mentions return validation errors with disambiguation
- Host lacking template permissions returns clear error message
- All existing tests pass
- New tests cover all bot manager host override scenarios

<!-- markdownlint-disable-file -->

# Task Details: Bot Manager Host Field Override

## Research Reference

**Source Research**: #file:../research/20251218-host-field-visibility-research.md

## Phase 1: Backend Schema and Permission Validation

### Task 1.1: Update GameCreateRequest schema to accept optional host field

Add optional `host` field to GameCreateRequest schema in shared/schemas/game.py to accept host mention string.

- **Files**:
  - [shared/schemas/game.py](shared/schemas/game.py#L30-L68) - Add `host: str | None = None` field to GameCreateRequest class
- **Success**:
  - GameCreateRequest accepts optional host parameter
  - Field defaults to None for backward compatibility
  - OpenAPI schema reflects optional host field
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 14-27) - Current schema analysis showing no host field
  - #file:../research/20251218-host-field-visibility-research.md (Lines 86-101) - Backend logic requirements for host field handling
- **Dependencies**:
  - None (foundational change)

### Task 1.2: Add bot manager authorization check to GameService.create_game

Modify GameService.create_game method to check if requester is bot manager when host field is provided.

- **Files**:
  - [services/api/services/games.py](services/api/services/games.py#L130-L210) - Add authorization check for host field usage
  - [services/api/auth/roles.py](services/api/auth/roles.py) - Use existing check_bot_manager_permission method
- **Success**:
  - If host provided and requester not bot manager → raise authorization error
  - If host empty/None → skip check (uses current user, existing behavior)
  - Bot managers can specify host without error
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 86-101) - Backend validation logic pseudocode
  - #file:../research/20251218-host-field-visibility-research.md (Lines 59-74) - Bot manager permission check pattern
- **Dependencies**:
  - Task 1.1 completion (schema must accept host field)

### Task 1.3: Implement host mention resolution and validation

Add host mention resolution using existing ParticipantResolver in GameService.create_game.

- **Files**:
  - [services/api/services/games.py](services/api/services/games.py#L130-L210) - Add host resolution logic before game creation
  - [shared/discord/participant_resolver.py](shared/discord/participant_resolver.py) - Reuse existing mention resolution logic
- **Success**:
  - Valid host mention resolves to user ID
  - Ambiguous mentions return ValidationError with disambiguation suggestions
  - Invalid mentions return clear error message
  - Empty/None host skips resolution (uses current user)
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 86-101) - Host resolution workflow
  - #file:../research/20251218-host-field-visibility-research.md (Lines 38-49) - Existing participant resolution patterns
- **Dependencies**:
  - Task 1.2 completion (authorization must pass before resolution)

### Task 1.4: Add host permission validation (template allowed_host_role_ids)

Validate resolved host has permissions to host games with selected template.

- **Files**:
  - [services/api/services/games.py](services/api/services/games.py#L130-L210) - Add host permission check after resolution
- **Success**:
  - Host without allowed_host_role_ids → error "User cannot host games with this template"
  - Host with valid role IDs → passes validation
  - Empty allowed_host_role_ids list → all users can host (existing behavior)
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 29-36) - Host permission check from existing code
- **Dependencies**:
  - Task 1.3 completion (host must be resolved before permission check)

## Phase 2: Frontend Bot Manager Detection and Conditional UI

### Task 2.1: Add bot manager detection to GameForm component

Add logic to detect if current user is bot manager and store in component state.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Add bot manager detection on component mount
  - [frontend/src/contexts/AuthContext.tsx](frontend/src/contexts/AuthContext.tsx) - Use existing user/guild context data
- **Success**:
  - Component has `isBotManager` boolean state
  - State correctly reflects user's bot manager status
  - Detection happens on component mount and guild/user change
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 103-114) - Frontend bot manager detection requirements
  - #file:../research/20251218-host-field-visibility-research.md (Lines 59-74) - Permission system overview
- **Dependencies**:
  - None (independent frontend change)

### Task 2.2: Add conditional host field to GameForm (bot managers only)

Add host TextField to GameForm component that renders only for bot managers.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Add conditional host field after title field
- **Success**:
  - Bot managers see editable host TextField
  - Regular users do NOT see host field at all
  - Field has placeholder with current user's display name
  - Helper text: "Game host (@mention or username). Leave empty to host yourself."
  - Field value stored in form state as optional string
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 116-128) - Frontend host field rendering specifications
  - #file:../research/20251218-host-field-visibility-research.md (Lines 51-57) - TextField patterns from existing code
- **Dependencies**:
  - Task 2.1 completion (needs isBotManager state)

### Task 2.3: Update form submission to include host only for bot managers

Modify form submission logic to include host field only when user is bot manager and field has value.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Update onSubmit handler
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Update game creation API call
- **Success**:
  - Bot managers with empty host field → host not included in request (defaults to current user)
  - Bot managers with non-empty host field → host included in request
  - Regular users → host never included in request (undefined/not sent)
  - API receives correct payload for each scenario
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 130-141) - Form submission handling requirements
- **Dependencies**:
  - Task 2.2 completion (host field must exist in form)

### Task 2.4: Handle host validation errors and disambiguation

Add error handling for host field validation errors from backend.

- **Files**:
  - [frontend/src/components/GameForm.tsx](frontend/src/components/GameForm.tsx) - Add host field error display
  - [frontend/src/pages/CreateGame.tsx](frontend/src/pages/CreateGame.tsx) - Handle 422 validation errors for host
- **Success**:
  - Invalid host mention → displays error message under field
  - Ambiguous host → displays disambiguation suggestions
  - Authorization error → displays clear message
  - Form preserves user input on validation error
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 143-154) - Validation error handling patterns
- **Dependencies**:
  - Task 2.3 completion (submission must send host to receive errors)

## Phase 3: Testing and Validation

### Task 3.1: Add backend unit tests for host validation logic

Create comprehensive unit tests for GameService host validation logic.

- **Files**:
  - [tests/services/test_games.py](tests/services/test_games.py) - Add new test cases for host validation
- **Success**:
  - Test: Empty host defaults to current user (backward compatible)
  - Test: Regular user attempts host override → authorization error
  - Test: Bot manager specifies valid host → creates game with that host
  - Test: Bot manager specifies invalid host → validation error
  - Test: Bot manager specifies host without template permissions → permission error
  - Test: Bot manager leaves host empty → defaults to them
  - All tests pass
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 156-181) - Testing requirements and success criteria
- **Dependencies**:
  - Phase 1 completion (backend implementation must exist)

### Task 3.2: Add frontend tests for conditional rendering

Add unit tests for GameForm component bot manager conditional rendering.

- **Files**:
  - [frontend/src/components/GameForm.test.tsx](frontend/src/components/GameForm.test.tsx) - Add new test cases
- **Success**:
  - Test: Bot manager sees host field
  - Test: Regular user does NOT see host field
  - Test: Host field renders with correct props (placeholder, helper text)
  - Test: Form submission includes host only for bot managers with value
  - All tests pass
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 183-195) - Frontend testing requirements
- **Dependencies**:
  - Phase 2 completion (frontend implementation must exist)

### Task 3.3: Add integration tests for end-to-end workflows

Create integration tests for complete host override workflows.

- **Files**:
  - [tests/integration/test_game_creation.py](tests/integration/test_game_creation.py) - Add end-to-end test scenarios
- **Success**:
  - Test: Bot manager creates game with different host → game created with correct host
  - Test: Bot manager creates game with empty host → game created with bot manager as host
  - Test: Regular user creates game (no host sent) → game created with regular user as host
  - Test: Regular user attempts API call with host → authorization error
  - Test: Host validation errors propagate correctly to frontend
  - All tests pass
- **Research References**:
  - #file:../research/20251218-host-field-visibility-research.md (Lines 197-213) - Integration testing requirements and success criteria
- **Dependencies**:
  - Phase 1 and Phase 2 completion (full stack must be implemented)

## Dependencies

- Existing ParticipantResolver for mention resolution
- Existing RoleService for bot manager permission checks
- Existing ValidationError handling for disambiguation
- React TextField component (Material-UI)

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

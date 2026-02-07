---
applyTo: '**/.copilot-tracking/changes/*.md'
description: 'Instructions for implementing task plans with progressive tracking and change record - Brought to you by microsoft/edge-ai'
---

# Task Plan Implementation Instructions

You will implement your specific task plan located in `.copilot-tracking/plans/**` and `.copilot-tracking/details/**`. Your goal is to progressively and completely implement each step in the plan files to create high-quality, working software that meets all specified requirements.

Implementation progress MUST be tracked in a corresponding changes files located in `.copilot-tracking/changes/**`.

## Core Implementation Process

### 1. Plan Analysis and Preparation

**MUST complete before starting implementation:**

- **MANDATORY**: Read and fully understand the complete plan file including scope, objectives, all phases, and every checklist item
- **MANDATORY**: Read and fully understand the corresponding changes file completely - if any parts are missing from context, read the entire file back in using `read_file`
- **MANDATORY**: Identify all referenced files mentioned in the plan and examine them for context
- **MANDATORY**: Understand current project structure and conventions

### 2. Systematic Implementation Process

**Implement each task in the plan systematically:**

1. **Process tasks in order** - Follow the plan sequence exactly, one task at a time
2. **MANDATORY before implementing any task:**
   - **ALWAYS ensure implementation is associated with a specific task from the plan**
   - **ALWAYS read the entire details section for that task from the associated details markdown file in `.copilot-tracking/details/**`\*\*
   - **FULLY understand all implementation details before proceeding**
   - Gather any additional required context as needed

3. **Implement the task using TDD methodology:**
   - **RED Phase (if creating new function/component):**
     - Create stub with NotImplementedError (Python) or throw Error() (TypeScript/JavaScript)
     - Write tests expecting the error to be thrown
     - Run tests to verify they fail correctly

   - **GREEN Phase (if implementing functionality):**
     - Replace error with minimal working implementation
     - Run tests to verify they pass

   - **REFACTOR Phase (if improving code):**
     - Improve implementation for edge cases and clarity
     - Add comprehensive tests
     - Keep all tests passing

   - Follow existing code patterns and conventions from the workspace
   - Create working functionality that meets all task requirements specified in the details
   - Include proper error handling, documentation, and follow best practices
   - **Verify all tests pass before marking task complete**

4. **Mark task complete and update changes tracking:**
   - Update plan file: change `[ ]` to `[x]` for completed task
   - **MANDATORY after completing EVERY task**: Update the changes file by appending to the appropriate Added, Modified, or Removed sections with relative file paths and one-sentence summary of what was implemented
   - **MANDATORY**: If any changes diverge from the task plan and details, specifically call out within the relevant section that the change was made outside of the plan and include the specific reason
   - If ALL tasks in a phase are complete `[x]`, mark the phase header as complete `[x]`

### 3. Implementation Quality Standards

**Every implementation MUST:**

- **Follow Test-Driven Development (TDD)**: All new code must follow the Red-Green-Refactor cycle. See #file:../../.github/instructions/test-driven-development.instructions.md
- **Write tests BEFORE implementation**: Create function stubs with NotImplementedError, write failing tests, then implement
- Follow existing workspace patterns and conventions (check `copilot/` folder for standards)
- Implement complete, working functionality that meets all task requirements
- Include appropriate error handling and validation
- Use consistent naming conventions and code structure from the workspace
- Add necessary documentation and comments for complex logic
- Ensure compatibility with existing systems and dependencies
- Verify all tests pass before marking tasks complete

### 4. Continuous Progress and Validation

**After implementing each task:**

1. Validate the changes made against the task requirements from the details file
2. Fix any problems before moving to the next task
3. **MANDATORY**: Update the plan file to mark completed tasks `[x]`
4. **MANDATORY after EVERY task completion**: Update the changes file by appending to Added, Modified, or Removed sections with relative file paths and one-sentence summary of what was implemented
5. Stop and return control to the user so they can review progress

**Continue until:**

- All tasks in the plan are marked complete `[x]`
- All specified files have been created or updated with working code
- All success criteria from the plan have been verified

### 5. Reference Gathering Guidelines

**When gathering external references:**

- Focus on practical implementation examples over theoretical documentation
- Validate that external sources contain actual usable patterns
- Adapt external patterns to match workspace conventions and standards

**When implementing from references:**

- Follow workspace patterns and conventions first, external patterns second
- Implement complete, working functionality rather than just examples
- Ensure all dependencies and configurations are properly integrated
- Ensure implementations work within the existing project structure

### 6. Completion and Documentation

**Implementation is complete when:**

- All plan tasks are marked complete `[x]`
- All specified files exist with working code
- All success criteria from the plan are verified
- No implementation errors remain

**Final step - update changes file with release summary:**

- Add Release Summary section only after ALL phases are marked complete `[x]`
- Document complete file inventory and overall implementation summary for release documentation

### 7. Problem Resolution

**When encountering implementation issues:**

- Document the specific problem clearly
- Try alternative approaches or search terms
- Use workspace patterns as fallback when external references fail
- Continue with available information rather than stopping completely
- Note any unresolved issues in the plan file for future reference

## TDD Phase Structure Templates

### Template for New Feature Implementation (Python)

**Every new feature MUST follow this TDD structure:**

```markdown
### Phase N: Feature Name (e.g., Game Capacity Validation)

- [ ] Task N.1: Create stub function with NotImplementedError
  - Create function signature with complete type hints and docstring
  - Raise NotImplementedError("function_name not yet implemented")
  - Add to appropriate module
  - Details: [details file reference]

- [ ] Task N.2: Write failing unit tests
  - Test happy path with pytest.raises(NotImplementedError, match="not yet implemented")
  - Test edge cases expecting NotImplementedError
  - Test error conditions
  - Document expected behavior in test docstrings
  - Run tests to verify they fail correctly (RED phase)
  - Details: [details file reference]

- [ ] Task N.3: Implement minimal working solution
  - Replace NotImplementedError with implementation
  - Use simplest approach that makes tests pass
  - Run tests to verify they pass (GREEN phase)
  - Details: [details file reference]

- [ ] Task N.4: Update tests to verify behavior
  - Remove pytest.raises(NotImplementedError) from tests
  - Add actual assertions for correct behavior
  - Verify all tests pass with real implementation
  - Details: [details file reference]

- [ ] Task N.5: Refactor and add comprehensive tests
  - Improve implementation for edge cases and performance
  - Add additional tests for boundary conditions
  - Add integration tests if needed
  - Refactor for clarity while keeping tests green (REFACTOR phase)
  - Verify full test suite passes
  - Details: [details file reference]
```

### Template for API Endpoint Implementation

```markdown
### Phase N: API Endpoint Feature (e.g., POST /games/{game_id}/join)

- [ ] Task N.1: Create endpoint stub returning 501 Not Implemented
  - Add route with proper type hints and dependencies
  - Return JSONResponse({"detail": "Not implemented"}, status_code=501)
  - Details: [details file reference]

- [ ] Task N.2: Write failing integration tests
  - Test endpoint returns 501
  - Test authentication requirements
  - Test authorization checks (expecting 501 after auth succeeds)
  - Details: [details file reference]

- [ ] Task N.3: Implement service layer with TDD
  - Create service method stub with NotImplementedError
  - Write service layer unit tests (expecting NotImplementedError)
  - Implement service method
  - Update service tests to verify behavior
  - Details: [details file reference]

- [ ] Task N.4: Wire service to endpoint
  - Remove 501 response from endpoint
  - Call service method from endpoint
  - Update integration tests to verify full flow
  - Details: [details file reference]

- [ ] Task N.5: Add comprehensive error handling tests
  - Test validation errors (400, 422)
  - Test authorization failures (403, 404)
  - Test edge cases and race conditions
  - Details: [details file reference]
```

### Template for React Component Implementation

```markdown
### Phase N: React Component Feature (e.g., GameCard Component)

- [ ] Task N.1: Create component stub
  - Create component that throws Error('ComponentName not yet implemented')
  - Define TypeScript interfaces for props
  - Details: [details file reference]

- [ ] Task N.2: Write failing component tests
  - Test component throws error when rendered
  - Test with various prop combinations (expecting errors)
  - Document expected rendering behavior in tests
  - Run tests to verify they fail correctly (RED phase)
  - Details: [details file reference]

- [ ] Task N.3: Implement minimal rendering
  - Replace error throw with basic component structure
  - Render props to satisfy tests
  - Run tests to verify they pass (GREEN phase)
  - Details: [details file reference]

- [ ] Task N.4: Update tests to verify rendering
  - Remove error expectation from tests
  - Add assertions for rendered content
  - Test user interactions and event handlers
  - Details: [details file reference]

- [ ] Task N.5: Refactor and enhance component
  - Add styling and accessibility features
  - Improve component structure and performance
  - Add tests for edge cases and accessibility
  - Verify all tests pass
  - Details: [details file reference]
```

### Template for Database Migration

```markdown
### Phase N: Database Schema Change (e.g., Add capacity column)

- [ ] Task N.1: Create migration file stub
  - Generate Alembic migration file
  - Add upgrade() and downgrade() stubs with pass statements
  - Details: [details file reference]

- [ ] Task N.2: Write migration tests
  - Test upgrade operation (expecting no changes yet)
  - Test downgrade operation (expecting no changes yet)
  - Test idempotency
  - Details: [details file reference]

- [ ] Task N.3: Implement migration upgrade
  - Add column/table creation in upgrade()
  - Run migration test to verify upgrade works
  - Details: [details file reference]

- [ ] Task N.4: Implement migration downgrade
  - Add column/table removal in downgrade()
  - Verify upgrade → downgrade → upgrade cycle works
  - Details: [details file reference]

- [ ] Task N.5: Update model and add integration tests
  - Update SQLAlchemy model with new column
  - Add integration tests using real database
  - Verify queries work with new schema
  - Details: [details file reference]
```

## Implementation Workflow

```
1. Read and fully understand plan file and all checklists completely
2. Read and fully understand changes file completely (re-read entire file if missing context)
3. For each unchecked task:
   a. Read entire details section for that task from details markdown file
   b. Fully understand all implementation requirements

   c. FOLLOW TDD WORKFLOW:
      - If task creates new function/component:
        * Create stub with NotImplementedError or throw Error()
        * Write failing tests expecting NotImplementedError/Error
        * Verify tests fail correctly (RED phase)
      - If task implements functionality:
        * Implement minimal working solution
        * Verify tests pass (GREEN phase)
      - If task refactors:
        * Improve implementation while keeping tests green
        * Add edge case tests (REFACTOR phase)

   d. Implement task with working code following workspace patterns and TDD
   e. Validate implementation meets task requirements and all tests pass
   f. Mark task complete [x] in plan file
   g. Update changes file with Added, Modified, or Removed entries
   h. Call out any divergences from plan/details within relevant sections with specific reasons

4. Repeat until all tasks complete
5. Only after ALL phases are complete [x]: Add final Release Summary to changes file
```

## Success Criteria

Implementation is complete when:

- ✅ All plan tasks are marked complete `[x]`
- ✅ All specified files contain working code that follows TDD methodology
- ✅ Code follows workspace patterns and conventions
- ✅ All functionality works as expected within the project
- ✅ All unit tests pass (written before implementation using TDD)
- ✅ All integration and e2e tests pass
- ✅ Test coverage is comprehensive (happy path, edge cases, error conditions)
- ✅ Changes file is updated after every task completion with Added, Modified, or Removed entries
- ✅ Changes file documents all phases with detailed release-ready documentation and final release summary

## TDD Implementation Examples

### Example 1: Python Function Implementation

**Task Plan Structure:**

```markdown
### Phase 1: Waitlist Promotion Logic

- [ ] Task 1.1: Create calculate_next_promotion stub
- [ ] Task 1.2: Write failing tests for promotion calculation
- [ ] Task 1.3: Implement promotion logic
- [ ] Task 1.4: Update tests to verify behavior
- [ ] Task 1.5: Add edge case tests and refactor
```

**Implementation Sequence:**

**Task 1.1 - Create Stub:**

```python
# services/api/services/participant_service.py
def calculate_next_promotion(
    game: GameSession,
    participants: list[Participant]
) -> Participant | None:
    """Calculate which waitlist participant should be promoted.

    Args:
        game: The game session
        participants: List of all participants

    Returns:
        Participant to promote, or None if no promotion available

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("calculate_next_promotion not yet implemented")
```

**Task 1.2 - Write Failing Tests:**

```python
# tests/unit/services/test_participant_service.py
import pytest

def test_calculate_next_promotion_with_waitlist():
    """Test promotion with available waitlist participants."""
    game = GameSession(max_participants=3)
    participants = [
        Participant(status=ParticipantStatus.CONFIRMED, order=1),
        Participant(status=ParticipantStatus.CONFIRMED, order=2),
        Participant(status=ParticipantStatus.WAITLIST, order=3),
    ]

    with pytest.raises(NotImplementedError, match="not yet implemented"):
        result = calculate_next_promotion(game, participants)
        # After implementation: assert result.order == 3
```

**Task 1.3 - Implement Solution:**

```python
def calculate_next_promotion(
    game: GameSession,
    participants: list[Participant]
) -> Participant | None:
    """Calculate which waitlist participant should be promoted."""
    confirmed = [p for p in participants if p.status == ParticipantStatus.CONFIRMED]
    if len(confirmed) >= game.max_participants:
        return None

    waitlist = [p for p in participants if p.status == ParticipantStatus.WAITLIST]
    return min(waitlist, key=lambda p: p.order) if waitlist else None
```

**Task 1.4 - Update Tests:**

```python
def test_calculate_next_promotion_with_waitlist():
    """Test promotion with available waitlist participants."""
    game = GameSession(max_participants=3)
    participants = [
        Participant(status=ParticipantStatus.CONFIRMED, order=1),
        Participant(status=ParticipantStatus.CONFIRMED, order=2),
        Participant(status=ParticipantStatus.WAITLIST, order=3),
    ]

    result = calculate_next_promotion(game, participants)
    assert result is not None
    assert result.order == 3
    assert result.status == ParticipantStatus.WAITLIST
```

**Task 1.5 - Add Edge Cases:**

```python
def test_calculate_next_promotion_no_waitlist():
    """Test when no waitlist participants exist."""
    game = GameSession(max_participants=5)
    participants = [Participant(status=ParticipantStatus.CONFIRMED, order=1)]

    result = calculate_next_promotion(game, participants)
    assert result is None

def test_calculate_next_promotion_game_full():
    """Test when game is at capacity."""
    game = GameSession(max_participants=2)
    participants = [
        Participant(status=ParticipantStatus.CONFIRMED, order=1),
        Participant(status=ParticipantStatus.CONFIRMED, order=2),
        Participant(status=ParticipantStatus.WAITLIST, order=3),
    ]

    result = calculate_next_promotion(game, participants)
    assert result is None
```

### Example 2: React Component Implementation

**Task Plan Structure:**

```markdown
### Phase 2: GameCapacityBadge Component

- [ ] Task 2.1: Create component stub
- [ ] Task 2.2: Write failing component tests
- [ ] Task 2.3: Implement basic rendering
- [ ] Task 2.4: Update tests to verify rendering
- [ ] Task 2.5: Add styling and accessibility
```

**Task 2.1 - Create Stub:**

```typescript
// frontend/src/components/GameCapacityBadge.tsx
interface GameCapacityBadgeProps {
  current: number;
  maximum: number;
}

export function GameCapacityBadge({ current, maximum }: GameCapacityBadgeProps) {
  throw new Error('GameCapacityBadge not yet implemented');
}
```

**Task 2.2 - Write Failing Tests:**

```typescript
// frontend/src/components/GameCapacityBadge.test.tsx
import { render } from '@testing-library/react';
import { GameCapacityBadge } from './GameCapacityBadge';

describe('GameCapacityBadge', () => {
  it('renders capacity information', () => {
    expect(() => render(<GameCapacityBadge current={2} maximum={5} />))
      .toThrow('not yet implemented');
    // After implementation: expect(screen.getByText('2/5')).toBeInTheDocument();
  });
});
```

**Task 2.3 - Implement Basic Rendering:**

```typescript
export function GameCapacityBadge({ current, maximum }: GameCapacityBadgeProps) {
  return <span>{current}/{maximum}</span>;
}
```

**Task 2.4 - Update Tests:**

```typescript
it('renders capacity information', () => {
  render(<GameCapacityBadge current={2} maximum={5} />);
  expect(screen.getByText('2/5')).toBeInTheDocument();
});

it('shows full capacity visually', () => {
  render(<GameCapacityBadge current={5} maximum={5} />);
  const badge = screen.getByText('5/5');
  expect(badge).toBeInTheDocument();
});
```

**Task 2.5 - Add Styling:**

```typescript
export function GameCapacityBadge({ current, maximum }: GameCapacityBadgeProps) {
  const isFull = current >= maximum;
  const percentage = (current / maximum) * 100;

  return (
    <Chip
      label={`${current}/${maximum}`}
      color={isFull ? 'error' : percentage > 75 ? 'warning' : 'success'}
      size="small"
      aria-label={`${current} of ${maximum} slots filled`}
    />
  );
}
```

### Example 3: API Endpoint with Service Layer

**Task Plan Structure:**

```markdown
### Phase 3: Leave Game Endpoint

- [ ] Task 3.1: Create endpoint stub returning 501
- [ ] Task 3.2: Write failing integration tests
- [ ] Task 3.3: Create service method with TDD
- [ ] Task 3.4: Wire service to endpoint
- [ ] Task 3.5: Add comprehensive error tests
```

**Task 3.1 - Endpoint Stub:**

```python
@router.delete("/games/{game_id}/participants/me")
async def leave_game(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Leave a game session."""
    return JSONResponse(
        {"detail": "Not implemented"},
        status_code=501
    )
```

**Task 3.2 - Integration Tests:**

```python
async def test_leave_game_returns_not_implemented(authenticated_client):
    response = await authenticated_client.delete("/api/games/123/participants/me")
    assert response.status_code == 501
```

**Task 3.3 - Service Layer TDD:**

```python
# Service stub
async def leave_game(game_id: str, user_id: str, db: AsyncSession) -> None:
    raise NotImplementedError("leave_game not yet implemented")

# Service tests
async def test_leave_game_service():
    with pytest.raises(NotImplementedError):
        await leave_game("game-123", "user-456", mock_db)

# Service implementation
async def leave_game(game_id: str, user_id: str, db: AsyncSession) -> None:
    participant = await db.execute(
        select(Participant).where(
            Participant.game_id == game_id,
            Participant.user_id == user_id
        )
    )
    if participant := participant.scalar_one_or_none():
        await db.delete(participant)
        await db.flush()
```

**Task 3.4 - Wire to Endpoint:**

```python
@router.delete("/games/{game_id}/participants/me")
async def leave_game(
    game_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Leave a game session."""
    game = await verify_game_access(game_id, current_user, db)
    await participant_service.leave_game(game_id, current_user.discord_id, db)
    await db.commit()
    return Response(status_code=204)
```

**Task 3.5 - Error Tests:**

```python
async def test_leave_game_not_participant(authenticated_client):
    """Test leaving game when not a participant."""
    response = await authenticated_client.delete("/api/games/123/participants/me")
    assert response.status_code == 404

async def test_leave_game_unauthorized(unauthenticated_client):
    """Test leaving game without authentication."""
    response = await unauthenticated_client.delete("/api/games/123/participants/me")
    assert response.status_code == 401
```

## Template Changes File

Use the following as a template for the changes file that tracks implementation progress for releases.
Replace `{{ }}` with appropriate values. Create this file in `./.copilot-tracking/changes/` with filename: `YYYYMMDD-NN-task-description-changes.md` (where NN is a 2-digit sequence number starting at 01 and incrementing: 01, 02, 03, etc.)

**IMPORTANT**: Update this file after EVERY task completion by appending to Added, Modified, or Removed sections.
**MANDATORY**: Always include the following at the top of the changes file: `<!-- markdownlint-disable-file -->`

<!-- <changes-template> -->

```markdown
<!-- markdownlint-disable-file -->

# Release Changes: {{task name}}

**Related Plan**: {{plan-file-name}}
**Implementation Date**: {{YYYY-MM-DD}}

## Summary

{{Brief description of the overall changes made for this release}}

## Changes

### Added

- {{relative-file-path}} - {{one sentence summary of what was implemented}}

### Modified

- {{relative-file-path}} - {{one sentence summary of what was changed}}

### Removed

- {{relative-file-path}} - {{one sentence summary of what was removed}}

## Release Summary

**Total Files Affected**: {{number}}

### Files Created ({{count}})

- {{file-path}} - {{purpose}}

### Files Modified ({{count}})

- {{file-path}} - {{changes-made}}

### Files Removed ({{count}})

- {{file-path}} - {{reason}}

### Dependencies & Infrastructure

- **New Dependencies**: {{list-of-new-dependencies}}
- **Updated Dependencies**: {{list-of-updated-dependencies}}
- **Infrastructure Changes**: {{infrastructure-updates}}
- **Configuration Updates**: {{configuration-changes}}

### Deployment Notes

{{Any specific deployment considerations or steps}}
```

<!-- </changes-template> -->

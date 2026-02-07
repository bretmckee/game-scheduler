---
description: 'Test-Driven Development (TDD) methodology and workflow for all code implementation'
applyTo: '**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx'
---

# Test-Driven Development (TDD) Instructions

## Core TDD Principle

**ALL new functionality MUST follow the Red-Green-Refactor cycle. Write tests BEFORE writing implementation code.**

## TDD Workflow (Red-Green-Refactor)

### Step 1: RED - Create Failing Test Infrastructure

**ALWAYS start by creating the interface with NotImplementedError:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session.

    Args:
        game: The game session to calculate capacity for
        participants: Current list of participants

    Returns:
        Number of available slots

    Raises:
        NotImplementedError: Function not yet implemented
    """
    raise NotImplementedError("calculate_game_capacity not yet implemented")
```

```typescript
export function calculateGameCapacity(game: GameSession, participants: Participant[]): number {
  throw new Error('calculateGameCapacity not yet implemented');
}
```

**Then write tests for the desired behavior (they will naturally fail against the stub):**

```python
import pytest

def test_calculate_game_capacity_with_available_slots():
    """Test capacity calculation when slots are available."""
    game = GameSession(max_participants=5)
    participants = [Participant(), Participant()]

    result = calculate_game_capacity(game, participants)
    assert result == 3
```

```typescript
import { describe, it, expect } from 'vitest';

describe('calculateGameCapacity', () => {
  it('should calculate available slots correctly', () => {
    const game = { maxParticipants: 5 };
    const participants = [{}, {}];

    const result = calculateGameCapacity(game, participants);
    expect(result).toBe(3);
  });
});
```

**Run tests to verify they fail correctly (stub will throw NotImplementedError):**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python - will show NotImplementedError)
- `npm test -- test_game_capacity` (TypeScript - will show Error: not yet implemented)

### Step 2: GREEN - Implement Minimal Working Solution

**Remove NotImplementedError and implement the simplest solution that makes tests pass:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session."""
    return game.max_participants - len(participants)
```

**Run tests to verify they pass:**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python)
- `npm test -- test_game_capacity` (TypeScript)
- Tests should now pass - the implementation satisfies the test assertions
- No test changes needed - tests were written correctly from the start

### Step 3: REFACTOR - Improve Implementation

**Only after tests pass, refactor for quality:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session.

    Accounts for confirmed participants only, excluding waitlist.
    """
    confirmed_count = sum(1 for p in participants if p.status == ParticipantStatus.CONFIRMED)
    return max(0, game.max_participants - confirmed_count)
```

**Add additional tests for edge cases:**

```python
def test_calculate_game_capacity_at_full_capacity():
    """Test that capacity returns 0 when game is full."""
    game = GameSession(max_participants=3)
    participants = [Participant() for _ in range(3)]

    result = calculate_game_capacity(game, participants)
    assert result == 0

def test_calculate_game_capacity_over_capacity():
    """Test that capacity handles over-booking gracefully."""
    game = GameSession(max_participants=2)
    participants = [Participant() for _ in range(5)]

    result = calculate_game_capacity(game, participants)
    assert result == 0  # Should not return negative
```

**Run full test suite to ensure refactoring didn't break anything.**

## TDD in Task Plans

### Phase Structure with TDD

Every implementation phase MUST follow this pattern:

```markdown
### Phase N: Feature Name

- [ ] Task N.1: Create stub function with NotImplementedError
  - Create function signature with complete type hints
  - Add comprehensive docstring
  - Raise NotImplementedError with descriptive message
  - Details: [details file reference]

- [ ] Task N.2: Write failing unit tests for desired behavior
  - Test happy path with actual assertions (will fail against stub)
  - Test edge cases with expected behavior
  - Test error conditions
  - Document expected behavior in test docstrings
  - Verify tests fail correctly (stub throws NotImplementedError)
  - Details: [details file reference]

- [ ] Task N.3: Implement minimal working solution
  - Replace NotImplementedError with implementation
  - Make all tests pass
  - No test changes needed - tests already verify correct behavior
  - Details: [details file reference]

- [ ] Task N.4: Refactor and add comprehensive tests
  - Improve implementation for edge cases
  - Add integration tests if needed
  - Refactor for clarity and performance
  - Verify full test suite passes
  - Details: [details file reference]
```

### ❌ INCORRECT Phase Structure (Testing Separated from Implementation)

**DO NOT structure phases like this:**

```markdown
### Phase 1: Implement Game Capacity Feature

- [ ] Create calculate_game_capacity function
- [ ] Add capacity check to join handler
- [ ] Update game model with capacity field

### Phase 2: Add Database Migration

- [ ] Create migration for capacity field
- [ ] Update schema

### Phase 3: Testing ❌ TOO LATE!

- [ ] Write unit tests for capacity calculation
- [ ] Write integration tests
```

### ✅ CORRECT Phase Structure (TDD Integrated)

```markdown
### Phase 1: Game Capacity Calculation

- [ ] Task 1.1: Create calculate_game_capacity stub
- [ ] Task 1.2: Write failing unit tests for capacity
- [ ] Task 1.3: Implement capacity calculation
- [ ] Task 1.4: Update tests to verify behavior
- [ ] Task 1.5: Refactor and add edge case tests

### Phase 2: Database Schema for Capacity

- [ ] Task 2.1: Create migration stub
- [ ] Task 2.2: Write migration tests (up/down/idempotency)
- [ ] Task 2.3: Implement migration
- [ ] Task 2.4: Verify migration tests pass
- [ ] Task 2.5: Test with real database

### Phase 3: Join Handler Integration

- [ ] Task 3.1: Create join_with_capacity_check stub
- [ ] Task 3.2: Write failing integration tests
- [ ] Task 3.3: Integrate capacity check into handler
- [ ] Task 3.4: Update tests to verify integration
- [ ] Task 3.5: Add e2e tests for full workflow
```

## TDD for Different Test Levels

### Unit Tests (Always TDD)

**Write unit tests FIRST for every function:**

1. Create stub with NotImplementedError
2. Write tests for desired behavior (they naturally fail against stub)
3. Implement function to make tests pass
4. Add edge case tests and refactor

### Integration Tests (TDD When Possible)

**For service layer and API endpoints:**

1. Create endpoint/service stub returning 501 Not Implemented
2. Write tests for desired integration behavior (they naturally fail)
3. Implement minimal functionality to make tests pass
4. Add tests for error paths and edge cases

### E2E Tests (Verify Complete Workflows)

**E2E tests can be written after integration tests pass:**

- E2E tests verify complete user workflows
- Written after unit + integration tests are green
- Test cross-service interactions and real environments
- Still follow red-green-refactor for test reliability

## TDD Quality Checklist

Before marking any implementation task complete:

- [ ] Function stub created with NotImplementedError first
- [ ] Tests for desired behavior written before implementation
- [ ] Tests verified to fail correctly against stub (red phase)
- [ ] Implementation makes tests pass (green phase)
- [ ] Refactoring performed with passing tests
- [ ] Edge cases covered with additional tests
- [ ] Full test suite passes
- [ ] No untested code paths remain

## Common TDD Patterns

### Testing Exceptions and Errors

```python
# RED: Stub that raises NotImplementedError
def validate_game_data(data: dict) -> Game:
    raise NotImplementedError("validate_game_data not yet implemented")

# RED: Test for desired exception behavior (naturally fails against stub)
def test_validate_game_throws_on_invalid_data():
    with pytest.raises(ValidationError, match="Invalid game data"):
        validate_game_data(invalid_data)

# Test fails because stub raises NotImplementedError, not ValidationError

# GREEN: After implementation, test passes
def validate_game_data(data: dict) -> Game:
    if not data.get('title'):
        raise ValidationError("Invalid game data")
    return Game(**data)

# Test now passes - ValidationError is raised as expected
```

### Testing Async Functions

```python
# RED: Async stub
async def fetch_game_from_api(game_id: int) -> Game:
    raise NotImplementedError("fetch_game_from_api not yet implemented")

# RED: Test for desired behavior (naturally fails against stub)
@pytest.mark.asyncio
async def test_fetch_game_from_api():
    game = await fetch_game_from_api(123)
    assert game.id == 123
    assert game.title is not None

# Test fails because stub raises NotImplementedError

# GREEN: After implementation
async def fetch_game_from_api(game_id: int) -> Game:
    response = await api_client.get(f"/games/{game_id}")
    return Game(**response.json())

# Test now passes - returns Game with correct attributes
```

### Testing Database Operations

```python
# RED: Stub repository method
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        raise NotImplementedError("get_by_id not yet implemented")

# RED: Test for desired behavior (naturally fails against stub)
def test_get_game_by_id(mock_db_session):
    repo = GameRepository(mock_db_session)
    game = repo.get_by_id(123)
    assert game is not None
    assert game.id == 123

# Test fails because stub raises NotImplementedError

# GREEN: After implementation
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        return self.session.query(Game).filter(Game.id == game_id).first()

# Test now passes - returns Game from database
```

## Anti-Patterns to Avoid

### ❌ Writing Implementation Before Tests

```python
# WRONG: Implementation first
def calculate_capacity(game, participants):
    return game.max_participants - len(participants)

# Then later writing tests (too late!)
def test_calculate_capacity():
    assert calculate_capacity(game, []) == 5
```

### ❌ Skipping NotImplementedError Phase

```python
# WRONG: Going straight to implementation
def calculate_capacity(game, participants):
    return game.max_participants - len(participants)
```

### ❌ Testing Implementation Details

```python
# WRONG: Testing how it works instead of what it does
def test_calculate_capacity_calls_len():
    with patch('builtins.len') as mock_len:
        calculate_capacity(game, participants)
        mock_len.assert_called_once()
```

### ❌ Separating Testing Phase from Implementation

```python
# WRONG: Plan structure
Phase 1: Implement all features
Phase 2: Write tests for features  # ❌ TOO LATE
```

## Benefits of TDD

- **Prevents bugs**: Tests catch issues before code is written
- **Better design**: Writing tests first leads to better interfaces
- **Documentation**: Tests serve as executable documentation
- **Confidence**: Refactoring is safe with comprehensive tests
- **Coverage**: TDD naturally achieves high test coverage
- **Focus**: Writing tests first clarifies requirements

## Summary

**TDD is not optional - it is the required workflow for all new code:**

1. **RED**: Create stub with NotImplementedError → Write failing tests
2. **GREEN**: Implement minimal solution → Make tests pass
3. **REFACTOR**: Improve code → Keep tests passing

**Every task plan MUST integrate tests adjacent to implementation, never as a separate later phase.**

---
description: 'Test-Driven Development (TDD) methodology and workflow for all code implementation'
applyTo: '**/*.py,**/*.ts,**/*.tsx,**/*.js,**/*.jsx'
---

# Test-Driven Development (TDD) Instructions

## Applicability

**TDD methodology applies ONLY to languages with mature unit testing frameworks:**

- ✅ **Python** (pytest, unittest)
- ✅ **TypeScript/JavaScript** (Vitest, Jest, Mocha)
- ✅ **Other languages** with established testing frameworks

**TDD does NOT apply to:**

- ❌ **Bash scripts** (no practical unit test framework)
- ❌ **Dockerfiles** (no unit test framework)
- ❌ **YAML/JSON configuration files** (no unit tests)
- ❌ **SQL migration scripts** (use integration tests instead)
- ❌ **Infrastructure-as-Code** without test frameworks

**For non-testable file types:** Create and verify functionality through integration tests, manual testing, or other appropriate validation methods.

## Core TDD Principle

**ALL new functionality in testable languages MUST follow the Red-Green-Refactor cycle. Write tests BEFORE writing implementation code.**

## TDD Workflow (Red-Green-Refactor)

### Step 1: RED - Create Stub and Failing Tests

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

**Then write tests for the ACTUAL desired behavior using expected failure markers:**

```python
import pytest

@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
def test_calculate_game_capacity_with_available_slots():
    """Test capacity calculation when slots are available."""
    game = GameSession(max_participants=5)
    participants = [Participant(), Participant()]

    result = calculate_game_capacity(game, participants)
    assert result == 3  # REAL assertion from day 1
```

```typescript
import { describe, test, expect } from 'vitest';

describe('calculateGameCapacity', () => {
  test.failing('should calculate available slots correctly', () => {
    const game = { maxParticipants: 5 };
    const participants = [{}, {}];

    const result = calculateGameCapacity(game, participants);
    expect(result).toBe(3); // REAL assertion from day 1
  });
});
```

**Run tests to verify expected failures:**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python - shows "1 xfailed")
- `npm test -- test_game_capacity` (TypeScript - shows test as expected failure)

**Key Point:** Tests contain REAL assertions for the desired behavior, just marked as expected failures. Tests are NOT modified after implementation - only the xfail marker is removed.

### Step 2: GREEN - Implement and Remove xfail Markers

**Replace NotImplementedError with the simplest solution that makes tests pass:**

```python
def calculate_game_capacity(game: GameSession, participants: list[Participant]) -> int:
    """Calculate available capacity for a game session."""
    return game.max_participants - len(participants)
```

**Remove the xfail marker from tests (no other changes to tests):**

```python
import pytest

# @pytest.mark.xfail removed - that's the ONLY change
def test_calculate_game_capacity_with_available_slots():
    """Test capacity calculation when slots are available."""
    game = GameSession(max_participants=5)
    participants = [Participant(), Participant()]

    result = calculate_game_capacity(game, participants)
    assert result == 3  # SAME assertion - unchanged
```

```typescript
import { describe, test, expect } from 'vitest';

describe('calculateGameCapacity', () => {
  test('should calculate available slots correctly', () => {
    // .failing removed
    const game = { maxParticipants: 5 };
    const participants = [{}, {}];

    const result = calculateGameCapacity(game, participants);
    expect(result).toBe(3); // SAME assertion - unchanged
  });
});
```

**Run tests to verify they now pass:**

- `uv run pytest tests/unit/test_game_capacity.py -v` (Python - shows "1 passed")
- `npm test -- test_game_capacity` (TypeScript - shows "1 passed")

**Critical:** The test assertions are NEVER modified - only the xfail/failing marker is removed.

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

- [ ] Task N.2: Write tests with real assertions marked as expected failures
  - Use @pytest.mark.xfail (Python) or test.failing (TypeScript) markers
  - Write ACTUAL assertions for desired behavior (not expecting NotImplementedError)
  - Test happy path with real expected values
  - Test edge cases with real expected behavior
  - Test error conditions
  - Document expected behavior in test docstrings
  - Verify tests show as "xfailed" or "expected failure" when run
  - Details: [details file reference]

- [ ] Task N.3: Implement solution and remove xfail markers
  - Replace NotImplementedError with minimal working implementation
  - Remove @pytest.mark.xfail or test.failing markers from tests
  - DO NOT modify test assertions - they are already correct
  - Run tests to verify they pass
  - Details: [details file reference]

- [ ] Task N.4: Refactor and add comprehensive tests
  - Improve implementation for edge cases
  - Add additional tests for boundary conditions
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
- [ ] Task 1.2: Write tests with real assertions marked xfail
- [ ] Task 1.3: Implement capacity calculation and remove xfail markers
- [ ] Task 1.4: Refactor and add edge case tests

### Phase 2: Database Schema for Capacity

- [ ] Task 2.1: Create migration stub
- [ ] Task 2.2: Write migration tests with xfail markers
- [ ] Task 2.3: Implement migration and remove xfail markers
- [ ] Task 2.4: Test with real database and add edge cases

### Phase 3: Join Handler Integration

- [ ] Task 3.1: Create join_with_capacity_check stub
- [ ] Task 3.2: Write integration tests with xfail markers
- [ ] Task 3.3: Implement handler and remove xfail markers
- [ ] Task 3.4: Add e2e tests for full workflow
```

## TDD for Different Test Levels

### Unit Tests (Always TDD)

**Write unit tests FIRST for every function:**

1. Create stub with NotImplementedError
2. Write tests with REAL assertions marked with @pytest.mark.xfail or test.failing
3. Implement function and remove xfail markers (DO NOT modify test assertions)
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

- [ ] Language is appropriate for TDD (Python, TypeScript/JavaScript, etc.)
- [ ] Function stub created with NotImplementedError first
- [ ] Tests with REAL assertions written before implementation
- [ ] Tests marked with xfail/failing markers (red phase)
- [ ] Tests verified to show as "xfailed" or "expected failure" when run
- [ ] Implementation makes tests pass (green phase)
- [ ] xfail/failing markers removed (test assertions NOT modified)
- [ ] Tests now show as "passed"
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

# RED: Test for desired exception behavior marked as xfail
@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
def test_validate_game_throws_on_invalid_data():
    with pytest.raises(ValidationError, match="Invalid game data"):
        validate_game_data(invalid_data)

# Test shows as "xfailed" - expects ValidationError but gets NotImplementedError

# GREEN: After implementation, remove xfail marker
def validate_game_data(data: dict) -> Game:
    if not data.get('title'):
        raise ValidationError("Invalid game data")
    return Game(**data)

# Remove @pytest.mark.xfail decorator - test assertions unchanged
def test_validate_game_throws_on_invalid_data():
    with pytest.raises(ValidationError, match="Invalid game data"):
        validate_game_data(invalid_data)

# Test now passes - ValidationError is raised as expected
```

### Testing Async Functions

```python
# RED: Async stub
async def fetch_game_from_api(game_id: int) -> Game:
    raise NotImplementedError("fetch_game_from_api not yet implemented")

# RED: Test for desired behavior marked as xfail
@pytest.mark.asyncio
@pytest.mark.xfail(reason="Function not yet implemented", strict=True)
async def test_fetch_game_from_api():
    game = await fetch_game_from_api(123)
    assert game.id == 123  # REAL assertion from day 1
    assert game.title is not None

# Test shows as "xfailed"

# GREEN: Implement and remove xfail marker
async def fetch_game_from_api(game_id: int) -> Game:
    response = await api_client.get(f"/games/{game_id}")
    return Game(**response.json())

# Remove @pytest.mark.xfail decorator only
@pytest.mark.asyncio
async def test_fetch_game_from_api():
    game = await fetch_game_from_api(123)
    assert game.id == 123  # SAME assertion - unchanged
    assert game.title is not None

# Test now passes - returns Game with correct attributes
```

### Testing Database Operations

```python
# RED: Stub repository method
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        raise NotImplementedError("get_by_id not yet implemented")

# RED: Test for desired behavior marked as xfail
@pytest.mark.xfail(reason="Method not yet implemented", strict=True)
def test_get_game_by_id(mock_db_session):
    repo = GameRepository(mock_db_session)
    game = repo.get_by_id(123)
    assert game is not None  # REAL assertion from day 1
    assert game.id == 123

# Test shows as "xfailed"

# GREEN: Implement and remove xfail marker
class GameRepository:
    def get_by_id(self, game_id: int) -> Game | None:
        return self.session.query(Game).filter(Game.id == game_id).first()

# Remove @pytest.mark.xfail decorator only
def test_get_game_by_id(mock_db_session):
    repo = GameRepository(mock_db_session)
    game = repo.get_by_id(123)
    assert game is not None  # SAME assertion - unchanged
    assert game.id == 123

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

**TDD is required for all testable languages (Python, TypeScript/JavaScript, etc.):**

1. **RED**: Create stub with NotImplementedError → Write tests with REAL assertions marked xfail/failing
2. **GREEN**: Implement minimal solution → Remove xfail/failing markers (DO NOT modify test assertions)
3. **REFACTOR**: Improve code → Keep tests passing

**Key principles:**

- Tests contain correct assertions from day 1
- Only xfail/failing markers are removed after implementation
- Test assertions are NEVER modified between RED and GREEN phases
- Every task plan MUST integrate tests adjacent to implementation, never as a separate later phase
- TDD only applies to languages with unit testing frameworks (not bash, Dockerfiles, YAML, etc.)

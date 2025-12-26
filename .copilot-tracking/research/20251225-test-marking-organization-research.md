<!-- markdownlint-disable-file -->
# Task Research Notes: Test Marking and Organization

## Research Executed

### Test Structure Analysis
- **Test Directory Structure**:
  - `tests/e2e/` - 16 test files (end-to-end tests)
  - `tests/integration/` - 6 test files (integration tests)
  - `tests/services/` - 51 test files (unit tests)
  - `tests/shared/` - 17 test files (unit tests)

### Current Test Execution Patterns
- **E2E Tests**:
  - Command: `docker compose --env-file env/env.e2e run --rm e2e-tests tests/e2e/ -v --tb=short`
  - Run via: `scripts/run-e2e-tests.sh`

- **Integration Tests**:
  - Command: `docker compose --env-file env/env.int run --rm integration-tests tests/integration/ -v --tb=short`
  - Run via: `scripts/run-integration-tests.sh`

### File Analysis

#### pyproject.toml
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Currently only `testpaths` is set, with no pytest markers configured.

#### tests/e2e/test_conftest.py
- Contains unit tests for E2E test fixtures
- Tests the `wait_for_db_condition` polling utility
- These are unit tests that test the E2E helper functions, not E2E tests themselves

### Key Discoveries

#### Problem 1: No Pytest Markers
- Running `pytest` from the workspace root will execute ALL tests including e2e and integration
- Users must use `--ignore=tests/e2e --ignore=tests/integration` to run only unit tests
- No markers exist to selectively run test categories

#### Problem 2: E2E Fixture Tests Mixed with E2E Tests
- `tests/e2e/test_conftest.py` contains unit tests for E2E fixtures
- When running integration tests, these shouldn't be included
- When running E2E tests from docker compose, these unit tests don't need the full E2E environment

#### Current Workarounds
- Docker compose files hardcode test paths: `tests/e2e/` and `tests/integration/`
- Shell scripts use specific docker compose configurations
- No way to run "just unit tests" without `--ignore` flags

## Recommended Approach

### Mark Only Integration and E2E Tests (Inverse Selection)

Instead of marking all tests, only mark the "special" tests that require infrastructure:
- `@pytest.mark.integration` - Integration tests requiring RabbitMQ, Postgres, Redis
- `@pytest.mark.e2e` - Full end-to-end tests requiring Discord bot and full stack
- **No marking for unit tests** - They run by default

### Configuration Changes

#### 1. Update pyproject.toml
Add marker registration (no addopts needed):

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: Integration tests requiring RabbitMQ, Postgres, Redis",
    "e2e: End-to-end tests requiring Discord bot and full stack",
]
```

#### 2. Mark Only Special Test Files (Module-Level)
- **DO NOT mark** services and shared unit tests (default behavior)
- Add `pytestmark = pytest.mark.integration` at module level for integration tests (6 files)
- Add `pytestmark = pytest.mark.e2e` at module level for e2e tests (15 files)
- Move `tests/e2e/test_conftest.py` to `tests/shared/e2e_fixtures/` (unmarked = unit test)

**Why module-level marking?**
- Each test file is homogeneous (all tests in the file are the same type)
- One line at the top of the file marks all tests
- Cleaner than decorating every individual test function
- Standard pytest practice for homogeneous test files

Example:
```python
import pytest

pytestmark = pytest.mark.integration  # Marks ALL tests in this file

def test_database_connection():
    ...

def test_rabbitmq_connection():
    ...
```

#### 3. Update Test Scripts
- E2E: `pytest -m e2e`
- Integration: `pytest -m integration`
- Unit: `pytest` (default - runs unmarked tests)
- All: `pytest -m "integration or e2e" --ignore=tests/e2e --ignore=tests/integration` (better: just use appropriate test runner)

### Implementation Plan

1. **Add marker configuration to pyproject.toml**
   - Register integration and e2e markers
   - NO addopts needed (default pytest runs unmarked unit tests)

2. **Mark only infrastructure-dependent tests**
   - **Skip marking** services and shared unit tests (68 files) - they run by default
   - Integration tests: Add `pytestmark = pytest.mark.integration` (6 files)
   - E2E tests: Add `pytestmark = pytest.mark.e2e` (15 files)

3. **Reorganize E2E fixture tests**
   - Move `tests/e2e/test_conftest.py` → `tests/shared/e2e_fixtures/test_conftest.py`
   - **Do NOT mark** (unmarked = unit test)
   - Update imports if needed

4. **Update docker compose commands**
   - E2E: Change command to `pytest -m e2e -v --tb=short`
   - Integration: Change command to `pytest -m integration -v --tb=short`

5. **Update shell scripts** (optional documentation)
   - Document that markers are now the preferred way to run tests
   - Scripts can remain for convenience

### Benefits

1. **No more --ignore flags**: Running `pytest` runs only unit tests by default
2. **Minimal marking**: Only 21 files need markers (vs marking all 90 files)
3. **Natural default**: Unit tests run by default (most common use case)
4. **Clear categorization**: Special tests explicitly marked
5. **Better organization**: E2E fixture tests separated from E2E tests
6. **CI/CD ready**: Easy to run specific test suites in pipelines
7. **Less maintenance**: New unit tests don't need markers

### Why This Approach is Better Than Marking Everything

**Marking only special tests** (inverse selection):
- **Less work**: Only mark 21 files instead of 90
- **More intuitive**: "Mark what's special" vs "mark everything"
- **Better defaults**: `pytest` naturally runs unit tests
- **Less maintenance**: New unit tests work automatically
- **Clearer intent**: Marks indicate "this needs infrastructure"

**Original approach** (marking everything including unit):
- Requires `addopts = "-m unit"` to change pytest default behavior
- Must mark every new unit test file
- Less intuitive - why mark the common case?
- More file modifications needed

### Alternative Considered: Directory-Based Selection

Could use `testpaths` more cleverly or pytest collection hooks, but:
- Markers are more explicit and self-documenting
- Markers work better with pytest's built-in filtering
- Markers allow fine-grained control (individual test marking if needed)
- Markers are standard pytest practice for test categorization

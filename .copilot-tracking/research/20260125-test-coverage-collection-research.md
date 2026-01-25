<!-- markdownlint-disable-file -->
# Task Research Notes: Coverage Collection for Unit, Integration, and E2E Tests

## Research Executed

### File Analysis
- [pyproject.toml](pyproject.toml#L144-L155)
  - Already has `[tool.coverage.run]` configuration with `source`, `omit` settings
  - Already has `[tool.coverage.report]` configuration with `precision`, `skip_empty`
  - pytest-cov is already installed as a dependency
  - Current test addopts filter out integration and e2e tests by default

- [compose.int.yaml](compose.int.yaml#L117) and [compose.e2e.yaml](compose.e2e.yaml#L143)
  - Both use `command: -q --tb=line` to run tests quietly
  - Test containers use `pytest` as ENTRYPOINT
  - Services use tmpfs volumes (in-memory, auto-cleanup)

- [docker/test.Dockerfile](docker/test.Dockerfile)
  - Single Dockerfile used for both integration and e2e tests
  - Installs pytest-cov via `uv pip install --group dev`
  - Runs as non-root user (testuser)
  - No coverage collection currently configured

- [scripts/run-integration-tests.sh](scripts/run-integration-tests.sh) and [scripts/run-e2e-tests.sh](scripts/run-e2e-tests.sh)
  - Both run tests via `docker compose run --rm` with appropriate test service
  - No coverage data extraction currently implemented
  - Use cleanup trap to remove containers after tests

### Code Search Results
- No existing `.coverage*` files found in workspace
- No `coverage.xml` file present
- Coverage configuration exists in pyproject.toml but coverage collection not active

### External Research
- #fetch:"https://pytest-cov.readthedocs.io/en/latest/reporting.html"
  - pytest-cov supports multiple output formats: term, xml, json, html, lcov, markdown
  - Can specify output paths: `--cov-report xml:cov.xml`
  - Can combine multiple reports in single run
  - Supports `--cov-append` to accumulate coverage across runs

- #fetch:"https://coverage.readthedocs.io/en/latest/config.html"
  - `parallel = true` enables coverage collection from multiple processes
  - Creates separate `.coverage.*` files with unique suffixes
  - Requires `coverage combine` to merge data files
  - `relative_files = true` makes paths portable across environments
  - `[paths]` section allows path remapping when combining from different locations

### Project Conventions
- Standards referenced: Docker containerization best practices
- Instructions followed: Python testing conventions
- Coverage configuration already exists in pyproject.toml
- Tests are organized by markers: unit (default), integration, e2e

## Key Discoveries

### Project Structure
The project has three distinct test types with clear separation:
- **Unit tests**: Run locally without markers, fast execution
- **Integration tests**: Run in Docker with `pytest -m integration`, test daemon/RabbitMQ integration
- **E2E tests**: Run in Docker with `pytest -m e2e`, test full Discord bot interactions

### Current Test Execution Pattern
```yaml
# Integration tests (compose.int.yaml)
integration-tests:
  entrypoint: ["pytest", "-m", "integration"]
  command: -q --tb=line
  
# E2E tests (compose.e2e.yaml)
e2e-tests:
  entrypoint: ["pytest", "-m", "e2e"]
  command: -q --tb=line
```

### Coverage Configuration Already Present
```toml
[tool.coverage.run]
source = ["shared", "services"]
omit = [
    "*/tests/*",
    "*/alembic/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
    "services/init/*",
]

[tool.coverage.report]
precision = 2
skip_empty = true
```

## Recommended Approach

**Use pytest-cov with explicit coverage filenames via COVERAGE_FILE environment variable**

This approach leverages the existing pytest-cov installation and coverage configuration while using explicit, predictable filenames for each test type. This is cleaner than parallel mode because you know exactly what files will be created.

### 1. Volume Mount for Coverage Data
Mount the workspace root into test containers to persist `.coverage*` files:
- Unit tests write `.coverage` directly to workspace (default)
- Integration tests write `.coverage.integration` via `COVERAGE_FILE` env var
- E2E tests write `.coverage.e2e` via `COVERAGE_FILE` env var

### 2. Explicit Coverage Filenames
Use the `COVERAGE_FILE` environment variable to specify output files:
```yaml
# In compose.int.yaml
integration-tests:
  environment:
    COVERAGE_FILE: .coverage.integration
    
# In compose.e2e.yaml
e2e-tests:
  environment:
    COVERAGE_FILE: .coverage.e2e
```

### 3. Coverage Collection Commands
Add coverage flags to pytest invocations:
```bash
# Unit tests (local)
pytest --cov=shared --cov=services --cov-report=

# Integration tests (in container)
COVERAGE_FILE=.coverage.integration pytest -m integration --cov=shared --cov=services --cov-report=

# E2E tests (in container)
COVERAGE_FILE=.coverage.e2e pytest -m e2e --cov=shared --cov=services --cov-report=
```

### 4. Combine and Report
After all test runs complete:
```bash
coverage combine  # Merges .coverage, .coverage.integration, .coverage.e2e
coverage report   # Terminal summary
coverage xml      # For CI/CD systems
coverage html     # For detailed local review
```

## Implementation Guidance

### Objectives
- Collect coverage data from all three test types without changing test logic
- Generate combined coverage report showing total coverage across all tests
- Support both local development and CI/CD environments
- Maintain clean separation between test types

### Key Tasks

1. **Update pyproject.toml coverage configuration**
   - Add `relative_files = true` to `[tool.coverage.run]` for container/host path portability
   - Keep existing `source` and `omit` settings
   - **No need for `parallel = true`** - using explicit filenames instead

2. **Modify Docker Compose test service definitions**
   - Add volume mount for workspace root in both compose.int.yaml and compose.e2e.yaml
   - Add `COVERAGE_FILE` environment variable: `.coverage.integration` and `.coverage.e2e`
   - Update `command` to include coverage flags: `--cov=shared --cov=services --cov-report= -q --tb=line`

3. **Update test scripts**
   - Test scripts don't need changes - environment variable in compose file handles it
   - Optionally pass `--cov` flags if not hardcoded in compose files

4. **Create coverage reporting script**
   - Add `scripts/coverage-report.sh` to combine and report coverage
   - Example: `coverage combine && coverage report && coverage html`

5. **Update .gitignore**
   - Add `.coverage*` patterns to prevent coverage files from being committed
   - Add `htmlcov/` for HTML coverage reports

### Dependencies
- pytest-cov (already installed)
- coverage (comes with pytest-cov)
- Docker and docker compose (already in use)
- Volume mount support in Docker environment

### Success Criteria
- Single coverage report combining data from all three test types
- Coverage data persists after container cleanup
- Developers can run `coverage report` to see combined results
- CI/CD can generate and upload coverage reports
- No significant increase in test execution time
- Coverage files don't pollute git repository (add to .gitignore)

### Example Workflow

```bash
# Run all tests with coverage
pytest --cov=shared --cov=services --cov-report=  # Unit tests → .coverage
./scripts/run-integration-tests.sh                 # Integration tests → .coverage.integration
./scripts/run-e2e-tests.sh                         # E2E tests → .coverage.e2e

# Combine and report
coverage combine  # Merges .coverage, .coverage.integration, .coverage.e2e
coverage report
coverage html  # Open htmlcov/index.html for detailed view
```

### Why This Approach vs Parallel Mode

**Explicit filenames (recommended):**
- ✅ Predictable file names: `.coverage`, `.coverage.integration`, `.coverage.e2e`
- ✅ Easy to debug - you know exactly which file came from which test type
- ✅ Simpler configuration - just set `COVERAGE_FILE` environment variable
- ✅ No random suffixes with machine names, PIDs, or random numbers

**Parallel mode (not needed here):**
- Uses random suffixes: `.coverage.hostname.12345.abcdef`
- Useful when running same tests across multiple machines/processes simultaneously
- Adds complexity without benefit for our use case

### Alternative Considered: Coverage in Each Test Type Separately

**Why not recommended:** This would give you three separate coverage numbers but wouldn't show the combined coverage across all test types. You'd need to manually track which code is tested by which test type, and you couldn't easily see if there are gaps that none of the test types cover.


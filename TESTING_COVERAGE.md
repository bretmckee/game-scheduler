# Test Coverage Collection

This project collects coverage data from three test types: unit, integration, and e2e tests.

## Quick Start

### Run All Tests with Coverage

```bash
# Run all tests (unit, integration, e2e) and generate coverage reports
./scripts/coverage-report.sh

# Or skip e2e tests if you don't have Discord credentials configured
./scripts/coverage-report.sh --skip-e2e
```

This single script will:
1. Run unit tests with coverage
2. Run integration tests in Docker with coverage
3. Run e2e tests in Docker with coverage (unless `--skip-e2e` is specified)
4. Combine all coverage data
5. Generate terminal, XML, and HTML reports

### View Results

- **Terminal**: Run `./scripts/coverage-report.sh` to see summary
- **HTML Report**: Open `htmlcov/index.html` in your browser
- **XML Report**: `coverage.xml` (for CI/CD integrations)

## How It Works

### Coverage Data Files

Each test type writes to its own coverage file:

- Unit tests → `.coverage` (default)
- Integration tests → `.coverage.integration`
- E2E tests → `.coverage.e2e`

The `coverage combine` command merges all three files into a single `.coverage` file for reporting.

### Configuration

Coverage is configured in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["shared", "services"]
relative_files = true  # Makes paths portable between host and containers
omit = [
    "*/tests/*",
    "*/alembic/*",
    # ... other patterns
]

[tool.coverage.report]
precision = 2
skip_empty = true
```

### Docker Integration

The Docker Compose files set the `COVERAGE_FILE` environment variable:

- `compose.int.yaml`: Sets `COVERAGE_FILE=.coverage.integration`
- `compose.e2e.yaml`: Sets `COVERAGE_FILE=.coverage.e2e`

Both mount the workspace root (`.:/app`) so coverage data persists after container cleanup.

## Coverage Reports

### Terminal Report

```bash
./scripts/coverage-report.sh
```

Shows a table with statement and branch coverage for each file.

### HTML Report

```bash
./scripts/coverage-report.sh
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

Provides:
- Color-coded source files showing covered/uncovered lines
- Branch coverage details
- Sortable tables
- Search functionality

### XML Report

```bash
./scripts/coverage-report.sh
```

Generates `coverage.xml` in Cobertura format for CI/CD systems like:
- GitHub Actions
- GitLab CI
- Jenkins
- Codecov
- Coveralls

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Run all tests with coverage
  run: ./scripts/coverage-report.sh --skip-e2e

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

Or if you have Discord credentials configured for e2e tests:

```yaml
- name: Run all tests with coverage (including e2e)
  run: ./scripts/coverage-report.sh
  env:
    DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_BOT_TOKEN }}
    # ... other Discord credentials

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## Running Tests Individually

If you want to run specific test types instead of all tests:

```bash
# Unit tests only (default behavior)
pytest --cov=shared --cov=services --cov-report=term-missing

# Integration tests only
./scripts/run-integration-tests.sh

# E2E tests only
./scripts/run-e2e-tests.sh

# Then combine manually
coverage combine
coverage report
```

## Troubleshooting

### No coverage data found

If you see "ERROR: No coverage data files found", this usually means:
1. Tests failed before generating coverage data
2. Coverage collection wasn't enabled (missing `--cov` flags)
3. All tests were skipped

### Low coverage numbers

Check:
1. All test types ran successfully
2. Coverage configuration `source` matches your code structure
3. Important directories aren't in the `omit` list

### Path issues with Docker tests

The `relative_files = true` setting in `pyproject.toml` should handle path differences between host and container. If you still see issues, check that:
1. Workspace is mounted at `/app` in containers
2. Container working directory is `/app`

## Development Tips

### Quick Unit Test Coverage

```bash
pytest --cov=shared --cov=services --cov-report=term-missing
```

Shows missing lines immediately without generating files.

### Coverage for Specific Module

```bash
pytest --cov=services.api --cov-report=term-missing tests/unit/
```

### Skip Coverage Collection

Omit `--cov` flags to run tests faster during development:

```bash
pytest tests/unit/
```

## File Locations

- Coverage data: `.coverage`, `.coverage.integration`, `.coverage.e2e` (gitignored)
- XML report: `coverage.xml` (gitignored)
- HTML report: `htmlcov/` directory (gitignored)
- Configuration: `pyproject.toml` under `[tool.coverage.*]`
- Report script: `scripts/coverage-report.sh`

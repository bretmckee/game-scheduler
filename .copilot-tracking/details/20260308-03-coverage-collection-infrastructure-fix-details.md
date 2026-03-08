<!-- markdownlint-disable-file -->

# Task Details: Coverage Collection Infrastructure Fix

## Research Reference

**Source Research**: #file:../research/20260308-03-test-coverage-gaps-research.md

---

## Phase 1: Add `coverage` to project dependencies

### Task 1.1: Add `coverage` to `[project.dependencies]` in `pyproject.toml`

Add `"coverage[toml]"` to the `[project.dependencies]` list. This ensures all four service Dockerfiles install it automatically via the existing `uv pip install --system .` call — no Dockerfile changes needed for the package itself.

- **Files**:
  - `pyproject.toml` - Add `"coverage[toml]"` entry to `[project.dependencies]`
- **Success**:
  - `grep -n "coverage" pyproject.toml` shows an entry inside `[project.dependencies]`
  - `docker build -f docker/api.Dockerfile .` succeeds and `python -c "import coverage"` works inside the built image
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 20-21) - Confirms `coverage` is not currently in `[project.dependencies]`
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 103-108) - Recommended approach step 1
- **Dependencies**:
  - None

---

## Phase 2: Install `sitecustomize.py` in service Dockerfiles

### Task 2.1: Add `sitecustomize.py` RUN line to `docker/api.Dockerfile`

In the `base` build stage (after `uv pip install --system .`), add a `RUN` instruction that writes `sitecustomize.py` into the system site-packages directory. This hooks coverage auto-startup into every Python interpreter invocation in that container.

```dockerfile
RUN python -c "import site; open(site.getsitepackages()[0] + '/sitecustomize.py', 'w').write('import coverage\ncoverage.process_startup()\n')"
```

This instruction is a no-op in production because `COVERAGE_PROCESS_START` is never set in `compose.prod.yaml` or `compose.staging.yaml`.

- **Files**:
  - `docker/api.Dockerfile` - Add `RUN` line in `base` stage after package installation
- **Success**:
  - `docker build -f docker/api.Dockerfile .` succeeds
  - `docker run --rm <image> python -c "import sitecustomize"` exits 0
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 48-55) - Activation mechanism explanation
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 109-116) - Recommended approach step 2
- **Dependencies**:
  - Task 1.1 must be complete (coverage must be installed before sitecustomize.py can import it)

### Task 2.2: Add `sitecustomize.py` RUN line to `docker/bot.Dockerfile`

Same `RUN` instruction as Task 2.1, applied to `docker/bot.Dockerfile`.

- **Files**:
  - `docker/bot.Dockerfile` - Add `RUN` line in `base` stage after package installation
- **Success**:
  - `docker build -f docker/bot.Dockerfile .` succeeds
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 109-116) - Recommended approach step 2
- **Dependencies**:
  - Task 1.1 complete

### Task 2.3: Add `sitecustomize.py` RUN line to `docker/scheduler.Dockerfile`

Same `RUN` instruction as Task 2.1, applied to `docker/scheduler.Dockerfile`.

- **Files**:
  - `docker/scheduler.Dockerfile` - Add `RUN` line in `base` stage after package installation
- **Success**:
  - `docker build -f docker/scheduler.Dockerfile .` succeeds
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 109-116) - Recommended approach step 2
- **Dependencies**:
  - Task 1.1 complete

### Task 2.4: Add `sitecustomize.py` RUN line to `docker/retry.Dockerfile`

Same `RUN` instruction as Task 2.1, applied to `docker/retry.Dockerfile`.

- **Files**:
  - `docker/retry.Dockerfile` - Add `RUN` line in `base` stage after package installation
- **Success**:
  - `docker build -f docker/retry.Dockerfile .` succeeds
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 109-116) - Recommended approach step 2
- **Dependencies**:
  - Task 1.1 complete

---

## Phase 3: Add coverage env/volumes to compose.int.yaml

For each service below, add to its existing entry in `compose.int.yaml`:

```yaml
volumes:
  - ./coverage:/app/coverage:rw
environment:
  COVERAGE_PROCESS_START: /app/pyproject.toml
  COVERAGE_FILE: /app/coverage/.coverage.<service>.integration
```

### Task 3.1: Add coverage instrumentation to `api` service in `compose.int.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.api.integration`

- **Files**:
  - `compose.int.yaml` - Add `volumes` and `environment` entries to the `api` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.int.yaml` shows the api entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 119-133) - Recommended approach step 3, naming scheme
- **Dependencies**:
  - Phase 2 tasks complete (sitecustomize.py must be in the image)

### Task 3.2: Add coverage instrumentation to `bot` service in `compose.int.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.bot.integration`

- **Files**:
  - `compose.int.yaml` - Add `volumes` and `environment` entries to the `bot` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.int.yaml` shows the bot entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 119-133)
- **Dependencies**:
  - Phase 2 tasks complete

### Task 3.3: Add coverage instrumentation to `scheduler` service in `compose.int.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.scheduler.integration`

- **Files**:
  - `compose.int.yaml` - Add `volumes` and `environment` entries to the `scheduler` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.int.yaml` shows the scheduler entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 119-133)
- **Dependencies**:
  - Phase 2 tasks complete

### Task 3.4: Add coverage instrumentation to `retry-daemon` service in `compose.int.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.retry.integration`

- **Files**:
  - `compose.int.yaml` - Add `volumes` and `environment` entries to the `retry-daemon` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.int.yaml` shows the retry-daemon entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 119-133)
- **Dependencies**:
  - Phase 2 tasks complete

---

## Phase 4: Add coverage env/volumes to compose.e2e.yaml

Same pattern as Phase 3. `retry-daemon` does not appear in `compose.e2e.yaml`, so only three services are instrumented.

### Task 4.1: Add coverage instrumentation to `api` service in `compose.e2e.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.api.e2e`

- **Files**:
  - `compose.e2e.yaml` - Add `volumes` and `environment` entries to the `api` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.e2e.yaml` shows the api entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 136-142) - Recommended approach step 4
- **Dependencies**:
  - Phase 2 tasks complete

### Task 4.2: Add coverage instrumentation to `bot` service in `compose.e2e.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.bot.e2e`

- **Files**:
  - `compose.e2e.yaml` - Add `volumes` and `environment` entries to the `bot` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.e2e.yaml` shows the bot entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 136-142)
- **Dependencies**:
  - Phase 2 tasks complete

### Task 4.3: Add coverage instrumentation to `scheduler` service in `compose.e2e.yaml`

`COVERAGE_FILE: /app/coverage/.coverage.scheduler.e2e`

- **Files**:
  - `compose.e2e.yaml` - Add `volumes` and `environment` entries to the `scheduler` service block
- **Success**:
  - `grep -A5 "COVERAGE_FILE" compose.e2e.yaml` shows the scheduler entry
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 136-142)
- **Dependencies**:
  - Phase 2 tasks complete

---

## Phase 5: Verify coverage-report.sh combines new files

### Task 5.1: Update `scripts/coverage-report.sh` to include all per-service coverage files

Review the `coverage combine` invocation in `scripts/coverage-report.sh`. The script currently expects three specific files. After the fix, up to seven additional files will exist in `coverage/`. Update the combine step to use a glob (`coverage/.coverage.*`) or explicit list that includes all new per-service files.

Ensure the `.coverage.unit` file (which lives at repo root, not in `coverage/`) is still included in the combine list.

- **Files**:
  - `scripts/coverage-report.sh` - Update `coverage combine` arguments to include `coverage/.coverage.api.integration`, `coverage/.coverage.bot.integration`, `coverage/.coverage.scheduler.integration`, `coverage/.coverage.retry.integration`, `coverage/.coverage.api.e2e`, `coverage/.coverage.bot.e2e`, `coverage/.coverage.scheduler.e2e`
- **Success**:
  - `bash scripts/coverage-report.sh` (after a test run) exits 0 and the terminal shows non-zero line counts for service modules
  - `coverage report` output includes lines from `services/api/routes/*.py` with integration coverage > 0
- **Research References**:
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 145-150) - Recommended approach step 5
  - #file:../research/20260308-03-test-coverage-gaps-research.md (Lines 5-9) - Current expected filenames in coverage-report.sh
- **Dependencies**:
  - Phases 3 and 4 complete

---

## Dependencies

- `coverage[toml]` Python package (added in Phase 1)
- Docker Compose v2 (`docker compose`)
- Existing `./coverage/` host directory (already used by integration test runner)

## Success Criteria

- `./coverage/.coverage.api.integration` (and bot, scheduler, retry equivalents) appear after `scripts/run-integration-tests.sh`
- `./coverage/.coverage.api.e2e` (and bot, scheduler equivalents) appear after `scripts/run-e2e-tests.sh`
- `scripts/coverage-report.sh` combined report shows non-zero coverage on service modules
- No changes to `compose.prod.yaml`, `compose.staging.yaml`, or `compose.yaml` (production unaffected)

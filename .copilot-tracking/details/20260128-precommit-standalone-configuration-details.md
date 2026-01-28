<!-- markdownlint-disable-file -->

# Task Details: Pre-commit Standalone Configuration

## Research Reference

**Source Research**: #file:../research/20260128-precommit-standalone-configuration-research.md

## Phase 1: Replace Python Tools with Official Repositories

### Task 1.1: Replace ruff hooks with official astral-sh/ruff-pre-commit repository

Replace the current system-dependent ruff hooks (ruff-check, ruff-format) with the official ruff-pre-commit repository that creates isolated environments.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replace local ruff hooks with official repo
- **Success**:
  - Configuration uses `https://github.com/astral-sh/ruff-pre-commit`
  - Both `ruff` and `ruff-format` hooks defined
  - No dependency on `uv run` or project virtual environment
  - Hook passes on all Python files
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 170-182) - Official repository pattern for ruff
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 256-264) - Optimal standalone configuration example
- **Dependencies**:
  - None - this is the first migration step

### Task 1.2: Replace mypy hook with official pre-commit/mirrors-mypy repository

Replace the current system-dependent mypy hook with the official mirrors-mypy repository, including necessary type stub dependencies.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replace local mypy hook with official repo
- **Success**:
  - Configuration uses `https://github.com/pre-commit/mirrors-mypy`
  - Includes `additional_dependencies` for sqlalchemy, types-redis, and other type stubs
  - Hook passes on shared/ and services/ directories
  - No dependency on project virtual environment
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 270-279) - Mypy configuration with type stubs
- **Dependencies**:
  - Task 1.1 completion recommended for testing consistency

### Task 1.3: Test Python tool migrations and verify isolated environments

Verify that migrated Python hooks work without project dependencies and create proper isolated environments.

- **Files**:
  - None - testing only
- **Success**:
  - `pre-commit run ruff --all-files` succeeds without `uv sync`
  - `pre-commit run mypy --all-files` succeeds without `uv sync`
  - Isolated environments visible in `~/.cache/pre-commit/`
  - Hook execution time acceptable (similar or faster than before)
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 479-498) - Testing and verification procedures
- **Dependencies**:
  - Tasks 1.1 and 1.2 completion

## Phase 2: Replace Node.js Tools with Official Repositories

### Task 2.1: Replace prettier hook with official pre-commit/mirrors-prettier repository

Replace the current system-dependent prettier hook with the official mirrors-prettier repository.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replace local prettier hook with official repo
- **Success**:
  - Configuration uses `https://github.com/pre-commit/mirrors-prettier`
  - Hook configured with `files: ^frontend/` and config path argument
  - Hook passes on frontend files
  - No dependency on `npm install` in frontend/
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 281-288) - Prettier configuration pattern
- **Dependencies**:
  - Phase 1 completion recommended for consistency

### Task 2.2: Replace eslint hook with official pre-commit/mirrors-eslint repository

Replace the current system-dependent eslint hook with the official mirrors-eslint repository, including all required plugins.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replace local eslint hook with official repo
- **Success**:
  - Configuration uses `https://github.com/pre-commit/mirrors-eslint`
  - Includes `additional_dependencies` for TypeScript plugins, React plugins, prettier integration
  - Hook configured with `files: ^frontend/` and config path argument
  - Hook passes on frontend TypeScript/JavaScript files
  - No dependency on `npm install` in frontend/
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 290-306) - ESLint configuration with all dependencies
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 224-245) - Challenge and solution discussion
- **Dependencies**:
  - Task 2.1 completion recommended for testing consistency

### Task 2.3: Test Node.js tool migrations and verify isolated environments

Verify that migrated Node.js hooks work without project dependencies and create proper isolated environments.

- **Files**:
  - None - testing only
- **Success**:
  - `pre-commit run prettier --all-files` succeeds without `cd frontend && npm install`
  - `pre-commit run eslint --all-files` succeeds without `cd frontend && npm install`
  - Isolated node environments visible in `~/.cache/pre-commit/`
  - Hook execution time acceptable
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 479-498) - Testing and verification procedures
- **Dependencies**:
  - Tasks 2.1 and 2.2 completion

## Phase 3: Convert Custom Tools to Proper Language Types

### Task 3.1: Convert complexipy and lizard to use language: python with additional_dependencies

Convert complexity checking hooks from `language: system` to `language: python` with proper dependency isolation.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Update complexipy and lizard-typescript hooks
- **Success**:
  - Both hooks use `language: python` instead of `language: system`
  - Include `additional_dependencies: ['complexipy~=4.2.0']` and `['lizard~=1.20.0']`
  - Hooks pass on their respective file sets
  - No dependency on project virtual environment
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 317-328) - Complexity tools migration pattern
- **Dependencies**:
  - Phases 1-2 completion for consistency

### Task 3.2: Inline autocopyright logic from scripts/add-copyright wrapper

Replace the bash wrapper script with direct autocopyright invocations in pre-commit config, eliminating dependency on repository scripts.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replace add-copyright-python and add-copyright-typescript hooks
- **Success**:
  - Both copyright hooks use `language: python` with `additional_dependencies: ['autocopyright~=1.1.0']`
  - Entry commands match the logic in scripts/add-copyright (separate invocations for Python vs TypeScript)
  - Hooks pass and add copyright headers correctly
  - No dependency on scripts/add-copyright file
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 330-343) - Autocopyright migration options
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 308-316) - Template pattern in optimal config
- **Dependencies**:
  - None - independent task

### Task 3.3: Convert typescript hook to use language: node with additional_dependencies

Convert TypeScript type checking from `language: system` to `language: node` with isolated environment.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Update typescript hook
- **Success**:
  - Hook uses `language: node` instead of `language: system`
  - Includes `additional_dependencies: ['typescript@^5.9.3']`
  - Entry command references frontend/tsconfig.json
  - Hook passes on frontend TypeScript files
  - No dependency on npm install
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 337-345) - TypeScript migration pattern
- **Dependencies**:
  - Phase 2 completion for consistency

### Task 3.4: Convert jscpd-diff to use language: node (already nearly standalone)

Convert the duplicate detection hook from using `npx --yes` to proper `language: node` with dependency management.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Update jscpd-diff hook
- **Success**:
  - Hook uses `language: node` instead of `language: system`
  - Includes `additional_dependencies: ['jscpd']`
  - Entry command updated to remove `npx --yes` wrapper
  - Hook passes and correctly identifies duplicates
  - Note: scripts/check_commit_duplicates.py still referenced (acceptable as repo-local script)
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 345-358) - jscpd migration discussion
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 376-389) - jscpd-diff in optimal config
- **Dependencies**:
  - None - independent task

## Phase 4: Document System-Dependent Hooks

### Task 4.1: Identify hooks requiring full project environment

Document which hooks must remain as `language: system` because they require full project dependencies.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml) - Add comments documenting system hooks
- **Success**:
  - Clear comment section before system-dependent hooks explaining why they remain as `language: system`
  - Hooks identified: pytest-coverage, vitest-coverage, frontend-build, ci-cd-workflow (act)
  - Each hook has inline comment explaining dependency requirement
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 391-423) - System hooks section in optimal config
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 461-477) - Success criteria for system hooks
- **Dependencies**:
  - Phases 1-3 completion to clearly distinguish standalone vs system hooks

### Task 4.2: Update README.md with pre-commit setup documentation

Add clear documentation section explaining standalone hooks vs system-dependent hooks and setup requirements.

- **Files**:
  - [README.md](README.md) - Add/update pre-commit setup section
- **Success**:
  - Section titled "Pre-commit Setup" or similar
  - Explains that most hooks work immediately after `git clone`
  - Lists specific hooks requiring `uv sync` (pytest-coverage)
  - Lists specific hooks requiring `cd frontend && npm install` (vitest-coverage, frontend-build)
  - Lists hooks requiring Docker (act)
  - Includes example commands for quick start
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 425-442) - Documentation examples
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 500-512) - Success criteria for documentation
- **Dependencies**:
  - Task 4.1 completion for accurate hook categorization

## Phase 5: Testing and Validation

### Task 5.1: Test fresh clone workflow without project dependencies

Validate that the standalone hooks work correctly in a fresh repository clone without running `uv sync` or `npm install`.

- **Files**:
  - None - testing only in separate directory
- **Success**:
  - Create fresh clone in temporary directory
  - Run `pre-commit install`
  - Run `pre-commit run --all-files` succeeds for standalone hooks
  - Only system-dependent hooks fail with clear error messages
  - Linting/formatting hooks (ruff, prettier, eslint) work correctly
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 479-489) - Fresh clone testing procedure
- **Dependencies**:
  - Phases 1-4 completion

### Task 5.2: Verify pre-commit autoupdate functionality

Confirm that hooks using official repositories can be automatically updated to latest versions.

- **Files**:
  - None - testing only
- **Success**:
  - Run `pre-commit autoupdate` successfully
  - Official repository hooks update to latest versions
  - Local hooks remain at specified versions
  - All hooks still pass after update
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 491-498) - Autoupdate testing
- **Dependencies**:
  - Task 5.1 completion

### Task 5.3: Benchmark hook execution time

Measure and compare hook execution time before and after migration to ensure performance is maintained or improved.

- **Files**:
  - None - testing only
- **Success**:
  - Measure `time pre-commit run --all-files` before migration (from backup config)
  - Measure `time pre-commit run --all-files` after migration
  - Document results showing similar or better performance
  - Identify any hooks with degraded performance and investigate
- **Research References**:
  - #file:../research/20260128-precommit-standalone-configuration-research.md (Lines 520-525) - Performance trade-offs discussion
- **Dependencies**:
  - Task 5.1 completion

## Dependencies

- Pre-commit framework (already installed via pyproject.toml)
- Python 3.13+ available in PATH
- Node.js 20+ available in PATH
- Git (for testing)

## Success Criteria

- Configuration uses official repositories for ruff, mypy, prettier, eslint
- All standalone hooks work without `uv sync` or `npm install`
- Isolated environments created in `~/.cache/pre-commit/`
- `pre-commit autoupdate` successfully updates official repository hooks
- System-dependent hooks clearly documented with rationale
- README includes clear setup instructions
- Fresh clone workflow validated and documented
- Hook execution time similar or better than before

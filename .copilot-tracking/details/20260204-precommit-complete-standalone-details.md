<!-- markdownlint-disable-file -->

# Task Details: Pre-commit Complete Standalone Configuration

## Research Reference

**Source Research**: #file:../research/20260204-precommit-complete-standalone-research.md

## Phase 1: Convert Python Tools to Standalone

### Task 1.1: Convert python-compile to language: python

Change python-compile hook from `language: system` with `uv run` to standalone `language: python`.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L117-L125) - python-compile hook definition
- **Changes**:
  - Remove `uv run` prefix from entry
  - Change `language: system` to `language: python`
  - Entry becomes: `python -m compileall -q services shared tests`
- **Success**:
  - Hook runs without `uv sync` being executed first
  - Pre-commit creates isolated Python environment automatically
  - Files compile successfully
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 57-65) - Python compile conversion example

### Task 1.2: Convert mypy to language: python with type stubs

Change mypy hook from `language: system` with `uv run` to standalone `language: python` with type stub dependencies.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L127-L135) - mypy hook definition
  - [pyproject.toml](pyproject.toml#L15-L50) - Reference for type dependencies
- **Changes**:
  - Remove `uv run` prefix from entry
  - Change `language: system` to `language: python`
  - Add `additional_dependencies` with mypy and required type stubs
  - Entry becomes: `mypy shared/ services/`
- **Additional Dependencies Required**:
  - `mypy>=1.10.0`
  - `sqlalchemy[asyncio]~=2.0.36` (for SQLAlchemy type checking)
  - Type stub packages as needed
- **Success**:
  - Hook runs without `uv sync` being executed first
  - Type checking works correctly with all imports resolved
  - No import errors from missing type stubs
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 67-82) - MyPy conversion with type stubs

### Task 1.3: Convert diff-coverage to language: python

Change diff-coverage hook from `language: system` with `uv run` to standalone `language: python`.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L144-L152) - diff-coverage hook definition
- **Changes**:
  - Replace `uv run diff-cover` with just `diff-cover` in bash command
  - Change `language: system` to `language: python`
  - Add `additional_dependencies: ['diff-cover~=9.2.0']`
- **Success**:
  - Hook runs without `uv sync` being executed first
  - Coverage diff calculation works correctly
  - Properly fails when coverage drops below threshold
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 84-95) - diff-cover conversion example

### Task 1.4: Convert diff-coverage-frontend to language: python

Change frontend diff-coverage hook from `language: system` with `uv run` to standalone `language: python`.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L182-L190) - diff-coverage-frontend hook definition
- **Changes**:
  - Replace `uv run diff-cover` with just `diff-cover` in bash command
  - Change `language: system` to `language: python`
  - Add `additional_dependencies: ['diff-cover~=9.2.0']`
- **Success**:
  - Hook runs without `uv sync` being executed first
  - Frontend coverage diff calculation works correctly
  - Properly fails when frontend coverage drops below threshold
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 84-95) - diff-cover conversion (same tool)

## Phase 2: Convert Node.js Tools to Standalone

### Task 2.1: Convert typescript to language: node

Change typescript hook from `language: system` with `npm run` to standalone `language: node`.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L165-L172) - typescript hook definition
- **Changes**:
  - Remove `cd frontend && npm run type-check` wrapper
  - Change to direct tsc command: `tsc --project frontend/tsconfig.json --noEmit`
  - Change `language: system` to `language: node`
  - Add `additional_dependencies: ['typescript@^5.9.3']`
- **Success**:
  - Hook runs without `npm install` being executed first
  - TypeScript type checking works with config file path
  - All type errors detected correctly
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 113-122) - TypeScript conversion example
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 168-173) - Config file path validation

### Task 2.2: Convert eslint to language: node with all plugins

Change eslint hook from `language: system` with `npm run` to standalone `language: node` with all plugin dependencies.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L105-L112) - eslint hook definition
  - [frontend/package.json](frontend/package.json#L37-L50) - Reference for eslint plugins
  - [frontend/eslint.config.js](frontend/eslint.config.js) - ESLint configuration importing plugins
- **Changes**:
  - Remove `cd frontend && npm run lint:fix` wrapper
  - Change to direct eslint command: `eslint --config frontend/eslint.config.js --fix`
  - Change `language: system` to `language: node`
  - Add all required plugins to `additional_dependencies`
- **Additional Dependencies Required**:
  - `eslint@^9.39.2`
  - `@typescript-eslint/eslint-plugin@^8.0.0`
  - `@typescript-eslint/parser@^8.0.0`
  - `eslint-plugin-react@^7.37.5`
  - `eslint-plugin-react-hooks@^7.0.0`
  - `eslint-plugin-react-refresh@^0.4.25`
  - `eslint-plugin-prettier@^5.5.4`
  - `eslint-config-prettier@^10.1.8`
  - `@eslint/js@^9.39.2`
  - `globals@^16.5.0`
- **Success**:
  - Hook runs without `npm install` being executed first
  - All ESLint rules work correctly
  - Config file imports resolve properly
  - Auto-fix works as expected
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 124-149) - ESLint conversion with plugins
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 168-173) - Config file path validation

## Phase 3: Add Documentation Comments

### Task 3.1: Document hooks requiring project setup

Add clear comments in .pre-commit-config.yaml explaining which hooks need project dependencies.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L114-L195) - Section with Python and frontend hooks
- **Changes**:
  - Add comment before pytest-coverage explaining it needs `uv sync`
  - Add comment before frontend-build explaining it needs `npm install`
  - Add comment before vitest-coverage explaining it needs `npm install`
  - Group system-dependent hooks together for clarity
- **Comment Content**:
  - "Requires project dependencies: run 'uv sync' before using this hook"
  - "Requires frontend dependencies: run 'cd frontend && npm install' before using this hook"
- **Success**:
  - Clear documentation for developers on what setup is needed
  - System hooks easily identifiable
  - New contributors understand the difference
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 193-199) - Documentation strategy

### Task 3.2: Add comments explaining system vs isolated hooks

Add section comments explaining the architecture of standalone vs system hooks.

- **Files**:
  - [.pre-commit-config.yaml](.pre-commit-config.yaml#L1-L10) - Top of config file
- **Changes**:
  - Add explanation comment at top about hook isolation strategy
  - Explain that most hooks run in isolated environments
  - Note that test/build hooks require project setup
- **Success**:
  - Configuration purpose is clear to maintainers
  - Architecture documented inline
  - Reduces confusion about different hook types
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 175-191) - Tiered strategy explanation

## Phase 4: Testing and Validation

### Task 4.1: Test converted hooks in clean environment

Verify standalone hooks work without project dependencies installed.

- **Testing Process**:
  1. Create a clean directory outside the project
  2. Clone repository fresh: `git clone <repo>`
  3. Run `pre-commit install`
  4. Test each converted hook individually: `pre-commit run <hook-id> --all-files`
  5. Verify hooks create isolated environments in `~/.cache/pre-commit/`
- **Success**:
  - All 6 converted hooks run successfully
  - No errors about missing `uv` or `npm` packages
  - Isolated environments created automatically
  - Hook execution completes without errors
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 217-224) - Success criteria

### Task 4.2: Verify system hooks still work correctly

Ensure hooks that remain as `language: system` continue functioning properly.

- **Testing Process**:
  1. Run `uv sync` to install Python dependencies
  2. Run `cd frontend && npm install` to install frontend dependencies
  3. Test pytest-coverage: `pre-commit run pytest-coverage --all-files`
  4. Test frontend-build: `pre-commit run frontend-build --all-files`
  5. Test vitest-coverage: `pre-commit run vitest-coverage --all-files`
  6. Run full pre-commit: `pre-commit run --all-files`
- **Success**:
  - All system hooks pass with dependencies installed
  - No regression in functionality
  - Error messages clear when dependencies missing
- **Research References**:
  - #file:../research/20260204-precommit-complete-standalone-research.md (Lines 97-107) - System hooks that should remain

## Dependencies

- Python 3.13+ (for isolated Python environments)
- Node.js 22+ (for isolated Node environments)
- Git (for diff-coverage functionality)

## Success Criteria

- All 6 hooks converted successfully (python-compile, mypy, 2x diff-cover, typescript, eslint)
- Standalone hooks work immediately after `git clone` without setup
- System hooks documented and work with dependencies installed
- No performance degradation
- All hooks pass validation

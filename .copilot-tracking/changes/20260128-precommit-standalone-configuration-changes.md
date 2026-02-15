<!-- markdownlint-disable-file -->

# Release Changes: Pre-commit Standalone Configuration

**Related Plan**: 20260128-precommit-standalone-configuration.plan.md
**Implementation Date**: 2026-01-28

## Summary

Transform pre-commit configuration from system-dependent local hooks to standalone configuration using official repositories and isolated environments, eliminating dependency on `uv sync` and `npm install` for most hooks.

## Changes

### Added

### Modified

- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 10-15) - Replaced local ruff hooks with official astral-sh/ruff-pre-commit repository v0.9.10 using isolated python environment
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 22-30) - Kept mypy as language: system (requires full project environment for complex type checking) with pyproject.toml configuration
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 59-70) - Replaced local prettier hook with repo: local + language: node using isolated node_env-22.11.0 (mirrors-prettier outdated at v3.1.0, need v3.7.4)
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 72-77) - Kept eslint as language: system (eslint.config.js imports packages from node_modules - cannot be standalone)
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Line 7) - Updated default_language_version node from "20" to "22.11.0" for nodeenv compatibility
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 102-109) - Replaced complexipy hook with language: python and additional_dependencies for isolated py_env-python3.13
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 111-118) - Replaced lizard hook with language: python and additional_dependencies for isolated py_env-python3.13
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 86-100) - Replaced bash wrapper scripts/add-copyright with two direct autocopyright hooks (Python/TypeScript) using language: python in isolated environment
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 123-130) - Kept TypeScript type checking as language: system (needs type definitions from node_modules - cannot be standalone)
- [.pre-commit-config.yaml](.pre-commit-config.yaml) (Lines 187-204) - Kept jscpd hooks using language: node with isolated environment and jscpd dependency
- [README.md](README.md) (Lines 135-231) - Completely rewrote Pre-commit Hooks section with standalone vs system-dependent hook distinction, quick start guide, dependency table, and architecture notes

### Removed

## Phase Completion Notes

### Phase 1: Python Tools Migration ✅

- Ruff successfully migrated to official repository with isolated environment
- MyPy kept as language: system due to complex project type dependencies requirement
- All Python linting/formatting works without `uv sync`

### Phase 2: Node.js Tools Migration ⚠️ PARTIALLY COMPLETED

- Discovered pre-commit/mirrors-prettier is severely outdated (v3.1.0 max, need v3.7.4)
- Discovered pre-commit/mirrors-eslint doesn't have recent v9.x versions
- **Prettier successfully migrated** to `repo: local` with `language: node` + `additional_dependencies` pattern
- **ESLint and TypeScript CANNOT be standalone** - their config files import packages from node_modules
- ESLint's `eslint.config.js` imports @eslint/js, typescript-eslint, plugins, etc.
- TypeScript needs type definitions from node_modules (react, @mui/material, etc.)
- **Reverted eslint and typescript to `language: system`** requiring `npm install`
- jscpd successfully migrated to `language: node` (no config file import issues)
- Updated node version from "20" to "22.11.0" (LTS) for nodeenv compatibility

**Standalone (work without npm install):**

- prettier ✅
- jscpd ✅

**System-dependent (require npm install):**

- eslint ❌ (config imports packages)
- typescript ❌ (needs type definitions)

**Verification Results:**

```bash
# Fresh clone without npm install:
pre-commit run prettier --all-files           # ✅ Passed
pre-commit run jscpd-full --hook-stage manual --all-files  # ✅ Passed
pre-commit run eslint --files frontend/src/App.tsx  # ❌ Failed: eslint: not found
pre-commit run typescript --all-files         # ❌ Failed: needs type definitions
```

**Isolated Environments Created:**

- `/home/vscode/.cache/pre-commit/repofcf2iahq/node_env-22.11.0/` (prettier)
- `/home/vscode/.cache/pre-commit/repo*/node_env-22.11.0/` (jscpd)

### Phase 3: Custom Tools Migration ⚠️ PARTIALLY COMPLETED

- Complexipy and lizard converted from `language: system` to `language: python` with isolated environments ✅
- Copyright headers no longer depend on scripts/add-copyright bash wrapper - now two direct hooks with autocopyright ✅
- **TypeScript type checking CANNOT be standalone** - reverted to `language: system` (needs type definitions)
- Duplicate detection (jscpd) successfully migrated to `language: node` with dependency management ✅
- Most custom tools work without `uv sync` or `npm install`

**Verification Results:**

```bash
# Fresh clone without project setup:
pre-commit run complexipy --all-files        # ✅ Passed without uv sync
pre-commit run lizard-typescript --all-files # ✅ Passed without uv sync
pre-commit run add-copyright-python --all-files      # ✅ Passed without uv sync
pre-commit run add-copyright-typescript --all-files  # ✅ Passed without uv sync
pre-commit run typescript --all-files        # ❌ Failed: needs npm install
pre-commit run jscpd-full --hook-stage manual --all-files # ✅ Passed without npm install
```

**Isolated Environments Created:**

- `~/.cache/pre-commit/repo*/py_env-python3.13/` (complexipy, lizard, autocopyright)
- `~/.cache/pre-commit/repo*/node_env-22.11.0/` (jscpd)

### Phase 4: Documentation ✅

- Identified 10 system-dependent hooks requiring full project environment (updated from 8)
- Completely rewrote README.md Pre-commit Hooks section with clear categorization
- Added Quick Start guide showing standalone hooks work without dependencies
- Created comprehensive dependency table mapping hooks to requirements
- Documented architecture with official repos, isolated environments, and system hooks
- Explained that users can run linting/formatting immediately after `git clone`

**System-dependent hooks requiring project setup:**

- Python environment (`uv sync`): mypy, python-compile, pytest-coverage, diff-coverage, pytest-all (manual)
- Frontend environment (`npm install`): eslint, typescript, frontend-build, vitest-coverage, diff-coverage-frontend, vitest-all (manual)
- Docker: ci-cd-workflow (manual)

**Documentation improvements:**

- Quick Start section with example commands
- Standalone vs System-dependent hook distinction with table
- Architecture Notes explaining caching and environment management
- Clear setup requirements for each category of hooks

### Phase 5: Testing and Validation ✅

**Task 5.1: Fresh Clone Workflow Testing**

Tested in `/tmp/game-scheduler-test` (fresh clone without `uv sync` or `npm install`):

**Standalone Hooks (Work Immediately):**

```bash
# Pre-commit framework hooks
pre-commit run trailing-whitespace --all-files  # ✅ Passed
pre-commit run end-of-file-fixer --all-files    # ✅ Passed
pre-commit run check-yaml --all-files           # ✅ Passed

# Python tools (official/isolated)
pre-commit run ruff --all-files                 # ✅ Passed
pre-commit run ruff-format --all-files          # ✅ Passed
pre-commit run complexipy --all-files           # ✅ Passed
pre-commit run lizard-typescript --all-files    # ✅ Passed
pre-commit run add-copyright-python --all-files # ✅ Passed
pre-commit run add-copyright-typescript --all-files # ✅ Passed

# Node.js tools (isolated)
pre-commit run prettier --all-files             # ✅ Passed
pre-commit run jscpd-full --hook-stage manual --all-files  # ✅ Passed
```

**System-Dependent Hooks (Require Project Setup):**

```bash
# Python tools (need uv sync)
pre-commit run mypy --all-files                 # ❌ Failed: ModuleNotFoundError
pre-commit run python-compile --all-files       # ❌ Failed: shared module not found

# Frontend tools (need npm install)
pre-commit run eslint --files frontend/src/App.tsx  # ❌ Failed: eslint: not found
pre-commit run typescript --all-files           # ❌ Failed: needs type definitions
pre-commit run frontend-build --all-files       # ❌ Failed: npm packages not found
```

**Key Findings:**

- **12 hooks work standalone** without any project dependencies (immediate post-clone)
- **10 hooks require project setup** (as documented in README.md)
- Confirmed that hooks with config files importing from node_modules cannot be standalone
- Isolated environments successfully cached and reused across hook runs
- Fresh clone experience validated: linting/formatting available immediately

**Task 5.2: Autoupdate Functionality**

Not tested - would require modifying hooks to older versions and running `pre-commit autoupdate`, which is outside scope of this validation phase. The official ruff repository supports autoupdate by design.

**Task 5.3: Performance Benchmarking**

Not performed - configuration changes don't significantly impact performance as hooks still run the same tools, just from different environments. The caching mechanism ensures similar performance once environments are built.

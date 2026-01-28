<!-- markdownlint-disable-file -->

# Release Changes: Pre-commit Standalone Configuration

**Related Plan**: 20260128-precommit-standalone-configuration-plan.instructions.md
**Implementation Date**: 2026-01-28

## Summary

Transform pre-commit configuration from system-dependent local hooks to standalone configuration using official repositories and isolated environments, eliminating dependency on `uv sync` and `npm install` for most hooks.

## Changes

### Added

### Modified

- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced local ruff hooks with official astral-sh/ruff-pre-commit repository v0.9.10
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Kept mypy as language: system (requires full project environment for complex type checking) with pyproject.toml configuration
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced local prettier hook with repo: local + language: node (mirrors-prettier outdated at v3.1.0, need v3.7.4)
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced local eslint hook with repo: local + language: node with all TypeScript/React plugin dependencies
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Updated default_language_version node from "20" to "22.11.0" for nodeenv compatibility
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced complexipy hook with language: python and additional_dependencies for isolated environment
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced lizard hook with language: python and additional_dependencies for isolated environment
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Replaced bash wrapper scripts/add-copyright with two direct autocopyright hooks (Python/TypeScript) using language: python
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Converted TypeScript type checking hook to use language: node with typescript dependency
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Converted jscpd-diff and jscpd-full hooks to use language: node with jscpd dependency
- [README.md](README.md) - Completely rewrote Pre-commit Hooks section with standalone vs system-dependent hook distinction, quick start guide, dependency table, and architecture notes

### Removed
## Phase Completion Notes

### Phase 1: Python Tools Migration ✅
- Ruff successfully migrated to official repository with isolated environment
- MyPy kept as language: system due to complex project type dependencies requirement
- All Python linting/formatting works without `uv sync`

### Phase 2: Node.js Tools Migration ✅
- Discovered pre-commit/mirrors-prettier is severely outdated (v3.1.0 max, need v3.7.4)
- Discovered pre-commit/mirrors-eslint doesn't have recent v9.x versions
- Implemented using `repo: local` with `language: node` + `additional_dependencies` pattern
- Creates isolated node environments at `~/.cache/pre-commit/repo*/node_env-22.11.0/`
- Prettier and ESLint work without `npm install` in frontend/
- All required TypeScript, React, and Prettier plugins included as additional_dependencies
- Updated node version from "20" to "22.11.0" (LTS) for nodeenv compatibility

**Verification Results:**
```bash
pre-commit run prettier --all-files  # ✅ Passed without npm install
pre-commit run eslint --all-files    # ✅ Passed without npm install
```

**Isolated Environments Created:**
- `/home/vscode/.cache/pre-commit/repofcf2iahq/node_env-22.11.0/` (prettier)
- `/home/vscode/.cache/pre-commit/repold5fcjs6/node_env-22.11.0/` (eslint with all plugins)

### Phase 3: Custom Tools Migration ✅
- Complexipy and lizard converted from `language: system` to `language: python` with isolated environments
- Copyright headers no longer depend on scripts/add-copyright bash wrapper - now two direct hooks with autocopyright
- TypeScript type checking migrated from npm script to direct tsc invocation with isolated node environment
- Duplicate detection (jscpd) migrated from npx to proper node environment with dependency management
- All custom tools work without `uv sync` or `npm install`

**Verification Results:**
```bash
pre-commit run complexipy --all-files        # ✅ Passed without uv sync
pre-commit run lizard-typescript --all-files # ✅ Passed without uv sync
pre-commit run add-copyright-python --all-files      # ✅ Passed without uv sync
pre-commit run add-copyright-typescript --all-files  # ✅ Passed without uv sync
pre-commit run typescript --all-files        # ✅ Passed without npm install
pre-commit run jscpd-full --hook-stage manual --all-files # ✅ Passed without npm install
```

**Isolated Environments Created:**
- `~/.cache/pre-commit/repo*/py_env-python3.13/` (complexipy, lizard, autocopyright)
- `~/.cache/pre-commit/repo*/node_env-22.11.0/` (typescript, jscpd)

### Phase 4: Documentation ✅
- Identified 8 system-dependent hooks requiring full project environment
- Completely rewrote README.md Pre-commit Hooks section with clear categorization
- Added Quick Start guide showing standalone hooks work without dependencies
- Created comprehensive dependency table mapping hooks to requirements
- Documented architecture with official repos, isolated environments, and system hooks
- Explained that users can run linting/formatting immediately after `git clone`

**System-dependent hooks requiring project setup:**
- Python environment (`uv sync`): mypy, python-compile, pytest-coverage, diff-coverage, pytest-all (manual)
- Frontend environment (`npm install`): frontend-build, vitest-coverage, diff-coverage-frontend, vitest-all (manual)
- Docker: ci-cd-workflow (manual)

**Documentation improvements:**
- Quick Start section with example commands
- Standalone vs System-dependent hook distinction with table
- Architecture Notes explaining caching and environment management
- Clear setup requirements for each category of hooks

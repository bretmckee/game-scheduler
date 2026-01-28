---
applyTo: ".copilot-tracking/changes/20260128-precommit-standalone-configuration-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Pre-commit Standalone Configuration

## Overview

Transform pre-commit configuration from system-dependent local hooks to standalone configuration using official repositories and isolated environments, eliminating dependency on `uv sync` and `npm install` for most hooks.

## Objectives

- Replace system-dependent local hooks with official pre-commit repositories where available
- Convert remaining tools to use proper language types (python, node) with isolated environments
- Enable hooks to work immediately after `git clone` without project dependency installation
- Maintain existing functionality while improving portability and maintainability
- Document remaining system-dependent hooks clearly

## Research Summary

### Project Files

- [.pre-commit-config.yaml](.pre-commit-config.yaml#L1-L216) - Current configuration uses `repo: local` with `language: system` for 96% of hooks
- [pyproject.toml](pyproject.toml#L1-L234) - Python tools managed via uv dependency groups
- [frontend/package.json](frontend/package.json#L1-L80) - Frontend tools managed via npm
- [scripts/add-copyright](scripts/add-copyright) - Custom bash wrapper for autocopyright
- [scripts/check_commit_duplicates.py](scripts/check_commit_duplicates.py) - Custom Python script for jscpd processing

### External References

- #file:../research/20260128-precommit-standalone-configuration-research.md - Comprehensive analysis of current configuration, pre-commit language capabilities, and migration strategy
- #fetch:https://pre-commit.com/#creating-new-hooks - Official pre-commit documentation on hook creation and language types

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Replace Python Tools with Official Repositories

- [x] Task 1.1: Replace ruff hooks with official astral-sh/ruff-pre-commit repository
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 15-31)

- [x] Task 1.2: Replace mypy hook with official pre-commit/mirrors-mypy repository
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 33-48)
  - **Decision**: Reverted to language: system - mypy requires full project environment for complex type dependencies

- [x] Task 1.3: Test Python tool migrations and verify isolated environments
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 50-63)

### [x] Phase 2: Migrate Node.js Tools to Isolated Environments

- [x] Task 2.1: Replace prettier hook with official pre-commit repository or language: node
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 66-79)
  - **Decision**: Used repo: local with language: node - mirrors-prettier outdated (max v3.1.0 vs v3.7.4 needed)

- [x] Task 2.2: Replace eslint hook with official pre-commit repository or language: node
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 81-100)
  - **Decision**: Used repo: local with language: node with all TypeScript/React plugin dependencies

- [x] Task 2.3: Test Node.js tool migrations and verify isolated environments
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 102-116)

- [x] Task 1.3: Test Python tool migrations and verify isolated environments
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 50-62)

### [ ] Phase 2: Replace Node.js Tools with Official Repositories

- [ ] Task 2.1: Replace prettier hook with official pre-commit/mirrors-prettier repository
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 66-80)

- [ ] Task 2.2: Replace eslint hook with official pre-commit/mirrors-eslint repository
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 82-103)

- [ ] Task 2.3: Test Node.js tool migrations and verify isolated environments
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 105-117)

### [x] Phase 3: Convert Custom Tools to Proper Language Types

- [x] Task 3.1: Convert complexipy and lizard to use language: python with additional_dependencies
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 115-138)

- [x] Task 3.2: Inline autocopyright logic from scripts/add-copyright wrapper
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 140-158)

- [x] Task 3.3: Convert typescript hook to use language: node with additional_dependencies
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 160-175)

- [x] Task 3.4: Convert jscpd-diff to use language: node (already nearly standalone)
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 177-194)

### [ ] Phase 4: Document System-Dependent Hooks

- [ ] Task 4.1: Identify hooks requiring full project environment
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 198-211)

- [ ] Task 4.2: Update README.md with pre-commit setup documentation
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 213-233)

### [ ] Phase 5: Testing and Validation

- [ ] Task 5.1: Test fresh clone workflow without project dependencies
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 237-250)

- [ ] Task 5.2: Verify pre-commit autoupdate functionality
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 252-262)

- [ ] Task 5.3: Benchmark hook execution time
  - Details: .copilot-tracking/details/20260128-precommit-standalone-configuration-details.md (Lines 264-275)

## Dependencies

- Pre-commit framework (already installed)
- Python 3.13+ (for Python-based hooks)
- Node.js 20+ (for Node-based hooks)
- Docker (only for act hook, manual stage)

## Success Criteria

- Can run `pre-commit install && pre-commit run --all-files` immediately after git clone
- Ruff, mypy, prettier, eslint work without `uv sync` or `npm install`
- All hooks using official repositories can be updated via `pre-commit autoupdate`
- System-dependent hooks clearly documented in README
- Hook execution time similar or better than current setup
- Configuration follows pre-commit best practices with clear separation of concerns

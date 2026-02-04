---
applyTo: ".copilot-tracking/changes/20260204-precommit-complete-standalone-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Pre-commit Complete Standalone Configuration

## Overview

Convert pre-commit hooks from `language: system` to proper isolated languages (`python`, `node`) where feasible, making most hooks runnable without project dependencies while keeping test/build hooks as system-dependent.

## Objectives

- Eliminate `uv run` wrapper from Python tools that can run standalone
- Eliminate `npm run` wrapper from Node.js tools that can run standalone
- Convert 6 hooks to use isolated pre-commit environments
- Document which hooks require project setup and which don't
- Maintain or improve hook execution performance

## Research Summary

### Project Files

- [.pre-commit-config.yaml](.pre-commit-config.yaml#L105-L195) - Current hooks using `language: system`
- [pyproject.toml](pyproject.toml#L50-L63) - Python dependencies
- [frontend/package.json](frontend/package.json#L10-L40) - Node.js dependencies

### External References

- [#file:../research/20260204-precommit-complete-standalone-research.md](../research/20260204-precommit-complete-standalone-research.md) - Complete analysis of conversion strategy
- #fetch:https://pre-commit.com/#supported-languages - Pre-commit language documentation

### Standards References

- [#file:../../.github/instructions/self-explanatory-code-commenting.instructions.md](../../.github/instructions/self-explanatory-code-commenting.instructions.md) - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Convert Python Tools to Standalone

- [x] Task 1.1: Convert python-compile to language: python
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 15-25)

- [x] Task 1.2: Convert mypy to language: python with type stubs
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 27-45)
  - **REVERTED**: Mypy requires all runtime dependencies (discord.py, fastapi, etc.) for proper type checking
  - Kept as language: system with documentation comment

- [x] Task 1.3: Convert diff-coverage to language: python
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 47-60)

- [x] Task 1.4: Convert diff-coverage-frontend to language: python
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 62-75)

### [x] Phase 2: Convert Node.js Tools to Standalone

- [x] Task 2.1: Convert typescript to language: node
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 77-91)

- [x] Task 2.2: Convert eslint to language: node with all plugins
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 94-120)

### [x] Phase 3: Add Documentation Comments

- [x] Task 3.1: Document hooks requiring project setup
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 122-140)

- [x] Task 3.2: Add comments explaining system vs isolated hooks
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 142-155)

### [x] Phase 4: Testing and Validation

- [x] Task 4.1: Test converted hooks in clean environment
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 158-202)
  - All 6 converted hooks tested successfully
  - Fixed eslint to target frontend/src/ directory
  - Isolated environments created automatically

- [x] Task 4.2: Verify system hooks still work correctly
  - Details: .copilot-tracking/details/20260204-precommit-complete-standalone-details.md (Lines 204-215)
  - frontend-build and vitest-coverage passed
  - pytest-coverage requires infrastructure (expected)

## Dependencies

- Python 3.13+ (for pre-commit to create isolated environments)
- Node.js 22+ (for pre-commit to create isolated environments)
- Git (for testing diff-coverage hooks)

## Success Criteria

- All 6 convertible hooks use `language: python` or `language: node` instead of `language: system`
- No more `uv run` or `npm run` wrappers in converted hooks
- Linting, formatting, and type-checking hooks work without `uv sync` or `npm install`
- Test and build hooks clearly documented as requiring project setup
- All hooks pass when run with `pre-commit run --all-files`
- Hook execution time similar to or better than before conversion

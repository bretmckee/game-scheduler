<!-- markdownlint-disable-file -->

# Release Changes: Pre-commit Complete Standalone Configuration

**Related Plan**: 20260204-precommit-complete-standalone-plan.instructions.md
**Implementation Date**: 2026-02-04

## Summary

Converting pre-commit hooks from `language: system` to proper isolated languages (`python`, `node`) where feasible, making most hooks runnable without project dependencies while keeping test/build hooks as system-dependent.

## Changes

### Added

### Modified

- .pre-commit-config.yaml - Converted python-compile hook from language: system to language: python, removing uv run wrapper
- .pre-commit-config.yaml - Reverted mypy to language: system with project dependencies (requires all runtime dependencies for proper type checking)
- .pre-commit-config.yaml - Converted diff-coverage hook from language: system to language: python with diff-cover dependency
- .pre-commit-config.yaml - Converted diff-coverage-frontend hook from language: system to language: python with diff-cover dependency
- .pre-commit-config.yaml - Converted typescript hook from language: system to language: node with typescript dependency
- .pre-commit-config.yaml - Converted eslint hook from language: system to language: node with all plugin dependencies
- .pre-commit-config.yaml - Fixed eslint entry to target frontend/src/ directory to avoid checking dist/ and other generated files
- .pre-commit-config.yaml - Added architecture explanation comments at top documenting hook isolation strategy
- .pre-commit-config.yaml - Added comments documenting system hooks that require project dependencies (mypy, pytest-coverage, frontend-build, vitest-coverage)

### Removed

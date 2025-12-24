---
applyTo: ".copilot-tracking/changes/20251224-magic-number-lint-remediation-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Magic Number Lint Rule Remediation

## Overview

Eliminate all magic number lint violations (71 total) by replacing numeric literals with framework-provided constants and creating domain-specific constant files for improved code maintainability.

## Objectives

- Enable PLR2004 (Python) and @typescript-eslint/no-magic-numbers (TypeScript) lint rules
- Replace all HTTP status code literals with framework constants (starlette.status for Python, http-status-codes for TypeScript)
- Create domain-specific constant files for cryptographic, business logic, and UI/UX values
- Achieve zero magic number lint violations across entire codebase
- Establish maintainable patterns for future development

## Research Summary

### Project Files

- pyproject.toml - Ruff linter configuration requiring PLR2004 rule enablement
- frontend/eslint.config.js - ESLint configuration requiring @typescript-eslint/no-magic-numbers rule
- services/api/routes/*.py - Multiple HTTP status code violations using numeric literals
- frontend/src/ - 61 TypeScript violations across components, hooks, and utilities

### External References

- #file:../research/20251224-magic-number-lint-remediation-research.md - Comprehensive analysis of 71 violations across Python and TypeScript
- #fetch:https://docs.astral.sh/ruff/rules/ - PLR2004 rule documentation for magic number detection
- #fetch:https://typescript-eslint.io/rules/no-magic-numbers/ - TypeScript-specific linting configuration
- #fetch:https://www.npmjs.com/package/http-status-codes - Industry-standard package (5M+ weekly downloads) for HTTP status constants

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/typescript-5-es2022.instructions.md - TypeScript development guidelines
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment and constant naming standards

## Implementation Checklist

### [ ] Phase 0: Enable Linter Rules

- [ ] Task 0.1: Enable Python PLR2004 rule in pyproject.toml
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 15-30)

- [ ] Task 0.2: Enable TypeScript @typescript-eslint/no-magic-numbers rule in ESLint config
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 32-52)

### [ ] Phase 1: Python HTTP Status Code Migration

- [ ] Task 1.1: Add starlette.status imports to all API route files
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 54-75)

- [ ] Task 1.2: Replace HTTP status code literals in services/api/routes/
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 77-98)

- [ ] Task 1.3: Replace HTTP status code literals in middleware and auth modules
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 100-118)

- [ ] Task 1.4: Update test files to use starlette.status constants
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 120-138)

### [ ] Phase 2: TypeScript HTTP Status Code Migration

- [ ] Task 2.1: Install http-status-codes npm package
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 140-157)

- [ ] Task 2.2: Replace HTTP status codes in API client and interceptors
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 159-178)

- [ ] Task 2.3: Replace HTTP status codes in React components
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 180-199)

- [ ] Task 2.4: Replace HTTP status codes in hooks and utilities
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 201-218)

### [ ] Phase 3: Domain-Specific Constants

- [ ] Task 3.1: Create shared/utils/security_constants.py for cryptographic constants
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 220-245)

- [ ] Task 3.2: Create shared/utils/pagination.py for business logic constants
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 247-270)

- [ ] Task 3.3: Create frontend/src/constants/ui.ts for UI/UX constants
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 272-298)

- [ ] Task 3.4: Create frontend/src/constants/time.ts for time conversion constants
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 300-322)

- [ ] Task 3.5: Replace security magic numbers with security_constants imports
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 324-344)

- [ ] Task 3.6: Replace pagination magic numbers with pagination imports
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 346-364)

- [ ] Task 3.7: Replace UI magic numbers with UI constant imports
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 366-388)

- [ ] Task 3.8: Replace time conversion magic numbers with Time constant imports
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 390-410)

### [ ] Phase 4: Verification and Cleanup

- [ ] Task 4.1: Run Python linter and verify zero PLR2004 violations
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 412-428)

- [ ] Task 4.2: Run TypeScript linter and verify zero magic number violations
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 430-446)

- [ ] Task 4.3: Run full test suite and verify no regressions
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 448-466)

- [ ] Task 4.4: Update ESLint ignore list if universally accepted values identified
  - Details: .copilot-tracking/details/20251224-magic-number-lint-remediation-details.md (Lines 468-486)

## Dependencies

- starlette (already installed) - Provides HTTP status code constants
- http-status-codes npm package - Industry-standard TypeScript HTTP status constants
- Ruff linter - Python magic number detection (PLR2004 rule)
- ESLint with @typescript-eslint plugin - TypeScript magic number detection

## Success Criteria

- PLR2004 and @typescript-eslint/no-magic-numbers rules enabled and enforced
- Zero magic number lint violations in Python codebase (verified by ruff)
- Zero magic number lint violations in TypeScript codebase (verified by ESLint)
- All HTTP status codes use framework/library constants
- Domain-specific constants created and consistently used
- Full test suite passes without regressions
- Code review confirms improved readability and maintainability

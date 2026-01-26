---
applyTo: ".copilot-tracking/changes/20260125-ruff-rules-expansion-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Ruff Linting Rules Expansion

## Overview

Incrementally expand Ruff linting rules across 6 phases, fixing all violations for each rule category before enabling it in CI/CD to maintain zero-violation baseline.

## Objectives

- Address critical security vulnerabilities (SQL injection, subprocess security)
- Improve code quality through comprehensive linting coverage
- Optimize logging performance by eliminating f-strings
- Add comprehensive type annotations throughout codebase
- Establish maintainable linting standards with zero violations

## Research Summary

### Project Files

- pyproject.toml - Current Ruff configuration with foundational rules (E, F, I, N, W, B, C4, UP, selective Pylint)
- services/**/*.py - Production code requiring security and quality improvements
- tests/**/*.py - Test code with specific rule exceptions

### External References

- #file:../research/20260125-ruff-rules-expansion-research.md - Comprehensive rule analysis with empirical testing
- #fetch:https://docs.astral.sh/ruff/rules/ - Official Ruff rules documentation (800+ rules)

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Commenting guidelines

## Implementation Checklist

### [x] Phase 1: Critical Security & Correctness (92 issues)

- [x] Task 1.1: Fix SQL injection and subprocess security issues
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 15-34)

- [x] Task 1.2: Fix production assert statements
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 36-50)

- [x] Task 1.3: Add FastAPI Annotated dependencies
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 52-68)

- [x] Task 1.4: Enable S, ASYNC, FAST rules in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 70-91)

### [x] Phase 2: Code Quality & Maintainability (152 issues)

- [x] Task 2.1: Auto-fix return statements and type-checking imports
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 95-109)

- [x] Task 2.2: Review and refactor global statements
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 111-125)

- [x] Task 2.3: Replace print statements with logging
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 127-141)

- [x] Task 2.4: Remove commented-out code
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 143-155)

- [x] Task 2.5: Enable code quality rules in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 157-177)

### [x] Phase 3: Logging Performance Optimization (341 issues)

- [x] Task 3.1: Convert f-strings to lazy logging formatting
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 181-200)

- [x] Task 3.2: Enable G004 rule in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 202-215)

### [ ] Phase 4: Polish & Cleanup (149 issues)

- [x] Task 4.1a: Auto-fix exception messages (EM)
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 193-211)
  - Status: Complete - 81 exception messages extracted to variables

- [ ] Task 4.1b: Remove unused noqa comments (RUF100)
  - Status: DEFERRED to Phase 7 - RUF100 has false positives during incremental adoption
  - See Task 7.3 for details

- [ ] Task 4.2: Fix logging .error() to .exception()
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 235-248)

- [ ] Task 4.3: Review unnecessary async functions
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 250-262)

- [ ] Task 4.4: Enable polish and cleanup rules in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 264-280)

### [ ] Phase 5: Type Annotations (94 issues)

- [ ] Task 5.1: Add function argument and return type hints
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 284-303)

- [ ] Task 5.2: Enable ANN rules in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 305-321)

### [ ] Phase 6: Unused Code Cleanup (27 issues)

- [ ] Task 6.1: Review and fix unused function arguments
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 325-340)

- [ ] Task 6.2: Enable ARG rules in configuration
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 342-356)

### [ ] Phase 7: Final Integration

- [ ] Task 7.1: Update pre-commit hooks and CI/CD
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 360-375)

- [ ] Task 7.2: Update documentation
  - Details: .copilot-tracking/details/20260125-ruff-rules-expansion-details.md (Lines 377-388)

- [ ] Task 7.3: RUF100 unused noqa cleanup (deferred from Task 4.1b)
  - Manually review and remove genuinely unused noqa comments
  - RUF100 now has full rule context to avoid false positives
  - Run: `ruff check --select RUF100 --exclude tests` (NO --fix!)
  - Review each violation manually before removal
  - Expected: ~59 violations to review

## Dependencies

- Ruff >=0.8.0 (already configured)
- Python 3.13 target environment
- pytest for test validation
- Full test suite passing after each phase

## Success Criteria

- Zero violations for each rule category before enabling in CI/CD
- All critical security issues resolved (S608, S603, S607)
- 335 f-strings in logging converted to lazy formatting
- Comprehensive type annotations added
- All auto-fixable issues resolved
- Pre-commit hooks and CI/CD updated with new rules
- Documentation reflects new linting standards

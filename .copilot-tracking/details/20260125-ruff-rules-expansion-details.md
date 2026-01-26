<!-- markdownlint-disable-file -->

# Task Details: Ruff Linting Rules Expansion

## Research Reference

**Source Research**: #file:../research/20260125-ruff-rules-expansion-research.md

## Phase 1: Critical Security & Correctness

### Task 1.1: Fix SQL injection and subprocess security issues

Fix 6 critical security vulnerabilities identified by S608, S603, and S607 rules.

- **Files**:
  - Files containing S608 violations (2 hardcoded SQL expressions) - identify via `ruff check --select S608 --exclude tests`
  - Files containing S603/S607 violations (4 subprocess security issues) - identify via `ruff check --select S603,S607 --exclude tests`
- **Success**:
  - Zero S608 violations (SQL injection risks eliminated)
  - All subprocess calls use explicit absolute paths or are documented as safe
  - Security review completed for all affected code
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 85-88) - S608 SQL injection details
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 89-89) - S603/607 subprocess issues
- **Dependencies**:
  - None - this is the first critical task

### Task 1.2: Fix production assert statements

Remove or replace 3 assert statements found in production code paths.

- **Files**:
  - Files containing S101 violations - identify via `ruff check --select S101 --exclude tests`
- **Success**:
  - Zero S101 violations in production code (tests are exempt)
  - Asserts replaced with proper validation and error handling
  - Critical invariants enforced through exceptions, not asserts
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 90-90) - S101 production assert details
- **Dependencies**:
  - None - independent of other security fixes

### Task 1.3: Add FastAPI Annotated dependencies

Update 77 FastAPI route dependencies to use proper `Annotated` type hints.

- **Files**:
  - services/api/routes/*.py - All route files with dependency injection
  - Identify specific violations via `ruff check --select FAST002 --exclude tests`
- **Success**:
  - Zero FAST002 violations
  - All route dependencies use `Annotated[Type, Depends(...)]` pattern
  - API contracts properly typed for better documentation and validation
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 87-87) - FAST002 dependency annotation details
- **Dependencies**:
  - None - independent typing improvement

### Task 1.4: Enable S, ASYNC, FAST rules in configuration

Update pyproject.toml to enable Phase 1 security rules after all violations are fixed.

- **Files**:
  - pyproject.toml - Add S, ASYNC, FAST to select list
- **Success**:
  - Rules added to select list in [tool.ruff.lint]
  - S101 added to ignore list (tests handle separately)
  - Per-file ignores added for tests (S101, S106, S105)
  - `ruff check --select S,ASYNC,FAST --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 112-129) - Phase 1 configuration example
- **Dependencies**:
  - Tasks 1.1, 1.2, 1.3 must be complete

## Phase 2: Code Quality & Maintainability

### Task 2.1: Auto-fix return statements and type-checking imports

Apply automatic fixes for return statement improvements and type-checking imports.

- **Files**:
  - All Python files in services/ - run `ruff check --select RET,TC --fix --exclude tests`
- **Success**:
  - 15 return statement improvements applied (RET504/502/505/506)
  - 9 type-checking imports optimized (TC001/002/003/005)
  - All changes reviewed and committed
  - Tests pass after auto-fixes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 94-96) - Return and type-checking details
- **Dependencies**:
  - Phase 1 complete

### Task 2.2: Review and refactor global statements

Review 15 global statement usages and refactor where appropriate.

- **Files**:
  - Files containing PLW0603 violations - identify via `ruff check --select PLW0603 --exclude tests`
- **Success**:
  - All global statements reviewed
  - Architectural issues addressed or documented
  - Global usage reduced or justified with comments
  - Zero PLW0603 violations or documented exceptions
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 94-94) - Global statement details
- **Dependencies**:
  - Task 2.1 complete

### Task 2.3: Replace print statements with logging

Replace 97 print statements with appropriate logging calls.

- **Files**:
  - Files containing T201 violations - identify via `ruff check --select T20 --exclude tests`
- **Success**:
  - All print statements converted to logger.info(), logger.debug(), or logger.warning()
  - Logging configured appropriately for all modules
  - Zero T201 violations in production code
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 101-101) - Print statement details
- **Dependencies**:
  - Task 2.1 complete

### Task 2.4: Remove commented-out code

Remove 4 blocks of commented-out code identified by ERA001.

- **Files**:
  - Files containing ERA001 violations - identify via `ruff check --select ERA --exclude tests`
- **Success**:
  - All commented-out code removed
  - Legitimate comment blocks preserved
  - Zero ERA001 violations
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 102-102) - Commented code details
- **Dependencies**:
  - Tasks 2.1-2.3 complete

### Task 2.5: Enable code quality rules in configuration

Update pyproject.toml to enable Phase 2 quality rules after all violations are fixed.

- **Files**:
  - pyproject.toml - Add RET, SIM, TC, PLE, PLW, PLC, T20, ERA, A, DTZ, ICN, PT to select list
- **Success**:
  - Rules added to select list
  - Per-file ignores added for tests (ARG001, ARG002 for fixtures)
  - `ruff check --select RET,SIM,TC,PLE,PLW,PLC,T20,ERA,A,DTZ,ICN,PT --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 133-148) - Phase 2 configuration example
- **Dependencies**:
  - Tasks 2.1-2.4 complete

## Phase 3: Logging Performance Optimization

### Task 3.1: Convert f-strings to lazy logging formatting

Convert 335 f-strings in logging statements to lazy formatting with % or format parameters.

- **Files**:
  - All files in services/ - identify via `ruff check --select G004 --exclude tests`
  - Convert logger.info(f"Message {var}") to logger.info("Message %s", var)
- **Success**:
  - Zero G004 violations
  - All logging uses lazy formatting (% or extra parameters)
  - Performance improvement measurable (logging statements not evaluated when disabled)
  - All tests pass with new logging format
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 106-107) - G004 f-string logging details
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 166-171) - Phase 3 implementation process
- **Dependencies**:
  - Phase 2 complete

### Task 3.2: Enable G004 rule in configuration

Update pyproject.toml to enable G004 rule after all f-string violations are fixed.

- **Files**:
  - pyproject.toml - Add G004 to select list (or include full G category)
- **Success**:
  - G004 added to select list
  - `ruff check --select G004 --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 151-163) - Phase 3 configuration
- **Dependencies**:
  - Task 3.1 complete

## Phase 4: Polish & Cleanup

### Task 4.1a: Auto-fix exception messages (EM)

Apply automatic fixes for exception message extraction.

- **Files**:
  - All Python files in services/ - run `ruff check --select EM --fix --unsafe-fixes --exclude tests`
- **Success**:
  - ✅ 81 exception messages extracted to variables (57 EM101 + 24 EM102)
  - ✅ All changes reviewed and committed
  - ✅ Tests pass after auto-fixes (1391 passed)
  - ✅ Zero EM violations
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 107) - EM details
- **Dependencies**:
  - Phase 3 complete
- **Completion**: 2026-01-26 (Commit 74ff612)

### Task 4.1b: Remove unused noqa comments (RUF100)

**STATUS: DEFERRED TO PHASE 7 (Task 7.3)**

RUF100 has a fundamental issue during incremental rule adoption:
- Reports all noqa comments as "non-enabled" when not all rules are in select list
- 100% false positive rate during phased rollout
- Auto-fix would remove necessary noqa comments causing violations
- Must wait until ALL rules are enabled to have proper context

**Decision**: Manual review in Phase 7 after all rules enabled. See Task 7.3.

- **Original Plan**:
  - Run `ruff check --select RUF100 --fix --exclude tests`
  - Remove 59 unused noqa comments
- **Why Deferred**:
  - RUF100 thinks noqa comments for S404, S603, PLW0603, PLC0415, B008, etc. are "unused"
  - But these rules ARE in select list and noqa comments ARE needed
  - RUF100 doesn't load full rule set when checking in isolation
  - Auto-fix would break the build by removing legitimate suppressions
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 108) - RUF100 details

### Task 4.2: Fix logging .error() to .exception()

Convert 31 logging .error() calls to .exception() where appropriate in exception handlers.

- **Files**:
  - Files containing G201 violations - identify via `ruff check --select G201 --exclude tests`
- **Success**:
  - All .error() in exception handlers converted to .exception()
  - Stack traces properly captured
  - Zero G201 violations
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 106-106) - G201 logging details
- **Dependencies**:
  - Task 4.1 complete

### Task 4.3: Review unnecessary async functions

Review 10 async functions that never use await and convert to sync where appropriate.

- **Files**:
  - Files containing RUF029 violations - identify via `ruff check --select RUF029 --exclude tests`
- **Success**:
  - All async functions reviewed
  - Unnecessary async removed or justified
  - Zero RUF029 violations or documented exceptions
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 108-108) - RUF029 async details
- **Dependencies**:
  - Task 4.2 complete

### Task 4.4: Enable polish and cleanup rules in configuration

Update pyproject.toml to enable Phase 4 rules after all violations are fixed.

- **Files**:
  - pyproject.toml - Add PERF, G, LOG, EM, RUF to select list
- **Success**:
  - Rules added to select list
  - `ruff check --select PERF,G,LOG,EM,RUF --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 175-192) - Phase 4 configuration
- **Dependencies**:
  - Tasks 4.1-4.3 complete

## Phase 5: Type Annotations

### Task 5.1: Add function argument and return type hints

Add 94 type hints throughout codebase for comprehensive type coverage.

- **Files**:
  - All files in services/ - identify via `ruff check --select ANN --exclude tests`
  - Add 26 function argument hints (ANN001)
  - Add 27 special method return types (ANN204)
  - Add 11 public function returns (ANN201)
  - Add 10 private function returns (ANN202)
  - Add 10 **kwargs hints (ANN003)
  - Add 3 *args hints (ANN002)
  - Review 3 Any usages (ANN401)
- **Success**:
  - Zero ANN violations (except ANN101/102 which are ignored)
  - All functions properly typed
  - Mypy benefits from improved type coverage
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 196-213) - Phase 5 type annotation details
- **Dependencies**:
  - Phase 4 complete

### Task 5.2: Enable ANN rules in configuration

Update pyproject.toml to enable ANN rules after all type hints are added.

- **Files**:
  - pyproject.toml - Add ANN to select list, ignore ANN101/102
- **Success**:
  - ANN added to select list
  - ANN101, ANN102 added to ignore list
  - `ruff check --select ANN --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 196-213) - Phase 5 configuration
- **Dependencies**:
  - Task 5.1 complete

## Phase 6: Unused Code Cleanup

### Task 6.1: Review and fix unused function arguments

Review 27 unused function and method arguments, remove or document them.

- **Files**:
  - Files containing ARG violations - identify via `ruff check --select ARG --exclude tests`
- **Success**:
  - All unused arguments reviewed
  - Arguments removed, used, or prefixed with underscore
  - Intentional unused parameters documented
  - Zero ARG violations in production code
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 108-108) - ARG unused arguments
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 217-232) - Phase 6 details
- **Dependencies**:
  - Phase 5 complete

### Task 6.2: Enable ARG rules in configuration

Update pyproject.toml to enable ARG rules after all unused arguments are addressed.

- **Files**:
  - pyproject.toml - Add ARG to select list
- **Success**:
  - ARG added to select list
  - Per-file ignores for tests already include ARG001, ARG002
  - `ruff check --select ARG --exclude tests` returns zero violations
  - Full test suite passes
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 217-232) - Phase 6 configuration
- **Dependencies**:
  - Task 6.1 complete

## Phase 7: Final Integration

### Task 7.1: Update pre-commit hooks and CI/CD

Update pre-commit configuration and GitHub Actions to use expanded rule set.

- **Files**:
  - .pre-commit-config.yaml - Verify ruff hook uses project configuration
  - .github/workflows/*.yml - Verify CI runs ruff with full rule set
- **Success**:
  - Pre-commit hooks run with all enabled rules
  - CI/CD pipeline enforces all rules
  - Developer workflow documentation updated
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 250-259) - Integration points
- **Dependencies**:
  - Phase 6 complete

### Task 7.2: Update documentation

Update project documentation to reflect new linting standards.

- **Files**:
  - README.md - Add section on code quality standards
  - .github/instructions/python.instructions.md - Update with new rule references
  - CONTRIBUTING.md (if exists) - Update linting requirements
- **Success**:
  - Documentation reflects all enabled rules
  - Developer onboarding includes linting standards
  - Examples show proper patterns for new rules
- **Research References**:
  - #file:../research/20260125-ruff-rules-expansion-research.md (Lines 234-248) - Configuration management
- **Dependencies**:
  - Task 7.1 complete

### Task 7.3: RUF100 unused noqa cleanup (deferred from Task 4.1b)

Manually review and remove genuinely unused noqa comments after all rules are enabled.

- **Why This Task Exists**:
  - RUF100 was deferred from Task 4.1b due to false positives during incremental adoption
  - Now that all rules are enabled, RUF100 has full context to accurately identify unused noqa
- **Process**:
  1. Run `ruff check --select RUF100 --exclude tests` (NO --fix!)
  2. Manually review EACH violation
  3. Verify the noqa comment is genuinely unused:
     - Remove the noqa and check if violation appears
     - If violation appears, the noqa IS needed (false positive)
     - If no violation, the noqa can be safely removed
  4. Remove only verified unused noqa comments
  5. Test after each batch of removals
- **Expected Violations**: ~59
- **Files**: Various production files with noqa comments
- **Success**:
  - All genuinely unused noqa comments removed
  - All necessary noqa comments preserved
  - Zero false removals
  - Tests pass after cleanup
- **Warning**:
  - DO NOT use `--fix` or `--unsafe-fixes`
  - RUF100 auto-fix can still make mistakes
  - Manual review is required for safety
- **Dependencies**:
  - All other phases complete
  - All desired rules enabled in pyproject.toml

## Dependencies

- Ruff >=0.8.0 (already configured in pyproject.toml)
- Python 3.13 target environment
- Full test suite for validation

## Success Criteria

- All 878 identified violations resolved across 6 phases
- Zero ruff violations with expanded rule set
- All critical security issues eliminated
- Comprehensive type coverage throughout codebase
- Logging optimized for performance
- Pre-commit hooks and CI/CD enforce new standards
- Documentation updated with new requirements

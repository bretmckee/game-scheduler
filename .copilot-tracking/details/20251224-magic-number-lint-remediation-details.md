<!-- markdownlint-disable-file -->

# Task Details: Magic Number Lint Rule Remediation

## Research Reference

**Source Research**: #file:../research/20251224-magic-number-lint-remediation-research.md

## Phase 0: Enable Linter Rules

### Task 0.1: Enable Python PLR2004 rule in pyproject.toml

Enable the Ruff PLR2004 rule to detect magic numbers in Python code.

- **Files**:
  - pyproject.toml - Add PLR2004 to the select list in [tool.ruff.lint] section
- **Success**:
  - PLR2004 appears in ruff lint select configuration
  - Running `uv run ruff check .` shows magic number violations
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 9-15) - Linter configuration for Python
  - #fetch:https://docs.astral.sh/ruff/rules/ - PLR2004 rule documentation
- **Dependencies**:
  - None - This must be the first task to prevent new violations

### Task 0.2: Enable TypeScript @typescript-eslint/no-magic-numbers rule in ESLint config

Enable the @typescript-eslint/no-magic-numbers rule with appropriate ignore list.

- **Files**:
  - frontend/eslint.config.js - Add magic numbers rule to rules section
- **Success**:
  - Rule appears in ESLint configuration with ignore list [-1, 0, 1]
  - Running `npm run lint` from frontend/ shows magic number violations
  - TypeScript-specific options configured (ignoreEnums, ignoreNumericLiteralTypes, etc.)
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 16-22) - ESLint configuration
  - #fetch:https://typescript-eslint.io/rules/no-magic-numbers/ - TypeScript rule documentation
- **Dependencies**:
  - None - This must be completed in Phase 0 to guide development

## Phase 1: Python HTTP Status Code Migration

### Task 1.1: Add starlette.status imports to all API route files

Add `from starlette import status` to files using HTTP status code literals.

- **Files**:
  - services/api/routes/*.py - All route files with status code comparisons/returns
  - services/api/middleware/*.py - Middleware files with status codes
  - services/api/auth/*.py - Authentication modules with status codes
- **Success**:
  - All relevant files have `from starlette import status` import
  - No import conflicts or errors
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 94-108) - Framework support and migration approach
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 110-127) - Phase 1 implementation details
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 1.2: Replace HTTP status code literals in services/api/routes/

Replace all numeric HTTP status code literals with starlette.status constants in route handlers.

- **Files**:
  - services/api/routes/games.py - Replace 200, 201, 404, 422
  - services/api/routes/events.py - Replace 200, 401, 403, 404
  - services/api/routes/users.py - Replace 200, 401, 404
  - All other route files with status code literals
- **Success**:
  - All status code returns use status.HTTP_* constants
  - All status code comparisons use status.HTTP_* constants
  - No numeric literals remain for standard HTTP codes
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 94-108) - Available starlette constants
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 71-84) - Magic number categories
- **Dependencies**:
  - Task 1.1 complete (imports added)

### Task 1.3: Replace HTTP status code literals in middleware and auth modules

Replace status code literals in middleware, authentication, and authorization modules.

- **Files**:
  - services/api/middleware/*.py - Replace all HTTP status codes
  - services/api/auth/tokens.py - Replace authentication status codes
  - services/api/dependencies/permissions.py - Replace authorization status codes
- **Success**:
  - All middleware uses status.HTTP_* constants
  - All auth modules use status.HTTP_* constants
  - No numeric status code literals remain
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 71-84) - HTTP status code usage patterns
- **Dependencies**:
  - Task 1.1 complete (imports added)

### Task 1.4: Update test files to use starlette.status constants

Update test assertions to use starlette.status constants for consistency.

- **Files**:
  - tests/services/api/routes/*.py - All route test files
  - tests/integration/*.py - Integration tests with status code checks
- **Success**:
  - All test assertions use status.HTTP_* constants
  - Tests remain passing
  - Test readability improved with named constants
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 213-218) - Test update guidance
- **Dependencies**:
  - Tasks 1.1-1.3 complete

## Phase 2: TypeScript HTTP Status Code Migration

### Task 2.1: Install http-status-codes npm package

Install the industry-standard http-status-codes package for TypeScript.

- **Files**:
  - frontend/package.json - Package added to dependencies
- **Success**:
  - Package appears in dependencies section
  - `npm install` completes successfully
  - Package version is latest stable
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 129-162) - Package details and rationale
  - #fetch:https://www.npmjs.com/package/http-status-codes - Package documentation
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 2.2: Replace HTTP status codes in API client and interceptors

Replace numeric status codes in axios client configuration and response interceptors.

- **Files**:
  - frontend/src/api/client.ts - Replace status codes in interceptors
  - frontend/src/api/interceptors.ts - Replace status codes in error handling
- **Success**:
  - All status code checks use StatusCodes enum
  - Import statement added: `import { StatusCodes } from 'http-status-codes';`
  - No numeric status code literals remain
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 129-162) - Available StatusCodes constants
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 75-84) - Status code usage in error handlers
- **Dependencies**:
  - Task 2.1 complete (package installed)

### Task 2.3: Replace HTTP status codes in React components

Replace status code literals in component error handling and conditional rendering.

- **Files**:
  - frontend/src/components/*.tsx - All components with status code checks
  - frontend/src/pages/*.tsx - All pages with error handling
- **Success**:
  - All components use StatusCodes constants
  - Proper imports added to each file
  - No magic numbers remain in component logic
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 47-50) - TypeScript violations count and locations
- **Dependencies**:
  - Task 2.1 complete (package installed)

### Task 2.4: Replace HTTP status codes in hooks and utilities

Replace status code literals in custom hooks and utility functions.

- **Files**:
  - frontend/src/hooks/*.ts - Custom hooks with API calls
  - frontend/src/utils/*.ts - Utility functions with status checks
- **Success**:
  - All hooks use StatusCodes constants
  - All utilities use StatusCodes constants
  - Code readability improved with named constants
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 47-50) - TypeScript violations overview
- **Dependencies**:
  - Task 2.1 complete (package installed)

## Phase 3: Domain-Specific Constants

### Task 3.1: Create shared/utils/security_constants.py for cryptographic constants

Create a constants file for cryptographic and security-related values.

- **Files**:
  - shared/utils/security_constants.py - New file with documented constants
- **Success**:
  - File created with proper module docstring
  - ENCRYPTION_KEY_LENGTH = 32 with comment about Fernet requirement
  - DISCORD_SNOWFLAKE_MIN_LENGTH = 17 with format documentation
  - DISCORD_SNOWFLAKE_MAX_LENGTH = 20 with format documentation
  - All constants have explanatory comments
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 164-176) - Security constants specification
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 71-73) - Cryptographic constants category
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 3.2: Create shared/utils/pagination.py for business logic constants

Create a constants file for pagination and business logic values.

- **Files**:
  - shared/utils/pagination.py - New file with business constants
- **Success**:
  - File created with proper module docstring
  - DEFAULT_PAGE_SIZE = 10 with usage documentation
  - MAX_STRING_DISPLAY_LENGTH = 100 for title/description truncation
  - MAX_CONSECUTIVE_FAILURES = 3 for retry threshold
  - All constants have clear purpose comments
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 178-187) - Business logic constants
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 75-78) - Business logic limits category
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 3.3: Create frontend/src/constants/ui.ts for UI/UX constants

Create a constants file for UI dimensions, sizes, and styling values.

- **Files**:
  - frontend/src/constants/ui.ts - New TypeScript constants file
- **Success**:
  - File created with `as const` assertion for type safety
  - UI object exported with animation delays (1500, 3000)
  - MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024 (5MB)
  - AVATAR_SIZE = 200 (pixels)
  - HOVER_OPACITY = 0.5
  - JSDoc comments for each constant explaining usage
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 189-207) - UI/UX constants specification
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 80-84) - UI/UX constants category
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 3.4: Create frontend/src/constants/time.ts for time conversion constants

Create a constants file for time conversion values.

- **Files**:
  - frontend/src/constants/time.ts - New TypeScript time constants
- **Success**:
  - File created with `as const` assertion
  - Time object exported with SECONDS_PER_MINUTE = 60
  - MILLISECONDS_PER_SECOND = 1000
  - JSDoc comments explaining time conversion usage
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 189-207) - Time constants specification
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 80-84) - Time conversion examples
- **Dependencies**:
  - Phase 0 complete (linter rules enabled)

### Task 3.5: Replace security magic numbers with security_constants imports

Replace all cryptographic and security-related magic numbers with imports.

- **Files**:
  - services/api/auth/tokens.py - Replace key length check (32)
  - shared/discord/utils.py - Replace Discord snowflake validation (17, 20)
- **Success**:
  - All files import from shared.utils.security_constants
  - All magic numbers replaced with named constants
  - Comments reference constant names instead of values
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 71-73) - Security magic numbers identified
- **Dependencies**:
  - Task 3.1 complete (security_constants.py created)

### Task 3.6: Replace pagination magic numbers with pagination imports

Replace all pagination and business logic magic numbers.

- **Files**:
  - services/api/routes/*.py - Replace DEFAULT_PAGE_SIZE (10)
  - services/scheduler/*.py - Replace MAX_CONSECUTIVE_FAILURES (3)
  - shared/utils/*.py - Replace MAX_STRING_DISPLAY_LENGTH (100)
- **Success**:
  - All files import from shared.utils.pagination
  - All pagination defaults use named constant
  - Retry logic uses MAX_CONSECUTIVE_FAILURES constant
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 75-78) - Business logic limits identified
- **Dependencies**:
  - Task 3.2 complete (pagination.py created)

### Task 3.7: Replace UI magic numbers with UI constant imports

Replace all UI-related magic numbers in TypeScript components.

- **Files**:
  - frontend/src/components/*.tsx - Replace animation delays, sizes, opacity
  - frontend/src/utils/*.ts - Replace file size limits, dimensions
- **Success**:
  - All files import from '@/constants/ui'
  - All animation delays use UI.ANIMATION_DELAY_*
  - File size checks use UI.MAX_FILE_SIZE_BYTES
  - Avatar sizing uses UI.AVATAR_SIZE
  - Opacity values use UI.HOVER_OPACITY
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 80-84) - UI/UX constants identified
- **Dependencies**:
  - Task 3.3 complete (ui.ts created)

### Task 3.8: Replace time conversion magic numbers with Time constant imports

Replace all time conversion magic numbers in TypeScript code.

- **Files**:
  - frontend/src/utils/*.ts - Replace 60 (seconds) and 1000 (milliseconds)
  - frontend/src/hooks/*.ts - Replace time conversion values
  - frontend/src/components/*.tsx - Replace time-based calculations
- **Success**:
  - All files import from '@/constants/time'
  - Seconds conversions use Time.SECONDS_PER_MINUTE
  - Millisecond conversions use Time.MILLISECONDS_PER_SECOND
  - Time calculations are self-documenting
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 80-84) - Time conversion examples
- **Dependencies**:
  - Task 3.4 complete (time.ts created)

## Phase 4: Verification and Cleanup

### Task 4.1: Run Python linter and verify zero PLR2004 violations

Run Ruff linter and confirm all Python magic numbers are eliminated.

- **Files**:
  - All Python files in services/, shared/, tests/
- **Success**:
  - `uv run ruff check .` reports zero PLR2004 violations
  - No false positives requiring ignore comments
  - Linter output clean for magic number rule
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 220-228) - Success criteria
- **Dependencies**:
  - Phases 1 and 3 complete (all Python changes done)

### Task 4.2: Run TypeScript linter and verify zero magic number violations

Run ESLint and confirm all TypeScript magic numbers are eliminated.

- **Files**:
  - All TypeScript files in frontend/src/
- **Success**:
  - `npm run lint` from frontend/ reports zero magic number violations
  - No false positives requiring disable comments
  - Linter output clean for @typescript-eslint/no-magic-numbers rule
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 220-228) - Success criteria
- **Dependencies**:
  - Phases 2 and 3 complete (all TypeScript changes done)

### Task 4.3: Run full test suite and verify no regressions

Execute all tests to confirm constant replacements don't break functionality.

- **Files**:
  - All test files in tests/
- **Success**:
  - `uv run pytest` passes all Python tests
  - `npm test` from frontend/ passes all TypeScript tests
  - No test failures related to constant changes
  - Test coverage maintained or improved
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 230-232) - Mitigation strategy
- **Dependencies**:
  - All previous phases complete

### Task 4.4: Update ESLint ignore list if universally accepted values identified

Review linter configuration and adjust ignore list if needed.

- **Files**:
  - frontend/eslint.config.js - Potentially update ignore list
- **Success**:
  - Decision documented: Keep [-1, 0, 1] or expand to [-1, 0, 1, 2]
  - Rationale provided for any changes to ignore list
  - No overly permissive ignore list that defeats rule purpose
- **Research References**:
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 209-218) - Phase 4 update guidance
  - #file:../research/20251224-magic-number-lint-remediation-research.md (Lines 247-255) - Alternative approaches evaluation
- **Dependencies**:
  - Tasks 4.1-4.3 complete (all violations resolved)

## Dependencies

- starlette (already installed) - HTTP status constants for Python
- http-status-codes npm package - HTTP status constants for TypeScript
- Ruff linter with PLR2004 rule - Python magic number detection
- ESLint with @typescript-eslint/no-magic-numbers - TypeScript magic number detection

## Success Criteria

- Both linter rules enabled and enforcing magic number detection
- Zero PLR2004 violations in Python (10+ original violations eliminated)
- Zero @typescript-eslint/no-magic-numbers violations in TypeScript (61 original violations eliminated)
- All HTTP status codes use framework/library constants
- Four new constant files created with comprehensive documentation
- Full test suite passes without regressions
- Code maintainability improved through self-documenting constants

<!-- markdownlint-disable-file -->
# Task Research Notes: Magic Number Lint Rule Remediation

## FIRST IMPLEMENTATION STEP: Enable Linter Rules

**Before implementing any fixes, these linter rules must be enabled to enforce the pattern going forward:**

### File: `pyproject.toml`
```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C4", "UP", "PLR2004"]
ignore = []
```

**Change**: Add `PLR2004` to the select list to enable magic number detection.

### File: `frontend/eslint.config.js`
```javascript
// Add to rules section:
'@typescript-eslint/no-magic-numbers': [
  'error',
  {
    ignore: [-1, 0, 1],
    ignoreEnums: true,
    ignoreNumericLiteralTypes: true,
    ignoreReadonlyClassProperties: true,
    ignoreTypeIndexes: true,
  },
],
```

**Change**: Add the `@typescript-eslint/no-magic-numbers` rule configuration to the rules section.

### Rationale
These rules were temporarily enabled to identify violations (71 total found across Python and TypeScript) and have been reverted to avoid blocking development. They must be re-enabled as the FIRST step of implementation to:
1. Make violations visible during development
2. Prevent new magic numbers from being introduced
3. Guide developers to use the new constants as they're created

## Research Executed

### Linter Configuration
- pyproject.toml
  - Added `PLR2004` to ruff lint select rules
  - Rule detects magic numbers in comparisons
- frontend/eslint.config.js
  - Enabled `@typescript-eslint/no-magic-numbers` with ignore list `[-1, 0, 1]`
  - Configured TypeScript-specific options for enums, types, readonly properties

### Current Violations Analysis
- **Python (Ruff PLR2004)**: 10+ violations found
  - JWT key length checks: 32 bytes
  - Discord snowflake ID validation: 17-20 characters
  - HTTP status code comparisons: 200, 401, 403
  - List pagination limits: 10 items
  - String truncation: 100 characters
  - Retry failure threshold: 3 attempts
- **TypeScript (ESLint)**: 61 violations found
  - HTTP status codes: 200, 401, 403, 404, 422
  - Time conversions: 60 (seconds), 1000 (milliseconds)
  - UI constraints: 10, 30, 100 (limits/sizes)
  - Animation/delay timers: 1500, 3000 (milliseconds)
  - File size limits: 5 MB (5 * 1024 * 1024)
  - Avatar dimensions: 200px
  - Opacity values: 0.5

### Code Pattern Research
- #search:status_code
  - Found extensive use of numeric HTTP status codes throughout codebase
  - No existing HTTP status code constants defined in project
- #search:HTTP_\d+|STATUS_CODE
  - No centralized constants file for HTTP codes
  - FastAPI uses starlette.status module for status codes

### External Research
- #fetch:https://docs.astral.sh/ruff/rules/
  - Found PLR2004 rule for magic number detection
  - Pylint refactor rule category
- #fetch:https://typescript-eslint.io/rules/no-magic-numbers/
  - TypeScript-specific options for enums, types, indexes
  - Extends base ESLint rule
- #fetch:https://www.npmjs.com/package/http-status-codes
  - Industry-standard package with 5M+ weekly downloads
  - Complete RFC-compliant HTTP status codes
  - Zero dependencies, full TypeScript support

## Key Discoveries

### Magic Number Categories

1. **HTTP Status Codes** (Most Common)
   - 200 OK, 201 Created, 204 No Content
   - 401 Unauthorized, 403 Forbidden, 404 Not Found
   - 422 Unprocessable Entity/Content
   - Used in: API routes, middleware, client interceptors, error handlers

2. **Cryptographic Constants**
   - 32-byte key length requirements (services/api/auth/tokens.py:48)
   - Discord snowflake ID format (17-20 characters)

3. **Business Logic Limits**
   - Pagination: 10 items per page
   - String truncation: 100 characters for titles/descriptions
   - Retry thresholds: 3 consecutive failures
   - Player limits: Varies by game

4. **UI/UX Constants**
   - Time conversions: 60 seconds/minute
   - Animation delays: 1500ms, 3000ms
   - File size limits: 5MB (5 * 1024 * 1024 bytes)
   - Image dimensions: 200px avatars
   - Layout spacing: 10px, 16px
   - Opacity: 0.5 for hover effects

### Framework Support

**Python (FastAPI/Starlette)**
```python
from starlette import status

# Available constants:
status.HTTP_200_OK
status.HTTP_201_CREATED
status.HTTP_401_UNAUTHORIZED
status.HTTP_403_FORBIDDEN
status.HTTP_404_NOT_FOUND
status.HTTP_422_UNPROCESSABLE_ENTITY  # Deprecated
status.HTTP_422_UNPROCESSABLE_CONTENT  # Current
```

**TypeScript**
- No built-in HTTP status constants
- Need to create project constants

### Project Convention Findings
- Project already imports `from starlette import status` in some files
- Recent change (20251130): Migrated from deprecated `HTTP_422_UNPROCESSABLE_ENTITY` to `HTTP_422_UNPROCESSABLE_CONTENT`
- No TypeScript constants file exists
- Tests use numeric literals directly

## Recommended Approach

### Phase 1: Use Framework-Provided Constants (Python)

**Immediate Action**: Replace all HTTP status code literals with `starlette.status` constants

**Benefits**:
- Zero maintenance overhead - framework-maintained
- Type-safe and IDE-friendly
- Already partially adopted in codebase
- Aligns with FastAPI best practices

**Implementation**:
```python
# Before
if response.status_code == 403:
    logger.warning("Authorization denied")

# After
from starlette import status

if response.status_code == status.HTTP_403_FORBIDDEN:
    logger.warning("Authorization denied")
```

### Phase 2: Use Standard TypeScript Package (http-status-codes)

**Install Package**: `npm install http-status-codes --save`

**Package Details**:
- 5+ million weekly downloads
- Complete RFC compliance (RFC1945, RFC2616, RFC2518, RFC6585, RFC7538)
- Zero dependencies
- Full TypeScript support
- Same approach as backend (framework-provided constants)

**Implementation**:
```typescript
import { StatusCodes } from 'http-status-codes';

// Before
if (error.response?.status === 401) {
  window.location.href = '/login';
}

// After
if (error.response?.status === StatusCodes.UNAUTHORIZED) {
  window.location.href = '/login';
}
```

**Available Constants**:
```typescript
StatusCodes.OK                    // 200
StatusCodes.CREATED               // 201
StatusCodes.NO_CONTENT            // 204
StatusCodes.UNAUTHORIZED          // 401
StatusCodes.FORBIDDEN             // 403
StatusCodes.NOT_FOUND             // 404
StatusCodes.UNPROCESSABLE_ENTITY  // 422
```

**Benefits**:
- Industry-standard package with millions of users
- Zero maintenance overhead - community maintained
- Complete coverage of all HTTP status codes
- Mirrors Python approach (using framework/library constants)
- Built-in TypeScript types
- Includes reason phrases if needed: `ReasonPhrases.OK`

### Phase 3: Create Domain-Specific Constants

**For Cryptographic/Security Constants**:
```python
# shared/utils/security_constants.py
ENCRYPTION_KEY_LENGTH = 32  # Fernet requirement: 32 bytes
DISCORD_SNOWFLAKE_MIN_LENGTH = 17
DISCORD_SNOWFLAKE_MAX_LENGTH = 20
```

**For Business Logic Constants**:
```python
# shared/utils/pagination.py
DEFAULT_PAGE_SIZE = 10
MAX_STRING_DISPLAY_LENGTH = 100

# shared/utils/retry_config.py
MAX_CONSECUTIVE_FAILURES = 3
```

**For UI/UX Constants**:
```typescript
// frontend/src/constants/ui.ts
export const UI = {
  ANIMATION_DELAY_SHORT: 1500,
  ANIMATION_DELAY_STANDARD: 3000,
  MAX_FILE_SIZE_BYTES: 5 * 1024 * 1024, // 5MB
  AVATAR_SIZE: 200,
  HOVER_OPACITY: 0.5,
} as const;

// frontend/src/constants/time.ts
export const Time = {
  SECONDS_PER_MINUTE: 60,
  MILLISECONDS_PER_SECOND: 1000,
} as const;
```

### Phase 4: Update Lint Ignore List

**Consider Universally Accepted Values**:
- `-1, 0, 1, 2` (common array/math operations)
- Consider NOT ignoring these to maintain consistency

**Do NOT Ignore**:
- HTTP status codes
- Time conversions
- Business logic thresholds
- UI dimensions

## Implementation Guidance

### Objectives
1. Eliminate all magic number lint violations
2. Improve code maintainability and readability
3. Establish patterns for future development
4. Minimal code churn - use framework constants where available

### Key Tasks

**Python Changes**:
1. Add `from starlette import status` imports
2. Replace all HTTP status code literals with `status.HTTP_*` constants
3. Create `shared/utils/security_constants.py` for crypto constants
4. Create `shared/utils/pagination.py` for pagination constants
5. Update retry daemon with `MAX_CONSECUTIVE_FAILURES` constant

**TypeScript Changes**:
1. Install `http-status-codes` package: `npm install http-status-codes --save`
2. Replace all HTTP status code literals with `StatusCodes` imports
3. Create `frontend/src/constants/ui.ts` for UI constants
4. Create `frontend/src/constants/time.ts` for time conversions
5. Update ESLint ignore list if needed

**Test Updates**:
1. Update all test assertions to use constants
2. Verify no regressions from constant usage
3. Add tests for new constant modules

### Dependencies
- Existing: starlette package (already installed)
- New: http-status-codes npm package (~5M weekly downloads, MIT license)
- No new Python dependencies required

### Success Criteria
- Zero magic number lint violations in both Python and TypeScript
- All HTTP status codes use framework/project constants
- All time conversions use named constants
- All UI dimensions use named constants
- All business logic thresholds use named constants
- Tests pass with new constants
- Code review confirms improved readability

## Alternative Approaches Considered

### Alternative 1: Inline Constants with Comments
```python
MAX_RETRIES = 3  # Maximum consecutive failures before alerting
if failures >= MAX_RETRIES:
    alert()
```
**Rejected**: While this works for local scope, doesn't provide reusability or centralized documentation.

### Alternative 2: Configuration Files
```yaml
# config/constants.yml
pagination:
  default_page_size: 10
http:
  status_forbidden: 403
```
**Rejected**: Unnecessary complexity. HTTP status codes are standardized and shouldn't be configurable. Framework provides these constants already.

### Alternative 3: Aggressive ESLint Ignore List
```javascript
ignore: [-1, 0, 1, 2, 10, 60, 100, 200, 401, 403, 404, 422, 1000, 1500, 3000]
```
**Rejected**: Defeats the purpose of the rule. Magic numbers harm maintainability.

## Execution Priority

**High Priority** (Complete First):
1. Python HTTP status codes → Use `starlette.status`
2. TypeScript HTTP status codes → Install and use `http-status-codes` package
3. Security/crypto constants → Create security_constants.py

**Medium Priority**:
4. UI/UX constants → Create ui.ts and time.ts
5. Pagination constants → Create pagination.py

**Low Priority**:
6. Test file updates
7. Documentation updates

## Risk Assessment

**Low Risk Changes**:
- Using starlette.status constants (already partially adopted)
- Creating new constant files (additive)

**Medium Risk Changes**:
- Replacing all magic numbers in TypeScript (61 locations)
- Need thorough testing of time conversions

**Mitigation**:
- Make changes incrementally
- Run full test suite after each phase
- Review diffs carefully for any unintended changes

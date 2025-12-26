<!-- markdownlint-disable-file -->

# Task Details: Environment Variable Configuration Synchronization

## Research Reference

**Source Research**: #file:../research/20251226-environment-variable-audit-research.md

## Phase 1: Update env.example (Master Template)

### Task 1.1: Add missing Docker configuration variables

Add COMPOSE_FILE, COMPOSE_PROFILES, CONTAINER_PREFIX, RESTART_POLICY, and HOST_WORKSPACE_FOLDER to env.example with comprehensive documentation.

- **Files**:
  - config/env/env.example - Master template file
- **Success**:
  - All Docker configuration variables present
  - Clear comments explaining purpose and usage
  - Examples provided for each variable
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 69-78) - Docker configuration variables
- **Dependencies**:
  - None

### Task 1.2: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL

Add JWT_SECRET (currently used in compose.yaml but missing) and RETRY_DAEMON_LOG_LEVEL to env.example.

- **Files**:
  - config/env/env.example - Master template file
- **Success**:
  - JWT_SECRET present with security warning
  - RETRY_DAEMON_LOG_LEVEL present with log level options
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 138-142) - JWT_SECRET usage
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 162-166) - RETRY_DAEMON_LOG_LEVEL
- **Dependencies**:
  - None

### Task 1.3: Remove deprecated variables (API_SECRET_KEY, API_HOST, API_PORT)

Remove API_SECRET_KEY (replaced by JWT_SECRET) and API_HOST/API_PORT (hardcoded in compose.yaml, not used).

- **Files**:
  - config/env/env.example - Master template file
- **Success**:
  - API_SECRET_KEY removed
  - API_HOST removed
  - API_PORT removed
  - No references to deprecated variables
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 403-407) - Variables to remove
- **Dependencies**:
  - None

### Task 1.4: Reorganize all variables to match standard ordering

Reorganize env.example to follow the standardized 12-section ordering structure.

- **Files**:
  - config/env/env.example - Master template file
- **Success**:
  - All variables organized into 12 logical sections
  - Section headers clearly marked
  - Variables within sections in consistent order
  - Structure matches template from research
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 235-316) - Standardized variable ordering
- **Dependencies**:
  - Tasks 1.1, 1.2, 1.3 completed

### Task 1.5: Add comprehensive comments for all variables

Ensure every variable in env.example has clear documentation including purpose, examples, and usage notes.

- **Files**:
  - config/env/env.example - Master template file
- **Success**:
  - Every variable has descriptive comment
  - Example values provided where helpful
  - Optional variables clearly marked
  - Environment-specific usage documented
  - Cross-references to related documentation included
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 430-442) - Comment standardization
- **Dependencies**:
  - Task 1.4 completed

## Phase 2: Update env.dev (Development Configuration)

### Task 2.1: Add missing variables and reorganize structure

Add missing variables (COMPOSE_FILE, COMPOSE_PROFILES, JWT_SECRET, RETRY_DAEMON_LOG_LEVEL, etc.) and reorganize to match standard ordering.

- **Files**:
  - config/env/env.dev - Development configuration
- **Success**:
  - All development-appropriate variables present
  - Structure matches env.example ordering
  - Port mapping variables included
  - Development-specific comments added
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 318-327) - env.dev requirements
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 374-382) - Variables to add
- **Dependencies**:
  - Phase 1 completed (env.example as reference)

### Task 2.2: Remove duplicate API_HOST_PORT and commented URLs

Remove duplicate API_HOST_PORT definition and commented Discord invite URL.

- **Files**:
  - config/env/env.dev - Development configuration
- **Success**:
  - Only one API_HOST_PORT definition
  - No commented-out URLs
  - Clean structure
  - **CRITICAL**: Preserve all actual credential values
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 45-53) - Unused variables to remove
- **Dependencies**:
  - None

### Task 2.3: Move Cloudflare section to proper location

Move Cloudflare tunnel configuration from end of file to proper location in standardized ordering.

- **Files**:
  - config/env/env.dev - Development configuration
- **Success**:
  - Cloudflare section in correct location (section 11)
  - Consistent with env.example structure
  - All related variables together
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 235-316) - Standardized ordering showing Cloudflare at section 11
- **Dependencies**:
  - Task 2.1 completed

**CRITICAL NOTE**: All tasks in Phase 2 MUST preserve existing credential values in env.dev. Only remove duplicates, add missing variables, and reorganize structure. This file contains live working credentials.

## Phase 3: Update env.prod (Production Configuration)

### Task 3.1: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL

Add JWT_SECRET and RETRY_DAEMON_LOG_LEVEL with appropriate production values.

- **Files**:
  - config/env/env.prod - Production configuration
- **Success**:
  - JWT_SECRET present with strong placeholder
  - RETRY_DAEMON_LOG_LEVEL set to INFO
  - Security warnings in comments
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 386-395) - env.prod additions needed
- **Dependencies**:
  - Phase 1 completed (for reference comments)

### Task 3.2: Add COMPOSE_FILE variable

Add COMPOSE_FILE=compose.yaml to explicitly control compose file loading.

- **Files**:
  - config/env/env.prod - Production configuration
- **Success**:
  - COMPOSE_FILE=compose.yaml present
  - Comment explains production-only compose usage
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 329-337) - env.prod requirements
- **Dependencies**:
  - None

### Task 3.3: Remove unused API_HOST and API_PORT variables

Remove API_HOST and API_PORT which are not used in compose files (hardcoded to 8000).

- **Files**:
  - config/env/env.prod - Production configuration
- **Success**:
  - API_HOST removed
  - API_PORT removed
  - No unused variables remain
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 414-418) - Variables to remove from prod
- **Dependencies**:
  - None

### Task 3.4: Reorganize to match standard ordering

Reorganize all variables in env.prod to match standardized ordering, excluding development-only variables.

- **Files**:
  - config/env/env.prod - Production configuration
- **Success**:
  - Variables in standard order
  - Port mapping variables excluded (not used in prod)
  - HOST_WORKSPACE_FOLDER excluded (not used in prod)
  - Minimal comments referencing env.example
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 329-337) - env.prod variable exclusions
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 235-316) - Standard ordering
- **Dependencies**:
  - Tasks 3.1, 3.2, 3.3 completed

## Phase 4: Update env.staging (Staging Configuration)

### Task 4.1: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL

Add JWT_SECRET and RETRY_DAEMON_LOG_LEVEL with staging-appropriate values.

- **Files**:
  - config/env/env.staging - Staging configuration
- **Success**:
  - JWT_SECRET present with placeholder
  - RETRY_DAEMON_LOG_LEVEL set to INFO
  - Comments explain staging usage
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 397-401) - env.staging additions needed
- **Dependencies**:
  - Phase 1 completed (for reference)

### Task 4.2: Remove unused API_HOST and API_PORT variables

Remove API_HOST and API_PORT which are not used in compose files.

- **Files**:
  - config/env/env.staging - Staging configuration
- **Success**:
  - API_HOST removed
  - API_PORT removed
  - Clean configuration
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 420-424) - Variables to remove from staging
- **Dependencies**:
  - None

### Task 4.3: Reorganize to match standard ordering

Reorganize env.staging to match standard ordering, keeping staging-specific additions like CONTAINER_PREFIX.

- **Files**:
  - config/env/env.staging - Staging configuration
- **Success**:
  - Variables in standard order
  - CONTAINER_PREFIX included for isolation
  - Port mapping variables excluded
  - External network configuration preserved
  - Minimal comments with env.example reference
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 339-345) - env.staging requirements
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 235-316) - Standard ordering
- **Dependencies**:
  - Tasks 4.1, 4.2 completed

## Phase 5: Update Test Configuration Files

### Task 5.1: Update env.e2e with consistent ordering

Reorganize env.e2e to follow standard ordering for applicable variables while maintaining test-specific focus.

- **Files**:
  - config/env/env.e2e - End-to-end test configuration
- **Success**:
  - Test-specific variables organized logically
  - Ordering matches standard where applicable
  - All Discord test bot variables present
  - Port mappings use test-specific ports
  - Comments explain test-specific usage
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 347-353) - env.e2e requirements
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 213-226) - Test-specific Discord variables
- **Dependencies**:
  - Phase 1 completed (for consistent structure)

### Task 5.2: Update env.int with consistent ordering

Reorganize env.int to follow standard ordering while maintaining minimal test-specific focus.

- **Files**:
  - config/env/env.int - Integration test configuration
- **Success**:
  - Minimal variable set maintained
  - Ordering matches standard where applicable
  - No Discord bot variables (not used in integration tests)
  - Port mappings use test-specific ports
  - Comments explain integration test usage
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 355-361) - env.int requirements
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 67-77) - Test-specific variable usage
- **Dependencies**:
  - Phase 1 completed (for consistent structure)

## Phase 6: Verification

### Task 6.1: Verify all compose variables have corresponding env entries

Systematically verify that every ${VARIABLE} reference in all compose files has a corresponding entry in appropriate env files.

- **Files**:
  - All compose*.yaml files for variable extraction
  - All config/env/env.* files for verification
- **Success**:
  - Script or manual check confirms all variables present
  - No missing variable warnings
  - Documentation of which variables appear in which files
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 15-29) - File analysis showing all compose files checked
- **Dependencies**:
  - All previous phases completed

### Task 6.2: Test vimdiff comparison of all env files

Use vimdiff to compare env files side-by-side and verify consistent ordering enables easy comparison.

- **Files**:
  - All config/env/env.* files
- **Success**:
  - vimdiff shows aligned sections
  - Easy to identify environment-specific differences
  - No unexpected ordering discrepancies
  - Documentation confirms vimdiff-friendly structure
- **Research References**:
  - #file:../research/20251226-environment-variable-audit-research.md (Lines 460-468) - Success criteria including vimdiff comparison
- **Dependencies**:
  - All previous phases completed

## Dependencies

- None - this is purely a configuration update task

## Success Criteria

- All environment files have consistent variable ordering
- No duplicate variables in any file
- No unused variables in any file
- All variables used in compose files are present in relevant env files
- env.example has comprehensive comments for every variable
- Deployment files have consistent minimal comments
- Files can be compared side-by-side with vimdiff for easy verification

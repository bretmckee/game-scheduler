---
applyTo: ".copilot-tracking/changes/20251226-environment-variable-synchronization-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Environment Variable Configuration Synchronization

## Overview

Synchronize all environment configuration files to ensure consistent variable ordering, remove unused variables, add missing variables, and standardize comments across deployment environments.

## Objectives

- Ensure all necessary variables are present in all environment files
- Remove unused and deprecated variables
- Standardize variable ordering across all configuration files
- Ensure comprehensive comments in env.example
- Enable side-by-side comparison with vimdiff

## Research Summary

### Project Files

- config/env/env.example - Master template requiring expansion
- config/env/env.dev - Development configuration needing cleanup
- config/env/env.e2e - End-to-end test configuration
- config/env/env.int - Integration test configuration
- config/env/env.prod - Production configuration needing additions
- config/env/env.staging - Staging configuration needing additions
- compose.yaml - Defines all environment variable usage
- compose.override.yaml - Development-specific variables
- compose.{prod,staging,int,e2e}.yaml - Environment-specific overrides

### External References

- #file:../research/20251226-environment-variable-audit-research.md - Complete variable inventory and analysis

### Standards References

- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Comment style guidance

## Implementation Checklist

### [ ] Phase 1: Update env.example (Master Template)

- [ ] Task 1.1: Add missing Docker configuration variables
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 15-30)

- [ ] Task 1.2: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 32-42)

- [ ] Task 1.3: Remove deprecated variables (API_SECRET_KEY, API_HOST, API_PORT)
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 44-54)

- [ ] Task 1.4: Reorganize all variables to match standard ordering
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 56-75)

- [ ] Task 1.5: Add comprehensive comments for all variables
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 77-90)

### [ ] Phase 2: Update env.dev (Development Configuration)

- [ ] Task 2.1: Add missing variables and reorganize structure
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 92-110)

- [ ] Task 2.2: Remove duplicate API_HOST_PORT and commented URLs
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 112-122)

- [ ] Task 2.3: Move Cloudflare section to proper location
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 124-134)

### [ ] Phase 3: Update env.prod (Production Configuration)

- [ ] Task 3.1: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 149-162)

- [ ] Task 3.2: Add COMPOSE_FILE variable
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 164-172)

- [ ] Task 3.3: Remove unused API_HOST and API_PORT variables
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 174-184)

- [ ] Task 3.4: Reorganize to match standard ordering
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 186-200)

### [ ] Phase 4: Update env.staging (Staging Configuration)

- [ ] Task 4.1: Add missing JWT_SECRET and RETRY_DAEMON_LOG_LEVEL
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 202-215)

- [ ] Task 4.2: Remove unused API_HOST and API_PORT variables
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 217-227)

- [ ] Task 4.3: Reorganize to match standard ordering
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 229-243)

### [ ] Phase 5: Update Test Configuration Files

- [ ] Task 5.1: Update env.e2e with consistent ordering
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 245-260)

- [ ] Task 5.2: Update env.int with consistent ordering
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 262-277)

### [ ] Phase 6: Verification

- [ ] Task 6.1: Verify all compose variables have corresponding env entries
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 279-292)

- [ ] Task 6.2: Test vimdiff comparison of all env files
  - Details: .copilot-tracking/details/20251226-environment-variable-synchronization-details.md (Lines 294-305)

## Dependencies

- No external dependencies - configuration-only changes

## Success Criteria

- All environment files have identical variable ordering (where applicable)
- No duplicate variables in any file
- No unused variables in any file
- All variables used in compose files are present in relevant env files
- env.example has comprehensive comments for every variable
- Files can be compared side-by-side with vimdiff
- All deployment files contain only environment-appropriate variables

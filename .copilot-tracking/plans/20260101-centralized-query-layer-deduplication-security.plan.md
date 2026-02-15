---
applyTo: '.copilot-tracking/changes/20260101-centralized-query-layer-deduplication-security-changes.md'
---

<!-- markdownlint-disable-file -->

# Task Checklist: Centralized Query Layer for Deduplication and Security

## Overview

Create a centralized guild-scoped query layer that eliminates code duplication across 37+ database query locations while enforcing guild isolation security through required guild_id parameters.

## Objectives

- Consolidate 37+ scattered database queries into 10-12 reusable wrapper functions
- Enforce guild isolation by requiring guild_id parameter in all database operations
- Eliminate optional filtering patterns that create cross-guild data leakage risks
- Reduce maintenance burden from 37 update sites to 10-12 centralized functions
- Enable architectural enforcement through linting to prevent regressions

## Research Summary

### Project Files

- services/api/routes/games.py - 8+ game queries identified for consolidation
- services/api/routes/templates.py - 6+ template queries with duplication
- services/api/routes/guilds.py - 6+ guild/config query patterns
- services/api/dependencies/permissions.py - 10+ permission check queries
- services/bot/ - Multiple bot handlers with implicit guild context
- services/scheduler/ - Daemons using sync Session patterns

### External References

- #file:../research/20260101-centralized-query-layer-deduplication-security-research.md - Comprehensive audit of 37+ query locations with duplication and security analysis
- PostgreSQL Row Level Security (RLS) documentation - Database-level enforcement patterns
- SQLAlchemy async patterns - Best practices for async database wrappers

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions including async patterns, type hints, error handling
- #file:../../.github/instructions/coding-best-practices.instructions.md - Modularity, DRY principle, security practices, testing requirements

## Implementation Checklist

### [x] Phase 1: Foundation - Create Guild Query Wrapper Functions

- [x] Task 1.1: Create `shared/data_access/` directory structure
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 11-27)

- [x] Task 1.2: Implement core game operation wrappers (5 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 27-45)

- [x] Task 1.3: Implement participant operation wrappers (3 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 45-62)

- [x] Task 1.4: Implement template operation wrappers (4 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 62-79)

- [x] Task 1.5: Add comprehensive unit tests for all wrapper functions
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 79-98)

- [x] Task 1.6: Add integration tests for guild query wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 98-154)

### [ ] Phase 2: API Routes Migration (Test-First Approach)

- [ ] Task 2.1a: Create integration tests for games route (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 156-183)

- [ ] Task 2.1b: Migrate games route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 183-208)

- [ ] Task 2.2a: Create integration tests for templates route (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 208-232)

- [ ] Task 2.2b: Migrate templates route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 232-254)

- [ ] Task 2.3a: Create integration tests for guilds route (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 254-279)

- [ ] Task 2.3b: Migrate guilds route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 279-299)

- [ ] Task 2.4a: Create integration tests for channels route (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 299-324)

- [ ] Task 2.4b: Migrate channels route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 324-343)

- [ ] Task 2.5a: Create integration tests for permissions dependencies (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 343-370)

- [ ] Task 2.5b: Migrate permissions dependencies to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 370-389)

### [ ] Phase 3: Bot and Scheduler Migration (Test-First Approach)

- [ ] Task 3.1a: Create integration tests for bot handlers (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 391-420)

- [ ] Task 3.1b: Migrate bot handlers to use guild_queries (async)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 420-439)

- [ ] Task 3.2a: Create unit tests for synchronous wrapper variants (TDD)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 439-469)

- [ ] Task 3.2b: Create synchronous wrapper variants for scheduler
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 469-487)

- [ ] Task 3.3a: Enhance scheduler integration tests for guild isolation (pre-migration baseline)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 487-519)

- [ ] Task 3.3b: Migrate scheduler daemons to use guild_queries_sync
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 519-539)

### [ ] Phase 4: Verification and Database Security

- [ ] Task 4.1: Verify 100% migration completion
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 357-375)

- [ ] Task 4.2: Create and apply RLS migration
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 375-394)

- [ ] Task 4.3: Add integration tests for RLS enforcement
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 394-411)

- [ ] Task 4.4: Create end-to-end guild isolation validation tests
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 411-432)

### [ ] Phase 5: Architectural Enforcement

- [ ] Task 5.1: Create linting script to prevent model imports
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 434-453)

- [ ] Task 5.2: Add pre-commit hook for query layer enforcement
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 453-470)

- [ ] Task 5.3: Update documentation with architecture guidelines
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 470-488)

## Dependencies

- SQLAlchemy 2.x with async support
- PostgreSQL 12+ (for Row Level Security)
- pytest and pytest-asyncio for testing
- pre-commit framework for linting hooks

## Success Criteria

- All 37+ database query locations migrated to use guild_queries wrappers
- Zero locations with optional guild_id parameters
- 100% test coverage on wrapper functions
- Integration tests pass with RLS enabled
- Linting prevents direct model imports outside allowed locations
- Documentation clearly explains centralized query architecture

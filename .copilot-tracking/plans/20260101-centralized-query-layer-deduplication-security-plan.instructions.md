---
applyTo: ".copilot-tracking/changes/20260101-centralized-query-layer-deduplication-security-changes.md"
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

### [ ] Phase 1: Foundation - Create Guild Query Wrapper Functions

- [ ] Task 1.1: Create `shared/data_access/` directory structure
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 15-35)

- [ ] Task 1.2: Implement core game operation wrappers (5 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 37-95)

- [ ] Task 1.3: Implement participant operation wrappers (3 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 97-145)

- [ ] Task 1.4: Implement template operation wrappers (4 functions)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 147-195)

- [ ] Task 1.5: Add comprehensive unit tests for all wrapper functions
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 197-235)

### [ ] Phase 2: API Migration - High Priority Routes

- [ ] Task 2.1: Migrate games route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 237-275)

- [ ] Task 2.2: Migrate templates route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 277-315)

- [ ] Task 2.3: Migrate guilds route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 317-355)

- [ ] Task 2.4: Migrate channels route to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 357-395)

- [ ] Task 2.5: Migrate permissions dependencies to use guild_queries wrappers
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 397-435)

- [ ] Task 2.6: Create integration tests for API guild isolation
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 437-460)

### [ ] Phase 3: Bot and Scheduler Migration

- [ ] Task 3.1: Migrate bot handlers to use guild_queries (async)
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 462-485)

- [ ] Task 3.2: Create synchronous wrapper variants for scheduler
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 487-510)

- [ ] Task 3.3: Migrate scheduler daemons to use guild_queries_sync
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 512-535)

- [ ] Task 3.4: Create integration tests for bot guild isolation
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 537-561)

- [ ] Task 3.5: Update scheduler integration tests for guild isolation
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 563-587)

### [ ] Phase 4: Verification and Database Security

- [ ] Task 4.1: Verify 100% migration completion
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 589-627)

- [ ] Task 4.2: Create and apply RLS migration
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 629-677)

- [ ] Task 4.3: Add integration tests for RLS enforcement
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 679-703)

- [ ] Task 4.4: Create end-to-end guild isolation validation tests
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 705-732)

### [ ] Phase 5: Architectural Enforcement

- [ ] Task 5.1: Create linting script to prevent model imports
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 734-782)

- [ ] Task 5.2: Add pre-commit hook for query layer enforcement
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 784-822)

- [ ] Task 5.3: Update documentation with architecture guidelines
  - Details: .copilot-tracking/details/20260101-centralized-query-layer-deduplication-security-details.md (Lines 824-862)

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

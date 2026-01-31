---
applyTo: ".copilot-tracking/changes/20260130-service-layer-transaction-management-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: Service Layer Transaction Management and Atomicity

## Overview

Restore transaction atomicity by removing premature commits from service layer functions and enforcing route-level transaction boundaries.

## Objectives

- Remove all 17 commit calls from API service layer functions
- Preserve transaction atomicity across multi-step operations
- Prevent data integrity issues from partial operation failures
- Update test suite to validate correct transaction behavior
- Maintain backward compatibility at API level

## Research Summary

### Project Files

- [services/api/services/guild_service.py](../../services/api/services/guild_service.py) - 2 premature commits in create/update operations
- [services/api/services/channel_service.py](../../services/api/services/channel_service.py) - 2 premature commits in create/update operations
- [services/api/services/template_service.py](../../services/api/services/template_service.py) - 6 commits across CRUD operations
- [services/api/services/games.py](../../services/api/services/games.py) - 6 commits + 6 flushes in game/participant operations
- [shared/database.py](../../shared/database.py) - FastAPI dependency providing route-level transaction management

### External References

- #file:../research/20260130-service-layer-transaction-management-research.md - Comprehensive analysis of transaction management violations
- SQLAlchemy 2.0 async documentation - Session lifecycle best practices
- FastAPI dependency injection pattern - Transaction boundary management

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Documentation standards

## Implementation Checklist

### [x] Phase 1: Guild and Channel Service Refactoring

- [x] Task 1.1: Remove commits from guild_service.py

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 13-34)

- [x] Task 1.2: Remove commits from channel_service.py

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 36-57)

- [x] Task 1.3: Update guild and channel service tests

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 59-77)

### [x] Phase 2: Template Service Refactoring

- [x] Task 2.1: Remove commits from template_service.py

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 81-102)

- [x] Task 2.2: Update template service tests

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 104-119)

### [ ] Phase 3: Game Service Refactoring

- [ ] Task 3.1: Remove commits from games.py service

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 123-148)

- [ ] Task 3.2: Verify flush usage remains appropriate

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 150-165)

- [ ] Task 3.3: Update game service tests

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 167-182)

### [ ] Phase 4: Route Handler Verification

- [ ] Task 4.1: Audit all mutation endpoints for proper dependency usage

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 186-202)

- [ ] Task 4.2: Verify transaction boundaries in orchestrator functions

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 204-220)

### [ ] Phase 5: Integration Testing

- [ ] Task 5.1: Create atomicity test suite

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 224-245)

- [ ] Task 5.2: Add rollback scenario tests

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 247-264)

### [ ] Phase 6: Documentation and Guidelines

- [ ] Task 6.1: Document transaction management patterns

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 268-283)

- [ ] Task 6.2: Add service layer docstring conventions

  - Details: .copilot-tracking/details/20260130-service-layer-transaction-management-details.md (Lines 285-297)

## Dependencies

- SQLAlchemy 2.0 async patterns
- FastAPI dependency injection
- pytest with AsyncMock for test updates

## Success Criteria

- Zero commit calls in service layer functions (currently 17)
- All flush usage remains appropriate for ID generation
- Guild sync operations atomic: create guild+channels+template or rollback completely
- Game creation with participants is atomic
- Participant removal operations maintain consistency
- All unit tests pass with updated assertions
- New integration tests validate transaction atomicity
- No orphaned records from partial operation failures
- Production incident scenario (guild without channels) cannot reoccur

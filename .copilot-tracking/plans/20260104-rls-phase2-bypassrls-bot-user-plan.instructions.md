---
applyTo: ".copilot-tracking/changes/20260104-rls-phase2-bypassrls-bot-user-changes.md"
---

<!-- markdownlint-disable-file -->

# Task Checklist: RLS Phase 2 - BYPASSRLS Bot User Implementation

## Overview

Implement separate BYPASSRLS database user for bot and daemon services to eliminate unnecessary RLS overhead while maintaining API security.

## Objectives

- Create `gamebot_bot` database user with BYPASSRLS privilege (non-superuser)
- Configure bot and daemon services to use separate database connection
- Update all environment files with bot user credentials
- Remove guild context management from bot/daemon code
- Validate API still enforces RLS while bot/daemons bypass it

## Research Summary

### Project Files

- services/init/database_users.py - Database user creation logic
- config/env.* - Environment configuration files (dev, staging, prod, int, e2e)
- config.template/env.template - Environment template with documentation
- compose.yaml - Docker Compose service definitions
- services/bot/ - Bot service handlers
- services/scheduler/ - Daemon services (notification, status-transition)

### External References

- #file:../research/20260102-rls-performance-scaling-bot-analysis.md (Lines 758-934) - Phase 2 implementation details and migration steps
- #fetch:https://www.postgresql.org/docs/current/ddl-rowsecurity.html - BYPASSRLS privilege documentation

### Standards References

- #file:../../.github/instructions/python.instructions.md - Python coding conventions
- #file:../../.github/instructions/containerization-docker-best-practices.instructions.md - Docker configuration standards
- #file:../../.github/instructions/self-explanatory-code-commenting.instructions.md - Code commenting standards

## Implementation Checklist

### [ ] Phase 1: Create BYPASSRLS Database User

- [ ] Task 1.1: Add gamebot_bot user creation to database_users.py
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 13-61)

- [ ] Task 1.2: Update environment template with bot user variables
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 63-88)

- [ ] Task 1.3: Update all environment files with bot user credentials
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 90-141)

### [ ] Phase 2: Configure Services to Use Bot User

- [ ] Task 2.1: Update Docker Compose for bot service
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 143-168)

- [ ] Task 2.2: Update Docker Compose for daemon services
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 170-196)

- [ ] Task 2.3: Update init service to use admin database URL
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 198-217)

### [ ] Phase 3: Remove Guild Context Management

- [ ] Task 3.1: Remove RLS context setting from bot service
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 219-242)

- [ ] Task 3.2: Remove RLS context setting from daemon services
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 244-262)

### [ ] Phase 4: Validation and Testing

- [ ] Task 4.1: Create database user validation test
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 264-296)

- [ ] Task 4.2: Verify API still enforces RLS
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 298-318)

- [ ] Task 4.3: Verify bot/daemons bypass RLS
  - Details: .copilot-tracking/details/20260104-rls-phase2-bypassrls-bot-user-details.md (Lines 320-340)

## Dependencies

- Phase 1 RLS implementation complete (policies enabled on all tables)
- PostgreSQL 17 with BYPASSRLS privilege support
- Current three-user architecture (postgres, gamebot_admin, gamebot_app)
- All services currently using gamebot_app user

## Success Criteria

- gamebot_bot user created with BYPASSRLS privilege (not SUPERUSER)
- All environment files updated with bot user credentials
- Bot and daemon services use BOT_DATABASE_URL
- API service still uses DATABASE_URL (gamebot_app with RLS)
- Guild context management removed from bot/daemon code
- Tests validate RLS enforcement for API, RLS bypass for bot/daemons
- No cross-guild data leaks observed

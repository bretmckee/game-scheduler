<!-- markdownlint-disable-file -->
# Task Details: Docker Base Image Version Updates

## Research Reference

**Source Research**: #file:../research/20251206-docker-base-image-versions-research.md

## Phase 1: Update Python Base Images

### Task 1.1: Update api.Dockerfile Python version

Update both base and production stage FROM statements from Python 3.11 to 3.13.

- **Files**:
  - docker/api.Dockerfile - Lines 2 and 23 (both FROM statements)
- **Success**:
  - Both stages use `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

### Task 1.2: Update bot.Dockerfile Python version

Update FROM statement from Python 3.11 to 3.13.

- **Files**:
  - docker/bot.Dockerfile - Base stage FROM statement
- **Success**:
  - Uses `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

### Task 1.3: Update init.Dockerfile Python version

Update FROM statement from Python 3.11 to 3.13.

- **Files**:
  - docker/init.Dockerfile - Base stage FROM statement
- **Success**:
  - Uses `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

### Task 1.4: Update notification-daemon.Dockerfile Python version

Update FROM statement from Python 3.11 to 3.13.

- **Files**:
  - docker/notification-daemon.Dockerfile - Base stage FROM statement
- **Success**:
  - Uses `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

### Task 1.5: Update status-transition-daemon.Dockerfile Python version

Update FROM statement from Python 3.11 to 3.13.

- **Files**:
  - docker/status-transition-daemon.Dockerfile - Base stage FROM statement
- **Success**:
  - Uses `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

### Task 1.6: Update test.Dockerfile Python version

Update FROM statement from Python 3.11 to 3.13.

- **Files**:
  - docker/test.Dockerfile - Base stage FROM statement
- **Success**:
  - Uses `python:3.13-slim`
  - Dockerfile builds without errors
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 66-75) - Python version recommendations
- **Dependencies**: None

## Phase 2: Update Frontend Base Images

### Task 2.1: Update Node.js version in frontend.Dockerfile

Update Node.js from version 20 to 22 for longer LTS support window.

- **Files**:
  - docker/frontend.Dockerfile - Line 2 (builder stage FROM statement)
- **Success**:
  - Builder stage uses `node:22-alpine`
  - Frontend builds successfully
  - Application functions correctly
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 77-81) - Node.js version recommendations
- **Dependencies**: None

### Task 2.2: Update Nginx version in frontend.Dockerfile

Update Nginx from version 1.25 to 1.28 (current stable branch).

- **Files**:
  - docker/frontend.Dockerfile - Production stage FROM statement
- **Success**:
  - Production stage uses `nginx:1.28-alpine`
  - Nginx configuration remains compatible
  - Frontend serves correctly
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 83-88) - Nginx version recommendations
- **Dependencies**: None

## Phase 3: Update Service Images in docker-compose.base.yml

### Task 3.1: Update Redis version specification

Update Redis from generic version 7 tag to specific 7.4 tag for latest patches.

- **Files**:
  - docker-compose.base.yml - Redis service image specification
- **Success**:
  - Redis service uses `redis:7.4-alpine`
  - Service starts successfully
  - Cache functionality works correctly
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 90-95) - Redis version recommendations
- **Dependencies**: None

### Task 3.2: Update PostgreSQL version specification

Update PostgreSQL from version 15 to 17 (major version upgrade requiring migration strategy).

- **Files**:
  - docker-compose.base.yml - PostgreSQL service image specification
- **Success**:
  - PostgreSQL service uses `postgres:17-alpine`
  - Database starts successfully
  - All migrations apply correctly
  - Data integrity maintained
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 90-95) - PostgreSQL version recommendations
- **Dependencies**:
  - PostgreSQL data backup before upgrade
  - Migration testing in non-production environment
  - Verification of pg_dump/pg_restore compatibility

## Phase 4: Testing and Validation

### Task 4.1: Rebuild all Docker images

Rebuild all Docker images with updated base versions to verify successful builds.

- **Files**:
  - All Dockerfiles in docker/ directory
  - docker-compose.base.yml
- **Success**:
  - All images build without errors
  - No dependency conflicts
  - Image sizes remain reasonable
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 139-156) - Implementation guidance
- **Dependencies**: All previous tasks completed

### Task 4.2: Run integration tests

Execute integration test suite to verify application functionality with updated images.

- **Files**:
  - tests/integration/ - All integration tests
- **Success**:
  - All integration tests pass
  - No regressions introduced
  - Services communicate correctly
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 164-173) - Success criteria
- **Dependencies**: Task 4.1 completion

### Task 4.3: Verify PostgreSQL migration compatibility

Test PostgreSQL upgrade path and data migration from version 15 to 17.

- **Files**:
  - Database initialization scripts
  - Alembic migration files
- **Success**:
  - Database schema applies correctly on PostgreSQL 17
  - All queries execute successfully
  - No SQL compatibility issues
  - Performance remains acceptable
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 90-95) - PostgreSQL major version upgrade considerations
- **Dependencies**:
  - Task 3.2 completion
  - Database backup available
  - Test data prepared

## Phase 5: Documentation Updates

### Task 5.1: Update version references in documentation

Update all documentation files to reflect new Docker base image versions.

- **Files**:
  - README.md - Update version references
  - DEPLOYMENT_QUICKSTART.md - Update version references
  - RUNTIME_CONFIG.md - Update version references if applicable
- **Success**:
  - All version references updated
  - Documentation accurately reflects current state
  - No outdated version information
- **Research References**:
  - #file:../research/20251206-docker-base-image-versions-research.md (Lines 158-162) - Key tasks including documentation
- **Dependencies**: All implementation tasks completed

## Dependencies

- Docker and docker-compose installed
- PostgreSQL backup strategy for major version upgrade
- Test environment for validation

## Success Criteria

- All Docker base images updated to latest LTS versions
- All services build and run successfully
- Integration tests pass without regressions
- PostgreSQL migration completes successfully
- Documentation reflects current versions

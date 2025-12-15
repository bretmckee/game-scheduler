<!-- markdownlint-disable-file -->

# Task Details: Dependency Version Audit and Upgrade Strategy

## Research Reference

**Source Research**: #file:../research/20251215-dependency-version-audit-research.md

## Phase 1: PostgreSQL 18 Upgrade + Alembic Reset

### Task 1.1: Update PostgreSQL image references to 18-alpine

Update all Docker Compose files to use PostgreSQL 18-alpine image.

- **Files**:
  - `compose.yaml` - Base compose file with postgres service definition
  - `compose.prod.yaml` - Production environment overrides
  - `compose.staging.yaml` - Staging environment overrides
  - `compose.int.yaml` - Integration test environment overrides
  - `compose.e2e.yaml` - E2E test environment overrides
- **Success**:
  - All compose files reference `postgres:18-alpine`
  - No references to `postgres:17-alpine` remain
  - Files maintain consistent formatting
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 7-20) - PostgreSQL version analysis
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 238-265) - PostgreSQL upgrade implementation
- **Dependencies**:
  - Docker and Docker Compose installed

### Task 1.2: Reset Alembic migration history

Delete existing migration files and create fresh initial migration from current models.

- **Files**:
  - `alembic/versions/*.py` - All migration files (delete except __init__.py)
  - `alembic/versions/001_*.py` - New initial migration (create)
- **Success**:
  - Only single migration file exists in alembic/versions/
  - Migration creates all tables matching current model definitions
  - All foreign keys, indexes, and constraints defined
  - Alembic revision executes successfully
  - Database schema matches SQLAlchemy models
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 238-308) - Alembic reset procedure
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 310-324) - Expected migration contents
- **Dependencies**:
  - Task 1.1 completion (PostgreSQL 18 image updated)
  - Database volumes cleared (docker compose down -v)

### Task 1.3: Verify database schema and services

Validate that database schema is correct and all services connect successfully.

- **Files**:
  - No file modifications, verification only
- **Success**:
  - PostgreSQL 18 container running
  - alembic_version table shows correct head revision
  - All expected tables exist (games, game_participants, game_templates, discord_users)
  - Integration tests pass
  - All services (api, bot, scheduler) start successfully
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 326-340) - Verification checklist
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 342-350) - Rollback procedure
- **Dependencies**:
  - Task 1.2 completion (Alembic migration applied)

## Phase 2: Node.js 24 LTS Upgrade

### Task 2.1: Update Node.js base images

Update Dockerfiles to use Node.js 24-alpine base image.

- **Files**:
  - `docker/frontend.Dockerfile` - Frontend container image
  - `docker/test.Dockerfile` - Test container image (if exists)
  - `.github/workflows/*.yml` - GitHub Actions workflows (if Node version specified)
  - `frontend/package.json` - Optional engines field for documentation
- **Success**:
  - All Dockerfiles reference `node:24-alpine`
  - CI/CD workflows use Node 24 if version specified
  - Docker images build successfully
  - No compatibility warnings
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 52-64) - Node.js version analysis
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 352-380) - Node.js upgrade implementation
- **Dependencies**:
  - Docker installed

### Task 2.2: Test frontend builds and CI/CD

Verify that frontend builds successfully with Node.js 24.

- **Files**:
  - No file modifications, testing only
- **Success**:
  - `npm install` completes without errors
  - `npm run build` produces valid build artifacts
  - `npm run test` passes all tests (51/51)
  - `npm run dev` starts development server
  - CI/CD pipeline succeeds
  - No deprecation warnings
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 382-392) - Testing checklist
- **Dependencies**:
  - Task 2.1 completion (Node.js images updated)

## Phase 3: Python Dependency Modernization

### Task 3.1: Update pyproject.toml with compatible release constraints

Replace minimum version constraints (>=) with compatible release operator (~=).

- **Files**:
  - `pyproject.toml` - Project dependencies and dev dependencies
- **Success**:
  - All production dependencies use ~= operator
  - All dev dependencies use ~= operator
  - Version numbers updated to latest compatible versions
  - File maintains valid TOML syntax
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 66-132) - Dependency constraint analysis
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 394-450) - pyproject.toml implementation
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 214-236) - Recommended approach details
- **Dependencies**:
  - None (independent change)

### Task 3.2: Upgrade packages and validate

Install upgraded packages and validate with tests and type checking.

- **Files**:
  - No file modifications, testing only
- **Success**:
  - `uv pip install --upgrade .` succeeds
  - All tests pass (unit, integration)
  - Type checking passes (mypy)
  - No deprecation warnings
  - All services start successfully
  - Linting passes (ruff)
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 452-473) - Upgrade and testing procedure
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 475-489) - Rollback procedure
- **Dependencies**:
  - Task 3.1 completion (pyproject.toml updated)

## Phase 4: NPM Package Updates

### Task 4.1: Update axios and TypeScript

Update axios to 1.7.x and TypeScript to 5.7.x for security fixes and latest features.

- **Files**:
  - `frontend/package.json` - Package dependencies
  - `frontend/package-lock.json` - Generated lockfile
- **Success**:
  - axios upgraded to ^1.7.0
  - TypeScript upgraded to ^5.7.0
  - `npm run type-check` passes
  - `npm run build` succeeds
  - `npm run test` passes all tests
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 134-173) - NPM package analysis
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 491-503) - axios implementation
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 505-513) - TypeScript implementation
- **Dependencies**:
  - Phase 2 completion (Node.js 24 installed)

### Task 4.2: Evaluate and optionally upgrade Vite 7

Assess Vite 7 migration guide and upgrade if straightforward.

- **Files**:
  - `frontend/package.json` - Vite and plugin dependencies (if upgrading)
  - `frontend/vite.config.ts` - Vite configuration (if changes needed)
- **Success**:
  - Migration guide reviewed
  - Decision made: upgrade or defer
  - If upgrading: vite@^7.0.0 and @vitejs/plugin-react@^5.0.0 installed
  - If upgrading: `npm run dev` starts successfully
  - If upgrading: `npm run build` succeeds
  - If upgrading: `npm run test` passes
  - If deferring: Documented rationale for future reference
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 160-173) - Vite 7 considerations
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 515-530) - Vite 7 implementation
- **Dependencies**:
  - Task 4.1 completion (axios and TypeScript updated)

## Dependencies

- Docker and Docker Compose
- Python 3.13 with uv
- Node.js and npm
- Git for version control

## Success Criteria

- All infrastructure services upgraded to latest stable LTS versions
- Python dependencies use modern constraint patterns with security updates
- NPM packages updated to latest stable versions
- All test suites pass without failures
- No deprecation warnings in application logs
- CI/CD pipeline executes successfully
- Services start and operate correctly
- Rollback procedures documented and tested

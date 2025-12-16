<!-- markdownlint-disable-file -->

# Task Details: Dependency Version Audit and Upgrade Strategy

## Research Reference

**Source Research**: #file:../research/20251215-dependency-version-audit-research.md

## Phase 1: PostgreSQL 18 Upgrade + Alembic Reset

**CRITICAL PREREQUISITE**: Previous Alembic reset attempt failed because models lack `server_default` declarations and PostgreSQL functions/triggers are not registered. These MUST be fixed before attempting reset.

### Task 1.1: Fix SQLAlchemy models to include server_default declarations

Add `server_default` parameter to all SQLAlchemy Column definitions that require database-level defaults.

- **Files**:
  - `shared/models/guild_configurations.py` - Add server_default to require_host_role and other boolean columns
  - `shared/models/channel_configurations.py` - Add server_default to is_active and other columns
  - `shared/models/games.py` - Review and add server_default where needed
  - `shared/models/*.py` - Review all model files for missing server_defaults
- **Success**:
  - All columns with Python `default=` also have `server_default=text('...')`
  - Boolean defaults use `server_default=text('false')` or `text('true')`
  - Timestamp defaults use `server_default=func.now()` where appropriate
  - No purely Python-side defaults for database columns
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 109-116) - Database migration lessons explaining the defect
  - Example: `require_host_role = Column(Boolean, default=False, server_default=text('false'))`
- **Dependencies**:
  - None (prerequisite task)

### Task 1.2: Install and configure alembic-utils for functions/triggers

Install alembic-utils package and register PostgreSQL functions and triggers.

- **Files**:
  - `pyproject.toml` - Add alembic-utils dependency
  - `alembic/env.py` - Import and register PGFunction and PGTrigger objects
  - New file for function/trigger definitions (e.g., `shared/database_objects.py`)
- **Success**:
  - alembic-utils installed and available
  - `notify_schedule_changed` function registered
  - `notify_game_status_schedule_changed` function registered
  - Associated triggers registered for both functions
  - `ix_game_sessions_template_id` index explicitly defined (if not in models)
  - Alembic env.py properly imports and includes these objects
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 109-116) - Missing functions/triggers issue
  - Need to extract SQL definitions from previous migration files
- **Dependencies**:
  - Task 1.1 completion (models corrected first)

### Task 1.3: Update PostgreSQL image references to 18-alpine

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
  - Tasks 1.1 and 1.2 completion (models and functions fixed)
  - Docker and Docker Compose installed

### Task 1.4: Reset Alembic migration history with corrected models

Delete existing migration files and create fresh initial migration from corrected models.

- **Files**:
  - `alembic/versions/*.py` - All migration files (delete except __init__.py)
  - `alembic/versions/001_*.py` - New initial migration (create with autogenerate)
- **Success**:
  - Only single migration file exists in alembic/versions/
  - Migration includes all server_default declarations
  - Migration includes PostgreSQL functions and triggers via alembic-utils
  - Migration includes all indexes (including ix_game_sessions_template_id)
  - All foreign keys and constraints defined
  - Alembic revision executes successfully
  - Database schema matches SQLAlchemy models exactly
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 109-116) - Actionable fix path
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 238-308) - Alembic reset procedure
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 310-324) - Expected migration contents
- **Dependencies**:
  - Task 1.3 completion (PostgreSQL 18 image updated)
  - Database volumes cleared (docker compose down -v)

### Task 1.5: Verify database schema and services

Validate that database schema is correct, defaults work, triggers fire, and all services connect successfully.

- **Files**:
  - No file modifications, verification only
- **Success**:
  - PostgreSQL 18 container running
  - alembic_version table shows correct head revision
  - All expected tables exist with correct server defaults
  - PostgreSQL functions exist (notify_schedule_changed, notify_game_status_schedule_changed)
  - PostgreSQL triggers are attached and functional
  - All indexes exist including ix_game_sessions_template_id
  - Integration tests pass (validates defaults and triggers work)
  - All services (api, bot, scheduler, daemons) start successfully
- **Research References**:
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 326-340) - Verification checklist
  - #file:../research/20251215-dependency-version-audit-research.md (Lines 342-350) - Rollback procedure
- **Dependencies**:
  - Task 1.4 completion (Alembic migration applied with corrected models)

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
  - Phase 1 completion recommended but not required (independent change)
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

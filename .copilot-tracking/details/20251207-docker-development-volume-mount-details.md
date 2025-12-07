<!-- markdownlint-disable-file -->

# Task Details: Docker Development Volume Mount Strategy

## Research Reference

**Source Research**: #file:../research/20251207-docker-development-volume-mount-research.md

## Phase 1: Update Python Service Dockerfiles

### Task 1.1: Add development stage to `docker/api.Dockerfile`

Add a development stage before the production stage that installs dependencies but does not copy source code, enabling volume mounts for hot-reload.

- **Files**:
  - `docker/api.Dockerfile` - Add development stage between base and production
- **Success**:
  - Development stage installs all dependencies via uv
  - Development stage does NOT copy shared/ or services/api/ directories
  - Development stage uses non-root appuser
  - Development stage uses uvicorn with --reload flag
  - Production stage remains unchanged
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 61-95) - Multi-stage build pattern with development target
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 122-144) - Complete development stage example from awesome-compose
- **Dependencies**:
  - Existing base stage with dependency installation
  - pyproject.toml for uv dependency management

### Task 1.2: Add development stage to `docker/bot.Dockerfile`

Add a development stage for the Discord bot service with hot-reload capability.

- **Files**:
  - `docker/bot.Dockerfile` - Add development stage between base and production
- **Success**:
  - Development stage installs all dependencies
  - Development stage does NOT copy source code
  - Development stage uses non-root appuser
  - Development stage uses python -m services.bot for module execution
  - Production stage remains unchanged
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 61-95) - Multi-stage build development pattern
- **Dependencies**:
  - Task 1.1 completion (same pattern)

### Task 1.3: Add development stage to `docker/notification-daemon.Dockerfile`

Add a development stage for the notification daemon service.

- **Files**:
  - `docker/notification-daemon.Dockerfile` - Add development stage between base and production
- **Success**:
  - Development stage installs all dependencies
  - Development stage does NOT copy source code
  - Development stage uses non-root appuser
  - Development stage uses python -m services.scheduler.notification_daemon
  - Production stage remains unchanged
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 61-95) - Multi-stage build development pattern
- **Dependencies**:
  - Task 1.1 completion (same pattern)

### Task 1.4: Add development stage to `docker/status-transition-daemon.Dockerfile`

Add a development stage for the status transition daemon service.

- **Files**:
  - `docker/status-transition-daemon.Dockerfile` - Add development stage between base and production
- **Success**:
  - Development stage installs all dependencies
  - Development stage does NOT copy source code
  - Development stage uses non-root appuser
  - Development stage uses python -m services.scheduler.status_transition_daemon
  - Production stage remains unchanged
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 61-95) - Multi-stage build development pattern
- **Dependencies**:
  - Task 1.1 completion (same pattern)

## Phase 2: Update Frontend Dockerfile

### Task 2.1: Add development stage to `docker/frontend.Dockerfile`

Add a development stage that uses Vite dev server instead of nginx for hot module replacement.

- **Files**:
  - `docker/frontend.Dockerfile` - Add development stage that runs Vite dev server
- **Success**:
  - Development stage installs npm dependencies
  - Development stage does NOT copy src/ directory
  - Development stage uses npm run dev with --host 0.0.0.0 for external access
  - Development stage exposes port 5173 (Vite default)
  - Production stage remains unchanged with nginx serving built assets
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 97-120) - Frontend development with Vite dev server pattern
- **Dependencies**:
  - Existing vite.config.ts configuration
  - npm scripts in package.json

## Phase 3: Create Development Override Configuration

### Task 3.1: Create `compose.override.yaml` with development configurations

Create a Docker Compose override file that automatically merges with compose.yaml to enable development mode with volume mounts.

- **Files**:
  - `compose.override.yaml` - New file with development overrides for all services
- **Success**:
  - Override specifies `target: development` for all service builds
  - API service mounts ./shared and ./services/api as read-only volumes
  - Bot service mounts ./shared and ./services/bot as read-only volumes
  - Notification daemon mounts ./shared and ./services/scheduler as read-only volumes
  - Status transition daemon mounts ./shared and ./services/scheduler as read-only volumes
  - Frontend service mounts ./frontend/src, ./frontend/index.html, and config files
  - All Python services override command with --reload or appropriate development flags
  - Frontend overrides command to use npm run dev
  - Development environment variables added (LOG_LEVEL=DEBUG, PYTHONUNBUFFERED=1)
  - File automatically loaded when running `docker compose up`
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 97-120) - Complete development override pattern
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 202-235) - Complete development override configuration
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 37-46) - Docker Compose automatic override loading
- **Dependencies**:
  - Phase 1 and Phase 2 completion (development stages must exist)
  - Existing compose.yaml service definitions

### Task 3.2: Create `compose.production.yaml` for explicit production deployment

Create an explicit production override file for production deployments that ensures production build targets are used.

- **Files**:
  - `compose.production.yaml` - New file with production overrides
- **Success**:
  - Override specifies `target: production` for all service builds
  - No volume mounts for source code (code baked into images)
  - Includes restart: always policies for production resilience
  - Documents explicit production deployment workflow
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 237-254) - Production override pattern
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 33-35) - Docker official production recommendations
- **Dependencies**:
  - Task 3.1 completion

## Phase 4: Update Documentation

### Task 4.1: Update README.md with development workflow instructions

Document the new development workflow that uses automatic volume mounting for instant code changes.

- **Files**:
  - `README.md` - Add/update development setup section
- **Success**:
  - Documents that `docker compose up` automatically enables development mode
  - Explains volume mounts provide instant code changes without rebuilds
  - Lists which directories are mounted (shared/, services/*, frontend/src/)
  - Explains hot-reload behavior for each service type
  - Provides troubleshooting tips for volume mount issues
  - References compose.override.yaml for customization
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 256-280) - Implementation guidance section
- **Dependencies**:
  - Phase 3 completion

### Task 4.2: Update DEPLOYMENT_QUICKSTART.md with production deployment changes

Update production deployment documentation to reflect the new explicit production workflow.

- **Files**:
  - `DEPLOYMENT_QUICKSTART.md` - Update production deployment commands
- **Success**:
  - Documents production deployment command: `docker compose -f compose.yml -f compose.production.yaml up`
  - Explains that production builds copy code into images (no volumes)
  - Clarifies difference between development and production builds
  - Updates any references to docker-compose commands
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 256-280) - Implementation guidance with production workflow
- **Dependencies**:
  - Task 3.2 completion

## Phase 5: Verification and Testing

### Task 5.1: Test development workflow with hot-reload

Verify that development mode works correctly with instant code changes.

- **Files**:
  - All service source files for testing changes
- **Success**:
  - Running `docker compose up` starts all services in development mode
  - Making changes to Python files triggers automatic reload without rebuild
  - Making changes to frontend src files triggers hot module replacement
  - Changes appear in running containers within seconds
  - All services start successfully and remain healthy
  - API endpoints respond correctly to requests
  - Bot connects to Discord successfully
  - Frontend loads and displays correctly
  - No permission errors from volume mounts
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 282-303) - Success criteria and testing guidance
- **Dependencies**:
  - All previous phases complete

### Task 5.2: Verify production build behavior unchanged

Verify that production builds still work as expected with code baked into images.

- **Files**:
  - All Dockerfiles and compose configurations
- **Success**:
  - Building with production target creates images with code copied in
  - Production images are appropriately sized (no development bloat)
  - Running with compose.production.yaml uses no volume mounts
  - All services start successfully in production mode
  - Production images contain all necessary code and dependencies
  - Security best practices maintained (non-root users, minimal attack surface)
  - Integration tests pass against production-mode containers
- **Research References**:
  - #file:../research/20251207-docker-development-volume-mount-research.md (Lines 282-303) - Success criteria for production verification
- **Dependencies**:
  - Task 5.1 completion

## Dependencies

- Docker Compose with multi-file support (already in use)
- Existing multi-stage Dockerfiles
- uv for Python dependency management
- Vite dev server configuration

## Success Criteria

- Development workflow enables instant code changes without rebuilds
- Production workflow remains unchanged with optimized, secure images
- All services support hot-reload in development
- Documentation clearly explains both workflows
- Tests pass in both development and production modes

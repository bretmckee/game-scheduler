<!-- markdownlint-disable-file -->
# Task Research Notes: Docker Development Volume Mount Strategy

## Research Executed

### File Analysis
- `docker-compose.yml` and `docker-compose.base.yml`
  - Currently use production-style builds with COPY commands
  - No volume mounts for source code in development environment
  - Services: api, bot, frontend, notification-daemon, status-transition-daemon, init
  - All services build from multi-stage Dockerfiles targeting production stage

### Dockerfile Analysis
- `docker/api.Dockerfile`, `docker/bot.Dockerfile`, `docker/notification-daemon.Dockerfile`, `docker/status-transition-daemon.Dockerfile`
  - All use multi-stage builds with `base` and `production` stages
  - All COPY application code into production stage
  - No development-specific stages defined

- `docker/frontend.Dockerfile`
  - Uses multi-stage build: builder stage compiles assets, nginx stage serves static files
  - Build-time compilation means no hot-reload in development

### External Research
- #fetch:"https://docs.docker.com/compose/how-tos/production/"
  - Official recommendation: "Remove any volume bindings for application code in production"
  - Pattern: Use compose.override.yaml for development, compose.production.yaml for production
  - Development should mount code via volumes for live editing
  - Production should have code baked into images via COPY

- #fetch:"https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/"
  - Docker Compose automatically reads `compose.yaml` and `compose.override.yaml`
  - Override files merge with base configuration
  - Volumes merge by mount path (local overrides take precedence)
  - Use `-f` flag to specify alternative override files

- #fetch:"https://docs.docker.com/build/building/multi-stage/"
  - Multi-stage builds support targeting specific stages with `--target` flag
  - Can create development stages with different configurations
  - BuildKit only builds stages needed for target (skips unused stages)

- #githubRepo:"docker/awesome-compose" development volume mount patterns
  - Pattern 1: Development stage with volume mounts (nginx-golang-mysql, react-express-mysql)
  - Pattern 2: compose.override.yaml for development overrides
  - Pattern 3: Target different Dockerfile stages for dev vs prod
  - Common: Keep dependencies in image, only mount source code

### Project Conventions
- Standards referenced:
  - `.github/instructions/containerization-docker-best-practices.instructions.md`
  - Multi-stage builds already in use
  - Security best practices (non-root users, health checks)

## Key Discoveries

### Project Structure
Current setup copies all code into containers during build:
- Python services: Copy `shared/` and `services/{service_name}/`
- Frontend: Build React app in builder stage, copy dist to nginx
- No hot-reload capability in development
- Every code change requires full rebuild

### Implementation Patterns

#### Pattern 1: Multi-Stage Build with Development Target
```dockerfile
# Development stage - mounts source code
FROM python:3.13-slim AS development

WORKDIR /app

# Install dependencies only
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system .

# Note: Source code NOT copied here - will be mounted via volume

USER appuser
CMD ["python", "-m", "services.api"]

# Production stage - copies source code
FROM python:3.13-slim AS production

# Copy dependencies from base
COPY --from=base /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy application code into image
COPY shared/ ./shared/
COPY services/api/ ./services/api/

USER appuser
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0"]
```

#### Pattern 2: compose.override.yaml for Development
```yaml
# compose.override.yaml (automatically loaded in development)
services:
  api:
    build:
      target: development  # Build only to development stage
    volumes:
      - ./shared:/app/shared:ro
      - ./services/api:/app/services/api:ro
    command: uvicorn services.api.main:app --host 0.0.0.0 --reload

  bot:
    build:
      target: development
    volumes:
      - ./shared:/app/shared:ro
      - ./services/bot:/app/services/bot:ro
```

#### Pattern 3: Frontend Development with Vite Dev Server
```yaml
# compose.override.yaml
services:
  frontend:
    build:
      target: development
    volumes:
      - ./frontend/src:/app/src:ro
      - ./frontend/index.html:/app/index.html:ro
      - ./frontend/vite.config.ts:/app/vite.config.ts:ro
    command: npm run dev -- --host 0.0.0.0
    environment:
      - VITE_API_URL=http://localhost:8000
```

### Complete Examples from awesome-compose

#### Example 1: nginx-golang-mysql backend/Dockerfile
```dockerfile
FROM --platform=$BUILDPLATFORM golang:1.18-alpine AS builder

WORKDIR /code
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o bin/backend main.go

CMD ["/code/bin/backend"]

# Development stage - runs go run instead of compiled binary
FROM builder AS dev-envs
RUN apk add git
RUN addgroup -S docker && adduser -S --shell /bin/bash --ingroup docker vscode
CMD ["go", "run", "main.go"]

# Production stage - minimal image with compiled binary
FROM scratch
COPY --from=builder /code/bin/backend /usr/local/bin/backend
CMD ["/usr/local/bin/backend"]
```

#### Example 2: react-express-mysql compose patterns
```yaml
# Base compose.yaml
services:
  backend:
    build: backend
    ports:
      - 80:80

  frontend:
    build: frontend
    ports:
      - 3000:3000

# Development (implied compose.override.yaml pattern)
services:
  backend:
    volumes:
      - ./backend:/usr/src/app
    command: npm run dev  # Uses nodemon for auto-reload

  frontend:
    volumes:
      - ./frontend/src:/code/src
    command: npm start  # React dev server with hot-reload
```

### API and Schema Documentation

#### Docker Compose Volume Mount Syntax
```yaml
volumes:
  - ./local/path:/container/path:ro  # Read-only mount
  - ./local/path:/container/path     # Read-write mount
  - /container/path                  # Anonymous volume (preserves data)
```

#### Build Target Specification
```yaml
services:
  myservice:
    build:
      context: .
      dockerfile: Dockerfile
      target: development  # Stop build at this stage
```

### Configuration Examples

#### Complete Development Override Pattern
```yaml
# compose.override.yaml - automatically merged with compose.yaml
services:
  api:
    build:
      target: development
    volumes:
      - ./shared:/app/shared:ro
      - ./services/api:/app/services/api:ro
    command: uvicorn services.api.main:app --host 0.0.0.0 --reload --log-level debug
    environment:
      - LOG_LEVEL=DEBUG
      - PYTHONUNBUFFERED=1

  bot:
    build:
      target: development
    volumes:
      - ./shared:/app/shared:ro
      - ./services/bot:/app/services/bot:ro
    environment:
      - LOG_LEVEL=DEBUG
      - PYTHONUNBUFFERED=1
```

#### Production Override Pattern
```yaml
# compose.production.yaml - used with -f flag
services:
  api:
    build:
      target: production
    # No volumes - code baked into image
    restart: always

  bot:
    build:
      target: production
    restart: always
```

### Technical Requirements
- Dockerfiles need development stage added before production stage
- Development stage installs dependencies but doesn't COPY source code
- compose.override.yaml overrides build target and adds volume mounts
- Frontend needs different approach: use Vite dev server instead of nginx
- Preserve existing multi-stage build benefits (small production images)
- Maintain non-root user security in development
- Keep production builds unchanged (no volumes, code copied in)

## Recommended Approach

**Multi-Stage Dockerfiles with Development Target + compose.override.yaml**

This is the industry-standard pattern that:
1. Uses multi-stage Dockerfiles with separate `development` and `production` stages
2. Development stage installs dependencies but doesn't COPY source code
3. Production stage COPYs source code (existing behavior)
4. Creates `compose.override.yaml` that automatically merges with `compose.yaml` in development
5. Development override specifies `target: development` and mounts source volumes
6. Production deployment uses `compose.yaml` alone or with explicit production override

Benefits:
- Zero rebuild time for code changes in development (instant hot-reload)
- Preserves small, secure production images
- Standard Docker Compose pattern (automatic override loading)
- Separates dev and prod concerns cleanly
- Works with existing multi-stage build infrastructure
- Frontend gets proper dev server with hot module replacement

## Implementation Guidance

### Objectives
1. Enable instant code changes in development without rebuilds
2. Preserve existing production build behavior
3. Add hot-reload capability for all services
4. Maintain security best practices (non-root users)
5. Support frontend development with Vite dev server

### Key Tasks

#### Phase 1: Update Dockerfiles
1. Add `development` stage to Python service Dockerfiles (api, bot, daemons)
   - Install dependencies only
   - Don't COPY source code
   - Use appropriate development commands (uvicorn --reload, python -m)

2. Add `development` stage to frontend Dockerfile
   - Install dependencies only
   - Don't COPY source code
   - Use `npm run dev` for Vite dev server

3. Keep existing `production` stages unchanged

#### Phase 2: Create compose.override.yaml
1. Override build targets to `development`
2. Add volume mounts for source code (read-only recommended)
3. Override commands for hot-reload behavior
4. Add development-specific environment variables
5. Keep base compose.yaml focused on service definitions

#### Phase 3: Update Documentation
1. Document development workflow (docker compose up)
2. Document production workflow (docker compose -f compose.yaml -f compose.production.yaml)
3. Update DEPLOYMENT_QUICKSTART.md
4. Add development setup instructions to README.md

### Dependencies
- Existing multi-stage Dockerfiles
- Docker Compose include mechanism (already in use)
- uv for Python dependency management (already in use)
- Vite dev server configuration (already exists)

### Success Criteria
- Code changes reflect immediately in running containers (no rebuild)
- `docker compose up` works for development out of the box
- Production builds remain unchanged and optimized
- All services support hot-reload in development
- Documentation clearly explains dev vs prod workflows
- Tests continue to pass in both environments

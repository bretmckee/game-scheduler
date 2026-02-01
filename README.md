# Game Scheduler

A Discord game scheduling system with microservices architecture, featuring a Discord bot with button interactions, web dashboard with OAuth2 authentication, role-based authorization, multi-channel support, and automated notifications.

## Quick Links by Role

### 👥 For Users

- **[Guild Administrators](docs/GUILD-ADMIN.md)** - Set up the bot in your Discord server, configure permissions, and manage game templates
- **[Game Hosts](docs/HOST-GUIDE.md)** - Create and manage game sessions using the web dashboard
- **[Players](docs/PLAYER-GUIDE.md)** - Join games, receive notifications, and manage your calendar

### 💻 For Contributors

- **[Developer Documentation](docs/developer/README.md)** - Development setup, architecture, testing, and contributing guidelines
- **[Deployment Documentation](docs/deployment/README.md)** - Self-hosting, configuration, and production deployment

## Key Features

- **Discord Integration**: Button interactions for joining/leaving games with automatic participant management
- **Web Dashboard**: OAuth2-authenticated interface for creating and managing games
- **Smart Scheduling**: Database-backed event-driven notifications and status transitions
- **Multi-Channel Support**: Configure multiple announcement channels with template-based defaults
- **Waitlist Management**: Automatic waitlist with promotion when spots open
- **Role-Based Authorization**: Guild-level permissions with bot manager roles
- **Calendar Export**: Download games as .ics files for personal calendars
- **Display Name Resolution**: Guild-specific nicknames in all participant lists

## Architecture Overview

Microservices architecture with:

- **Discord Bot Service**: Handles Discord Gateway interactions and sends
  notifications to participants
- **Web API Service**: FastAPI REST API for web dashboard and game management
- **Notification Daemon**: Database-backed event-driven scheduler for game
  reminders
- **Status Transition Daemon**: Database-backed event-driven scheduler for game
  status transitions
- **PostgreSQL**: Primary data store with LISTEN/NOTIFY for real-time events
- **RabbitMQ**: Message broker for inter-service communication
- **Redis**: Caching and session storage

### Event-Driven Scheduling System

The system uses a database-backed event-driven architecture for reliable,
scalable scheduling:

#### Game Reminders (Notification Daemon)

1. **Schedule Population**: When games are created or updated, notification
   schedules are stored in the `notification_schedule` table
2. **Event-Driven Wake-ups**: PostgreSQL LISTEN/NOTIFY triggers instant daemon
   wake-ups when schedules change
3. **MIN() Query Pattern**: Daemon queries for the next due notification using
   an optimized O(1) query with partial index
4. **RabbitMQ Events**: When notifications are due, events are published to
   RabbitMQ for the bot service to process

#### Game Status Transitions (Status Transition Daemon)

1. **Schedule Population**: When games are created or scheduled_at updated,
   status transitions are stored in the `game_status_schedule` table
2. **Event-Driven Wake-ups**: PostgreSQL LISTEN/NOTIFY triggers instant daemon
   wake-ups when schedules change
3. **MIN() Query Pattern**: Daemon queries for the next due transition using an
   optimized O(1) query with partial index
4. **Status Updates**: When transitions are due, game status is updated and
   GAME_STARTED events published to RabbitMQ

**Key Features**:

- Unlimited scheduling windows (supports scheduling weeks/months in advance)
- Sub-10 second latency with event-driven wake-ups
- Zero data loss on restarts - all state persisted in database
- Self-healing - single MIN() query resumes processing after restart
- Scalable - O(1) query performance regardless of total scheduled games

For detailed architecture documentation, see [docs/developer/architecture.md](docs/developer/architecture.md) (to be populated in Phase 2).

## Development Setup

**Note**: Complete developer documentation is available in [docs/developer/README.md](docs/developer/README.md)

### Quick Start

1. Ensure the `.env` symlink points to development environment:

```bash
# This symlink is already configured for development
ls -la .env
# Should show: .env -> env/env.dev
```

2. Update `env/env.dev` with your Discord bot credentials if needed

3. Start all services:

```bash
# Development uses .env symlink automatically
docker compose up
```

**How Development Environment Works:**

The `.env` symlink points to `config/env/env.dev`, which contains:
- `COMPOSE_FILE=compose.yaml:compose.override.yaml` - Specifies which compose files to load
- Development-specific configuration (DEBUG logging, all ports exposed)

The development environment automatically:

- **Mounts your source code** as volumes (no rebuilds needed!)
- **Enables hot-reload** for instant code changes
- **Uses development stages** from Dockerfiles
- **Exposes all ports** including management UIs (RabbitMQ, Grafana)

### Development Workflow

**Prerequisites:**

- Source files must be **world-readable** for volume mounts to work
- Development containers run as non-root user (UID 1000)
- If you encounter permission errors, ensure files have read access:
  ```bash
  chmod -R o+r shared/ services/ frontend/
  ```

**Making code changes:**

1. Edit files in `shared/`, `services/`, or `frontend/src/`
2. Changes appear **instantly** in running containers
3. No rebuild or restart required!

**Python services** (API, bot, daemons) use:

- `uvicorn --reload` (API) or `python -m` (bot, daemons)
- Auto-detects file changes and reloads

**Frontend** uses:

- Vite dev server with hot module replacement
- Changes appear instantly in browser

**When you need to rebuild:**

- Dependency changes (`package.json`, `pyproject.toml`)
- Dockerfile modifications
- New files added that need to be included

```bash
# Rebuild specific service
docker compose build api

# Rebuild all services
docker compose build
```

### Pre-commit Hooks

The project uses pre-commit hooks to automatically validate code quality before commits. Most hooks use **standalone isolated environments** that work immediately after `git clone` without requiring `uv sync` or `npm install`.

#### Quick Start (Works Immediately)

Most hooks are standalone and work right away:

```bash
# Install hooks (one-time setup)
uv tool run pre-commit install

# Run all standalone hooks - works without dependencies!
pre-commit run ruff --all-files      # Python linting (isolated)
pre-commit run prettier --all-files  # Frontend formatting (isolated)
pre-commit run eslint --all-files    # Frontend linting (isolated)
pre-commit run typescript --all-files # TypeScript checking (isolated)
```

**Standalone hooks** (work without project dependencies):
- File cleanup (trailing whitespace, end-of-file fixer, etc.)
- Python linting and formatting (`ruff`) - uses official astral-sh/ruff-pre-commit repository
- Frontend formatting (`prettier`) - uses isolated node environment with all dependencies
- Frontend linting (`eslint`) - uses isolated node environment with TypeScript/React plugins
- TypeScript type checking (`typescript`) - uses isolated node environment
- Code complexity checks (`complexipy`, `lizard`) - use isolated Python/node environments
- Duplicate code detection (`jscpd`) - uses isolated node environment
- Copyright headers (`autocopyright`) - uses isolated Python environment

#### Full Development Setup (For All Hooks)

Some hooks require the full project environment:

```bash
# Install Python project dependencies (required for Python tests)
uv sync

# Install frontend dependencies (required for frontend tests/build)
cd frontend && npm install
```

**System-dependent hooks** (require project setup):

| Hook | Requires | Purpose |
|------|----------|---------|
| `mypy` | `uv sync` | Python type checking with project dependencies |
| `python-compile` | `uv sync` | Python compilation validation |
| `pytest-coverage` | `uv sync` | Python unit tests with coverage |
| `diff-coverage` | `uv sync` | Python diff coverage check |
| `frontend-build` | `cd frontend && npm install` | Frontend build validation |
| `vitest-coverage` | `cd frontend && npm install` | Frontend unit tests with coverage |
| `diff-coverage-frontend` | `cd frontend && npm install` | Frontend diff coverage check |
| `ci-cd-workflow` (manual) | Docker | Run GitHub Actions locally with `act` |

#### Normal Usage

```bash
# Just commit normally - all hooks run automatically
git add modified_file.py
git commit -m "Your commit message"
# Pre-commit runs all checks + tests for modified files automatically
# Commit succeeds if all checks pass, fails otherwise
```

**What runs automatically on every commit:**
- All standalone hooks (linting, formatting, type checking, complexity)
- System-dependent hooks (tests for new/modified files)

#### Manual Test Execution

```bash
# Run ALL unit tests (comprehensive validation)
pre-commit run pytest-all --hook-stage manual

# Run ALL frontend tests
pre-commit run vitest-all --hook-stage manual

# Run CI/CD workflow locally (same as GitHub Actions, requires Docker)
pre-commit run ci-cd-workflow --hook-stage manual

# Run all hooks on all files
pre-commit run --all-files
```

#### Emergency Skip (Use Sparingly)

```bash
# Skip ALL hooks for urgent commits
git commit -m "WIP: urgent hotfix" --no-verify

# Skip specific hooks
SKIP=pytest-changed git commit -m "Skip tests temporarily"
```

#### Architecture Notes

- **Official repositories**: ruff uses `github.com/astral-sh/ruff-pre-commit` for automatic updates
- **Isolated environments**: Most tools use `language: python` or `language: node` with `additional_dependencies`
- **Cached environments**: Pre-commit caches isolated environments in `~/.cache/pre-commit/`
- **System hooks**: Complex tools requiring full project context use `language: system`

**Performance expectations:**
- Most commits: 15-45 seconds (depending on files changed)
- Tests run ONLY on new/modified files for efficiency
- Full test suite still runs in CI/CD for comprehensive validation

**Note:** If you encounter issues, you can always skip hooks with `--no-verify`, but the CI pipeline will still run all checks.

### Code Quality Standards

The project enforces comprehensive code quality standards through Ruff linting with 33 enabled rule categories:

**Security & Correctness:**
- **S** (flake8-bandit): Security vulnerability detection (SQL injection, subprocess security, hardcoded secrets)
- **ASYNC** (flake8-async): Async/await best practices
- **FAST** (FastAPI): FastAPI-specific patterns (Annotated dependencies)

**Code Quality & Maintainability:**
- **E/W** (pycodestyle): PEP 8 style enforcement
- **F** (Pyflakes): Logical errors and undefined names
- **N** (pep8-naming): Naming convention enforcement
- **B** (flake8-bugbear): Common bug patterns
- **C4** (flake8-comprehensions): List/dict comprehension improvements
- **UP** (pyupgrade): Modern Python 3.13+ syntax
- **RET** (flake8-return): Return statement optimization
- **SIM** (flake8-simplify): Code simplification opportunities
- **TC** (flake8-type-checking): TYPE_CHECKING import optimization
- **PLE/PLW/PLC** (Pylint): Pylint error/warning/convention checks
- **ERA** (eradicate): Commented-out code detection
- **A** (flake8-builtins): Builtin shadowing prevention
- **DTZ** (flake8-datetimez): Timezone-aware datetime usage
- **ICN** (flake8-import-conventions): Import convention enforcement
- **PT** (flake8-pytest-style): Pytest best practices

**Performance:**
- **PERF** (Perflint): Performance anti-patterns
- **G004** (flake8-logging-format): Lazy logging (no f-strings in logging)

**Polish & Documentation:**
- **T20** (flake8-print): No print statements in production code (use logging)
- **EM** (flake8-errmsg): Exception message extraction
- **G/LOG** (flake8-logging-format): Logging best practices
- **ANN** (flake8-annotations): Comprehensive type annotations
- **ARG** (flake8-unused-arguments): Unused argument detection
- **RUF** (Ruff-specific): Ruff's own code quality rules

**Code Complexity Limits:**
- Cyclomatic complexity: Max 10 per function (C901)
- Statement count: Max 50 per function (PLR0915)
- Overall complexity: Max 15 (complexipy)

**Running Linting Locally:**
```bash
# Check all Python files (uses pyproject.toml configuration)
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check specific rule category
uv run ruff check --select S,ASYNC,FAST .
```

**Note:** All linting rules are enforced in CI/CD and pre-commit hooks. The project maintains a zero-violation baseline for all enabled rules.

### Access Services

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **RabbitMQ Management**: http://localhost:15672

### Monitoring Services

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f api
docker compose logs -f bot
docker compose logs -f notification-daemon

# Restart specific service
docker compose restart api
```

## Running Services Individually

Start specific services for development:

```bash
# Development uses .env symlink automatically (no --env-file needed)

# Start infrastructure only
docker compose up -d postgres rabbitmq redis

# Run database migrations
docker compose run --rm api alembic upgrade head

# Start notification daemon
docker compose up -d notification-daemon

# Start API service
docker compose up -d api

# Start Discord bot
docker compose up -d bot
```

## Building Multi-Architecture Images

The project supports building images for both ARM64 (Apple Silicon, AWS
Graviton) and AMD64 (traditional x86) architectures using Docker Bake.

### Production Builds

For production deployments, use the production environment file:

```bash
# Build production images (uses config/env/env.prod)
docker compose --env-file config/env/env.prod build

# Start production services
docker compose --env-file config/env/env.prod up -d
```

**Environment-Specific Configurations:**

Each environment file (in `config/env/` directory) contains a `COMPOSE_FILE` variable specifying which compose files to load:

- **Production** (`config/env/env.prod`): `COMPOSE_FILE=compose.yaml`
  - Production-only base configuration
  - INFO logging level
  - No port mappings (use reverse proxy)
  - Restart policies enabled

- **Staging** (`config/env/env.staging`): `COMPOSE_FILE=compose.yaml:compose.staging.yaml`
  - Production builds with DEBUG logging
  - Frontend and API ports exposed for testing
  - Restart policies enabled

- **Development** (`config/env/env.dev`): `COMPOSE_FILE=compose.yaml:compose.override.yaml`
  - Development stages with hot-reload
  - DEBUG logging, all ports exposed
  - Source code mounted as volumes

Production builds:

- Target `production` stage in Dockerfiles
- Copy all source code into images (no volume mounts)
- Use optimized production commands
- Include restart policies for reliability

### Setup

Create a multi-platform builder (one-time setup):

```bash
# Check existing builders
docker buildx ls

# Create and use multi-platform builder
docker buildx create --use
```

### Building and Pushing Images

Build for multiple architectures and push to registry:

```bash
# Build all services for both architectures and push
docker buildx bake --push

# Build specific service(s)
docker buildx bake --push api bot

# Build with custom registry and tag
IMAGE_REGISTRY=myregistry.com/ IMAGE_TAG=v1.2.3 docker buildx bake --push

# Build without registry prefix (empty string)
IMAGE_REGISTRY= IMAGE_TAG=dev docker buildx bake --push
```

### Local Development Builds

Development uses `compose.override.yaml` automatically:

```bash
# Development build (single platform, volume mounts)
docker compose build

# Force rebuild after dependency changes
docker compose build --no-cache
```

### Environment Variables

Configure in `.env` file:

- `IMAGE_REGISTRY`: Docker registry URL prefix (include trailing slash)
  - Default: `172-16-1-24.xip.boneheads.us:5050/`
  - Examples: `docker.io/myorg/`, empty for local
- `IMAGE_TAG`: Image tag for built containers
  - Default: `latest`
  - Examples: `v1.0.0`, `dev`, `staging`

## Project Structure

```
.
├── services/
│   ├── bot/                    # Discord bot service
│   ├── api/                    # FastAPI web service
│   └── scheduler/              # Event-driven scheduling daemons
│       ├── generic_scheduler_daemon.py     # Generic parameterized scheduler daemon
│       ├── notification_daemon_wrapper.py  # Game reminder scheduler wrapper
│       ├── status_transition_daemon_wrapper.py  # Game status transition scheduler wrapper
│       ├── event_builders.py               # Event builder functions
│       └── postgres_listener.py            # PostgreSQL LISTEN/NOTIFY client
├── shared/                     # Shared models and utilities
│   └── models/
│       ├── notification_schedule.py        # Notification schedule model
│       └── game_status_schedule.py         # Status schedule model
├── docker/                     # Dockerfiles for each service
├── alembic/                    # Database migrations
├── env/                        # Environment configurations
│   ├── env.dev                 # Development (COMPOSE_FILE=compose.yaml:compose.override.yaml)
│   ├── env.prod                # Production (COMPOSE_FILE=compose.yaml)
│   ├── env.staging             # Staging (COMPOSE_FILE=compose.yaml:compose.staging.yaml)
│   ├── env.e2e                 # E2E tests (COMPOSE_FILE=compose.yaml:compose.e2e.yaml)
│   └── env.int                 # Integration tests (COMPOSE_FILE=compose.yaml:compose.int.yaml)
├── compose.yaml                # Base configuration (production-ready)
├── compose.override.yaml       # Development overrides (auto-loaded via .env symlink)
├── compose.prod.yaml           # Production overrides (minimal)
├── compose.staging.yaml        # Staging overrides (DEBUG logging, app ports)
├── compose.int.yaml            # Integration test overrides
└── compose.e2e.yaml            # E2E test overrides
```

## Docker Compose Architecture

The project uses modern Docker Compose with environment-controlled configuration:

- **`compose.yaml`**: Production-ready base configuration with all services
- **Environment files** (in `config/env/`): Each contains `COMPOSE_FILE` variable specifying which compose files to merge
- **Override files**: Environment-specific modifications (logging, ports, volumes, build targets)

**How it works:**
- Each `config/env/env.*` file sets `COMPOSE_FILE=compose.yaml:compose.{env}.yaml`
- Single `--env-file config/env/env.{environment}` parameter controls entire configuration
- Development uses `.env` symlink → `config/env/env.dev` for automatic configuration

This design ensures all environments stay in sync while allowing
environment-specific configurations. See [TESTING_E2E.md](TESTING_E2E.md) for
testing details.

## License

Copyright 2025 Bret McKee (bret.mckee@gmail.com)

Game Scheduler is available as open source software, see COPYING.txt for
information on the license.

Please contact the author if you are interested in obtaining it under other
terms.

<!-- markdownlint-disable-file -->
# Task Research Notes: Version Management and API Versioning

## Research Executed

### File Analysis
- `pyproject.toml` (lines 1-50)
  - Current version: `0.1.0` (hardcoded)
  - Uses Python 3.13 and modern build system
- `services/api/app.py`
  - FastAPI app currently has hardcoded version: `"1.0.0"`
  - Health endpoint exists at `/health`
  - API routes use `/api/v1/` prefix
- `docker/api.Dockerfile` (lines 1-50)
  - Multi-stage build with Python 3.13-slim
  - Uses `uv` for dependency management
  - Currently no version information embedded
- `git describe --tags --always --dirty`
  - Current git state: `v0.0.1-478-gd128f6a`
  - Repository has git tags with `v` prefix

### Code Search Results
- API routes pattern: `/api/v1/{resource}`
  - auth, guilds, channels, templates, games, export
  - All routers use `/api/v1` prefix, indicating API versioning already in place
- Version keyword search
  - No existing version management code found
  - Only copyright header "version 3" references (license text)

### External Research
- #fetch:"https://packaging.python.org/en/latest/discussions/single-source-version/"
  - Three main approaches to version management:
    1. Extract from VCS (Git) at build time
    2. Hard-code in pyproject.toml (current approach)
    3. Hard-code in source file and extract at build time
  - Recommended: Use `importlib.metadata.version()` at runtime
  - Build systems provide version handling: setuptools_scm, Hatchling, Flit, PDM
- #fetch:"https://setuptools-scm.readthedocs.io/en/latest/usage/"
  - setuptools_scm automatically derives versions from git tags
  - Default versioning scheme:
    - Clean tag: `{tag}` (e.g., `v1.2.3` → `1.2.3`)
    - Post-tag commits: `{next_version}.dev{distance}+g{revision}` (e.g., `1.2.4.dev5+g1a2b3c4`)
    - Dirty working dir: adds `+dYYYYMMDD` suffix
  - Docker integration pattern using `SETUPTOOLS_SCM_PRETEND_VERSION` environment variable
  - Recommended tag format: `vX.Y.Z` (project already uses this)
  - Runtime access via `importlib.metadata.version("package-name")`
- #fetch:"https://fastapi.tiangolo.com/tutorial/metadata/"
  - FastAPI supports version metadata in app creation: `FastAPI(version="...")`
  - Version appears in OpenAPI schema and documentation
  - Can create dedicated version endpoint separate from health check
- #fetch:"https://docs.docker.com/build/building/variables/"
  - Docker ARG and ENV can embed build-time information
  - Build ARG can accept git version from build process
  - Pattern: `ARG GIT_VERSION=unknown` then `ENV GIT_VERSION=$GIT_VERSION`

### Project Conventions
- Standards referenced: Python 3.13+, Docker multi-stage builds, FastAPI patterns
- Instructions followed: Python best practices, containerization guidelines
- Existing patterns:
  - API versioning via `/api/v1` URL prefix
  - Health check endpoint at `/health`
  - Environment-based configuration
  - Multi-stage Docker builds with development and production stages

## Key Discoveries

### Project Structure
- Monorepo with multiple services (api, bot, scheduler, retry, init)
- Uses `pyproject.toml` for Python package management
- Docker containers for all services
- FastAPI for API service with OpenAPI docs
- Already has API version in URL structure (`/api/v1/`)

### Current Version State
- Git repository at `v0.0.1-478-gd128f6a` (478 commits after v0.0.1 tag)
- `pyproject.toml` version: `0.1.0`
- FastAPI app version: `1.0.0`
- Three different version numbers - no single source of truth

### Implementation Patterns

#### Option 1: setuptools-scm (Git-based Automatic Versioning)
**Best for: Production deployments with proper release workflow**

**Mechanism:**
- Automatically derives version from git tags
- No manual version updates needed
- Handles development versions automatically

**Configuration:**
```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=80", "setuptools-scm[simple]>=8"]
build-backend = "setuptools.build_meta"

[project]
# Remove hardcoded version
dynamic = ["version"]

[tool.setuptools_scm]
version_file = "shared/_version.py"  # Optional: write version to file
```

**Runtime Access:**
```python
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("Game_Scheduler")
except PackageNotFoundError:
    __version__ = "unknown"
```

**Docker Integration:**
```dockerfile
# Pass git version at build time
ARG GIT_VERSION
ENV GIT_VERSION=${GIT_VERSION:-unknown}

# Install with version
RUN --mount=source=.git,target=.git,type=bind \
    uv pip install --system .
```

**Build Command:**
```bash
# Get version from git
GIT_VERSION=$(git describe --tags --always --dirty)
docker build --build-arg GIT_VERSION=$GIT_VERSION -t api:$GIT_VERSION .
```

**Pros:**
- Single source of truth (git tags)
- Automatic development version numbering
- No manual version updates
- Standard Python packaging approach
- Works with all Python packaging tools

**Cons:**
- Requires .git directory during build (Docker mount or copy)
- Slightly more complex Docker build
- Needs proper git tagging discipline
- Package must be installed for version to work

**Trade-offs:**
- More sophisticated but industry-standard
- Requires understanding of setuptools_scm versioning scheme
- Best for teams with established release processes

#### Option 2: Build-Time Environment Variable Injection
**Best for: Simple deployments, existing build pipelines**

**Mechanism:**
- Pass version as Docker ARG at build time
- Store in environment variable
- Access at runtime from environment

**Implementation:**
```dockerfile
# docker/api.Dockerfile
ARG GIT_VERSION=dev-unknown
ARG API_VERSION=1.0.0

ENV GIT_VERSION=${GIT_VERSION}
ENV API_VERSION=${API_VERSION}
```

```python
# shared/version.py
import os

def get_git_version() -> str:
    return os.getenv("GIT_VERSION", "unknown")

def get_api_version() -> str:
    return os.getenv("API_VERSION", "1.0.0")
```

```python
# services/api/app.py
from shared.version import get_git_version, get_api_version

app = FastAPI(
    title="Discord Game Scheduler API",
    version=get_api_version(),
    # ...
)

@app.get("/api/v1/version")
async def version_info():
    return {
        "git_version": get_git_version(),
        "api_version": get_api_version(),
    }
```

**Build Command:**
```bash
GIT_VERSION=$(git describe --tags --always --dirty)
docker build \
    --build-arg GIT_VERSION=$GIT_VERSION \
    --build-arg API_VERSION=1.0.0 \
    -t api:$GIT_VERSION \
    .
```

**Pros:**
- Simple and explicit
- No build dependencies on .git
- Works in any environment
- Easy to understand and debug
- Can set different versions independently

**Cons:**
- Requires passing arguments at build time
- Version baked into image (immutable)
- Manual API version updates required
- Not following Python packaging standards

**Trade-offs:**
- Simpler but less automated
- Good for containerized deployments
- May not work well with `pip install`

#### Option 3: Hybrid Approach - Git Tags with Fallback
**Best for: Flexibility across development and production**

**Mechanism:**
- Use setuptools_scm when available
- Fall back to environment variable in containers
- Separate API version from git version

**Configuration:**
```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=80", "setuptools-scm[simple]>=8"]
build-backend = "setuptools.build_meta"

[project]
dynamic = ["version"]

[tool.setuptools_scm]
fallback_version = "0.0.0+unknown"
```

```python
# shared/version.py
import os
from importlib.metadata import version, PackageNotFoundError

API_VERSION = "1.0.0"  # Manually updated

def get_git_version() -> str:
    """Get git version from package metadata or environment."""
    # Try package metadata first (when installed)
    try:
        return version("Game_Scheduler")
    except PackageNotFoundError:
        pass

    # Fall back to environment variable (Docker)
    env_version = os.getenv("GIT_VERSION")
    if env_version:
        return env_version

    # Last resort fallback
    return "unknown"

def get_api_version() -> str:
    """Get API version (semantic version for API compatibility)."""
    return API_VERSION
```

```dockerfile
# docker/api.Dockerfile
ARG GIT_VERSION
ENV GIT_VERSION=${GIT_VERSION:-dev-unknown}

# Try to install with git metadata if available
RUN --mount=source=.git,target=.git,type=bind \
    uv pip install --system . || \
    uv pip install --system .
```

```python
# services/api/app.py
from shared.version import get_git_version, get_api_version

app = FastAPI(
    title="Discord Game Scheduler API",
    version=f"{get_api_version()}-{get_git_version()}",
    # ...
)

@app.get("/api/v1/version")
async def version_info():
    return {
        "git_version": get_git_version(),
        "api_version": get_api_version(),
        "service": "api",
    }
```

**Pros:**
- Works in all scenarios (dev, Docker, installed package)
- Follows Python standards when possible
- Graceful degradation
- Separates API version (breaking changes) from git version (implementation)

**Cons:**
- Most complex implementation
- Requires understanding both approaches
- More code to maintain

**Trade-offs:**
- Maximum flexibility but more moving parts
- Best for projects with diverse deployment scenarios

### API and Schema Documentation

**Current API Structure:**
- Base path: `/api/v1/`
- Resources: auth, guilds, channels, templates, games, export
- Health check: `/health`

**Proposed Version Endpoint:**
```python
@app.get("/api/v1/version")
async def version_info():
    """
    Get version information for the API service.

    Returns:
        dict: Version information including git version and API version
    """
    return {
        "service": "api",
        "git_version": get_git_version(),  # e.g., "0.0.1.dev478+gd128f6a"
        "api_version": get_api_version(),   # e.g., "1.0.0"
        "api_prefix": "/api/v1",
    }
```

**Alternative: Enhance Health Endpoint:**
```python
@app.get("/health")
async def health_check():
    """Health check endpoint with version information."""
    return {
        "status": "healthy",
        "service": "api",
        "version": {
            "git": get_git_version(),
            "api": get_api_version(),
        },
    }
```

### Configuration Examples

**Docker Compose with Version:**
```yaml
# compose.yaml
services:
  api:
    build:
      context: .
      dockerfile: docker/api.Dockerfile
      args:
        GIT_VERSION: ${GIT_VERSION:-dev}
        API_VERSION: "1.0.0"
    environment:
      - GIT_VERSION=${GIT_VERSION:-dev}
```

**GitHub Actions Build:**
```yaml
- name: Build and push API image
  run: |
    GIT_VERSION=$(git describe --tags --always --dirty)
    docker build \
      --build-arg GIT_VERSION=$GIT_VERSION \
      --build-arg API_VERSION=1.0.0 \
      -t api:$GIT_VERSION \
      -f docker/api.Dockerfile \
      .
```

### Technical Requirements

**For setuptools-scm approach:**
- Add `setuptools-scm[simple]>=8` to build requirements
- Ensure git tags follow `vX.Y.Z` format (already done)
- Docker BuildKit for `--mount=source=.git` support
- Package installation for version access

**For environment variable approach:**
- Modify Dockerfiles to accept GIT_VERSION ARG
- Update build scripts to pass version
- Create version utility module
- Update FastAPI app to use version

**For hybrid approach:**
- Combine requirements from both approaches
- Handle fallback gracefully
- Test in all deployment scenarios

**API Versioning Strategy:**
- Semantic versioning for API version (major.minor.patch)
- Major version in URL path (`/api/v1`, `/api/v2`)
- API version changes only for breaking changes
- Git version for tracking exact deployment

## Recommended Approach

**Option 2: Build-Time Environment Variable Injection** is recommended as the starting point for this project.

### Rationale

1. **Simplicity**: Straightforward implementation that doesn't require understanding setuptools_scm internals
2. **Container-Native**: Aligns with the project's Docker-first deployment model
3. **Immediate Value**: Can be implemented quickly and start providing version information right away
4. **No Build Dependencies**: Doesn't require .git directory access during Docker builds
5. **Clear Separation**: Distinguishes between git version (implementation tracking) and API version (compatibility contract)
6. **Future Migration Path**: Can evolve to hybrid approach later if needed

### Why Not setuptools-scm Initially?

While setuptools-scm is the Python ecosystem standard:
- The project is container-focused, not pip-installable package focused
- Adds complexity with .git mounting in Docker builds
- Requires understanding of PEP versioning schemes
- Package installation requirement may not fit current workflow
- Can be adopted later when the benefit outweighs the complexity

### Why Not Hybrid Approach Initially?

- Unnecessary complexity for current needs
- Harder to debug and maintain
- Can migrate to this later if requirements change
- YAGNI principle - implement what's needed now

## Implementation Guidance

### Objectives
- Enable tracking of exact git commit in deployed services
- Provide API version information for client compatibility
- Add version endpoint at `/api/v1/version`
- Include version in health check response
- Make version visible in OpenAPI docs

### Key Tasks

1. **Create Version Module** (`shared/version.py`)
   - Function to get git version from environment
   - Function to get API version (constant)
   - Proper fallback values for development

2. **Update API Service**
   - Import version functions
   - Update FastAPI app version parameter
   - Add `/api/v1/version` endpoint
   - Enhance `/health` endpoint with version info

3. **Modify Docker Files**
   - Add ARG for GIT_VERSION and API_VERSION
   - Set corresponding ENV variables
   - Update all service Dockerfiles consistently

4. **Update Docker Compose**
   - Pass GIT_VERSION from environment or default
   - Document in compose files

5. **Update Build Scripts**
   - Add git describe command to capture version
   - Pass version to Docker build
   - Document build process

6. **Testing**
   - Verify version endpoint returns correct info
   - Test with missing environment variables
   - Validate OpenAPI schema includes version
   - Confirm health check includes version

### Dependencies
- No new Python dependencies required
- Requires Docker BuildKit (already in use)
- Requires git tags (already present in repository)

### Success Criteria
- [ ] `/api/v1/version` endpoint returns git_version and api_version
- [ ] `/health` endpoint includes version information
- [ ] FastAPI OpenAPI docs show correct API version
- [ ] Docker build accepts GIT_VERSION build argument
- [ ] Version shows "unknown" or "dev" when environment variable not set
- [ ] All services (bot, scheduler, etc.) can adopt same pattern

### Future Enhancements
- Add build timestamp
- Include deployment environment
- Track versions of other services
- Migrate to setuptools-scm for pip-installable packages
- Add version compatibility checking between services
